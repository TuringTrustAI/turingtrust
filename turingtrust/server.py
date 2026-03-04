"""
TuringTrust — Minimal Gateway Server

Run as a standalone FastAPI server:
    $ turingtrust-server           # via console_scripts entry point
    $ python -m turingtrust.server # via module

Provides /v1/chat/completions compatible endpoint that proxies to any LLM provider.
"""

import hashlib
import logging
import os
import sys
from typing import Optional

try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import JSONResponse
except ImportError:
    FastAPI = None  # type: ignore[assignment, misc]

from turingtrust.gateway import GatewayService, GatewayError, ProviderError
from turingtrust.hooks import PIIDetectionHook, LoggingHook

logger = logging.getLogger("turingtrust.server")


def _hash_rate_key(provider_key: Optional[str]) -> str:
    """Hash provider key for rate limiting — never use raw key material."""
    if not provider_key:
        return "anonymous"
    return hashlib.sha256(provider_key.encode()).hexdigest()[:16]


def create_app(
    enable_pii_detection: bool = True,
    enable_logging: bool = True,
    rate_limit_rpm: int = 60,
) -> "FastAPI":
    """
    Create a FastAPI application wrapping the TuringTrust gateway.

    Args:
        enable_pii_detection: Attach PIIDetectionHook (default: True).
        enable_logging: Attach LoggingHook (default: True).
        rate_limit_rpm: Requests per minute (0 = unlimited).
    """
    if FastAPI is None:
        raise ImportError(
            "FastAPI is required to run the gateway server. "
            "Install with: pip install turingtrust[gateway]"
        )

    app = FastAPI(
        title="TuringTrust Gateway",
        description="Open-source LLM gateway with PII detection and governance hooks",
        version="0.1.0",
    )

    hooks = []
    if enable_pii_detection:
        hooks.append(PIIDetectionHook())
    if enable_logging:
        hooks.append(LoggingHook())

    gateway = GatewayService(hooks=hooks, rate_limit_rpm=rate_limit_rpm)

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "turingtrust-gateway"}

    @app.get("/stats")
    async def stats():
        return gateway.get_stats()

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        """
        OpenAI-compatible chat completions endpoint.

        Headers:
            X-Provider: Provider name (openai, anthropic, gemini, groq, mistral, etc.)
            X-Provider-Key: Your API key for the chosen provider (BYOK).
            Authorization: Alternative — Bearer token used as provider key.

        Body:
            Standard chat completion body: {"model": "...", "messages": [...]}
        """
        provider = request.headers.get("X-Provider", "openai")
        provider_key = request.headers.get("X-Provider-Key")

        # Fall back to Authorization header
        if not provider_key:
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                provider_key = auth[7:]

        if not provider_key and provider not in ("ollama", "vllm"):
            raise HTTPException(
                status_code=401,
                detail="Missing provider API key. Set X-Provider-Key header or Authorization: Bearer <key>",
            )

        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")

        try:
            result = await gateway.proxy(
                provider=provider,
                body=body,
                provider_key=provider_key,
                rate_limit_key=_hash_rate_key(provider_key),
            )
            return JSONResponse(content=result)
        except GatewayError as e:
            status = 429 if "rate limit" in str(e).lower() else 503
            raise HTTPException(status_code=status, detail=str(e))
        except ProviderError as e:
            raise HTTPException(status_code=e.status_code, detail=str(e))
        except Exception as e:
            logger.exception("Internal gateway error")
            raise HTTPException(status_code=500, detail="Internal gateway error")

    @app.post("/v1/{provider}/chat/completions")
    async def provider_chat_completions(provider: str, request: Request):
        """
        Provider-specific endpoint: /v1/openai/chat/completions

        Same as /v1/chat/completions but provider is in the URL path.
        """
        provider_key = request.headers.get("X-Provider-Key")
        if not provider_key:
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                provider_key = auth[7:]

        if not provider_key and provider not in ("ollama", "vllm"):
            raise HTTPException(
                status_code=401,
                detail="Missing provider API key.",
            )

        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")

        try:
            result = await gateway.proxy(
                provider=provider,
                body=body,
                provider_key=provider_key,
                rate_limit_key=_hash_rate_key(provider_key),
            )
            return JSONResponse(content=result)
        except GatewayError as e:
            status = 429 if "rate limit" in str(e).lower() else 503
            raise HTTPException(status_code=status, detail=str(e))
        except ProviderError as e:
            raise HTTPException(status_code=e.status_code, detail=str(e))
        except Exception as e:
            logger.exception("Internal gateway error")
            raise HTTPException(status_code=500, detail="Internal gateway error")

    return app


def main():
    """Entry point for `turingtrust-server` console script."""
    try:
        import uvicorn
    except ImportError:
        print(
            "uvicorn is required to run the server. "
            "Install with: pip install turingtrust[gateway]",
            file=sys.stderr,
        )
        sys.exit(1)

    host = os.environ.get("TURINGTRUST_HOST", "127.0.0.1")
    port = int(os.environ.get("TURINGTRUST_PORT", "8080"))
    rpm = int(os.environ.get("TURINGTRUST_RPM", "60"))
    pii = os.environ.get("TURINGTRUST_PII_DETECTION", "true").lower() == "true"
    log = os.environ.get("TURINGTRUST_LOGGING", "true").lower() == "true"

    app = create_app(enable_pii_detection=pii, enable_logging=log, rate_limit_rpm=rpm)

    print(f"TuringTrust Gateway starting on {host}:{port}", file=sys.stderr)
    print(f"  PII detection: {'enabled' if pii else 'disabled'}", file=sys.stderr)
    print(f"  Rate limit: {rpm} RPM", file=sys.stderr)
    print(f"  Endpoints:", file=sys.stderr)
    print(f"    POST /v1/chat/completions", file=sys.stderr)
    print(f"    POST /v1/<provider>/chat/completions", file=sys.stderr)
    print(f"    GET  /health", file=sys.stderr)
    print(f"    GET  /stats", file=sys.stderr)

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
