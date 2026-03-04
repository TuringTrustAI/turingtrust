"""
TuringTrust — Gateway Service (Open Source)

Lightweight LLM gateway proxy with:
  - Multi-provider routing (OpenAI, Anthropic, Gemini, Groq, Mistral, Azure, Ollama, vLLM)
  - BYOK (Bring Your Own Key) — keys passed per-request, never stored
  - Circuit breaker — per-provider failure protection
  - Rate limiter — sliding window RPM
  - Token counting — tiktoken-based (with fallback)
  - Pluggable governance hooks — add PII detection, logging, custom policies

No database required. No external service dependencies (except the LLM providers).

Usage:
    from turingtrust.gateway import GatewayService
    from turingtrust.hooks import PIIDetectionHook

    gw = GatewayService(hooks=[PIIDetectionHook()])
    result = await gw.proxy(
        provider="openai",
        body={"model": "gpt-4o", "messages": [{"role": "user", "content": "Hello"}]},
        provider_key="sk-...",
    )
"""

import time
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

from turingtrust.circuit_breaker import CircuitBreaker
from turingtrust.rate_limiter import RateLimiter
from turingtrust.token_counter import TokenCounter
from turingtrust.hooks import GovernanceHook


# ──────────────────────────────────────────────
# Provider Definitions
# ──────────────────────────────────────────────
CLOUD_BACKENDS: dict[str, dict] = {
    "openai": {"host": "api.openai.com", "port": 443, "protocol": "https"},
    "anthropic": {"host": "api.anthropic.com", "port": 443, "protocol": "https"},
    "gemini": {"host": "generativelanguage.googleapis.com", "port": 443, "protocol": "https"},
    "groq": {"host": "api.groq.com", "port": 443, "protocol": "https"},
    "mistral": {"host": "api.mistral.ai", "port": 443, "protocol": "https"},
    "azure_openai": {"host": "openai.azure.com", "port": 443, "protocol": "https"},
    "ollama": {"host": "localhost", "port": 11434, "protocol": "http"},
    "vllm": {"host": "localhost", "port": 8000, "protocol": "http"},
}

SUPPORTED_PROVIDERS = list(CLOUD_BACKENDS.keys())


class GatewayError(Exception):
    """Raised when the gateway cannot process a request."""
    pass


class ProviderError(Exception):
    """Raised when the upstream LLM provider returns an error."""
    def __init__(self, message: str, status_code: int = 500, provider: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider


class GatewayService:
    """
    Lightweight LLM gateway proxy.

    Args:
        hooks: List of GovernanceHook instances to run on each request.
        backends: Custom backend definitions (overrides defaults).
        rate_limit_rpm: Requests per minute (0 = unlimited).
        circuit_failure_threshold: Failures before opening circuit.
        circuit_recovery_timeout: Seconds before attempting recovery.
        request_timeout: HTTP timeout for provider calls (seconds).
    """

    def __init__(
        self,
        hooks: Optional[list[GovernanceHook]] = None,
        backends: Optional[dict[str, dict]] = None,
        rate_limit_rpm: int = 60,
        circuit_failure_threshold: int = 5,
        circuit_recovery_timeout: int = 60,
        request_timeout: float = 120.0,
    ):
        self.hooks = hooks or []
        self.backends = {**CLOUD_BACKENDS, **(backends or {})}
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_failure_threshold,
            recovery_timeout=circuit_recovery_timeout,
        )
        self.rate_limiter = RateLimiter(requests_per_minute=rate_limit_rpm) if rate_limit_rpm > 0 else None
        self.token_counter = TokenCounter()
        self.request_timeout = request_timeout

    async def proxy(
        self,
        provider: str,
        body: dict,
        provider_key: Optional[str] = None,
        rate_limit_key: str = "global",
        path: str = "",
    ) -> dict:
        """
        Proxy a request to an LLM provider.

        Args:
            provider: Provider name (e.g., "openai", "anthropic", "gemini").
            body: Request body (must include "model" and "messages" for chat).
            provider_key: API key for the provider (BYOK — not stored).
            rate_limit_key: Key for rate limiting (e.g., user ID, API key hash).
            path: Custom path override (for ollama/vllm).

        Returns:
            Provider response dict, potentially augmented with governance metadata.

        Raises:
            GatewayError: Rate limited, circuit open, or missing provider.
            ProviderError: Upstream provider returned an error.
        """
        if httpx is None:
            raise GatewayError(
                "httpx is required for the gateway. Install with: pip install turingtrust[gateway]"
            )

        # 1. Validate provider
        backend = self.backends.get(provider)
        if not backend:
            raise GatewayError(
                f"Unknown provider '{provider}'. Supported: {list(self.backends.keys())}"
            )

        # 2. Rate limit check
        if self.rate_limiter and not self.rate_limiter.check_and_record(rate_limit_key):
            raise GatewayError(
                f"Rate limit exceeded ({self.rate_limiter.rpm} RPM). Try again later."
            )

        # 3. Circuit breaker check
        if not self.circuit_breaker.can_execute(provider):
            raise GatewayError(
                f"Circuit breaker open for '{provider}'. Provider appears to be down."
            )

        # 4. Extract model and messages
        model = body.get("model", "unknown")
        messages = body.get("messages", [])

        # 5. Run pre-request hooks
        metadata: dict = {}
        for hook in self.hooks:
            try:
                messages, metadata = hook.pre_request(provider, model, messages, metadata)
            except Exception as e:
                raise GatewayError(f"Hook {hook.__class__.__name__}.pre_request failed: {e}")

        # Update body with potentially modified messages
        if messages:
            body["messages"] = messages

        # 6. Count prompt tokens
        prompt_text = " ".join(
            m.get("content", "") for m in messages
            if isinstance(m.get("content"), str)
        )
        prompt_tokens = self.token_counter.count(prompt_text)

        # 7. Build URL + headers
        url, headers = self._build_provider_request(provider, backend, path, body, provider_key)

        # 8. Forward request
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                response = await client.post(url, json=body, headers=headers)
                response.raise_for_status()
                response_data = response.json()

            self.circuit_breaker.record_success(provider)
        except httpx.HTTPStatusError as e:
            self.circuit_breaker.record_failure(provider)
            raise ProviderError(
                f"{provider} returned {e.response.status_code}: {e.response.text[:500]}",
                status_code=e.response.status_code,
                provider=provider,
            )
        except Exception as e:
            self.circuit_breaker.record_failure(provider)
            raise ProviderError(
                f"Request to {provider} failed: {str(e)}",
                provider=provider,
            )

        latency_ms = (time.time() - start_time) * 1000

        # 9. Count completion tokens
        completion_text = ""
        if isinstance(response_data, dict):
            choices = response_data.get("choices", [])
            if choices and isinstance(choices[0], dict):
                msg = choices[0].get("message", {})
                completion_text = msg.get("content", "") if isinstance(msg, dict) else ""

        completion_tokens = self.token_counter.count(completion_text)

        # 10. Attach gateway metadata
        if isinstance(response_data, dict):
            response_data["gateway_metadata"] = {
                "provider": provider,
                "model": model,
                "prompt_tokens_estimated": prompt_tokens,
                "completion_tokens_estimated": completion_tokens,
                "latency_ms": round(latency_ms, 2),
            }

        # 11. Run post-response hooks
        for hook in self.hooks:
            try:
                response_data = hook.post_response(provider, model, response_data, metadata)
            except Exception:
                pass  # post-response hooks are best-effort

        return response_data

    def _build_provider_request(
        self,
        provider: str,
        backend: dict,
        path: str,
        body: dict,
        provider_key: Optional[str] = None,
    ) -> tuple[str, dict]:
        """Build provider-specific URL and headers (BYOK)."""
        base_url = f"{backend['protocol']}://{backend['host']}"
        if backend["port"] not in (80, 443):
            base_url += f":{backend['port']}"

        headers = {"Content-Type": "application/json"}

        if provider == "openai":
            url = f"{base_url}/v1/chat/completions"
            if provider_key:
                headers["Authorization"] = f"Bearer {provider_key}"

        elif provider == "anthropic":
            url = f"{base_url}/v1/messages"
            if provider_key:
                headers["x-api-key"] = provider_key
            headers["anthropic-version"] = "2023-06-01"

        elif provider == "gemini":
            model = body.get("model", "gemini-2.0-flash")
            url = f"{base_url}/v1beta/models/{model}:generateContent"
            if provider_key:
                headers["x-goog-api-key"] = provider_key

        elif provider == "groq":
            url = f"{base_url}/openai/v1/chat/completions"
            if provider_key:
                headers["Authorization"] = f"Bearer {provider_key}"

        elif provider == "mistral":
            url = f"{base_url}/v1/chat/completions"
            if provider_key:
                headers["Authorization"] = f"Bearer {provider_key}"

        elif provider == "azure_openai":
            deployment = body.get("model", "gpt-4o")
            endpoint = backend.get("azure_endpoint", "")
            api_version = backend.get("azure_api_version", "2024-02-01")
            url = f"https://{endpoint}.openai.azure.com/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
            if provider_key:
                headers["api-key"] = provider_key

        elif provider in ("ollama", "vllm"):
            default_path = "/v1/chat/completions" if provider == "vllm" else "/api/chat"
            url = f"{base_url}{path or default_path}"

        else:
            url = f"{base_url}{path or '/v1/chat/completions'}"
            if provider_key:
                headers["Authorization"] = f"Bearer {provider_key}"

        return url, headers

    def add_hook(self, hook: GovernanceHook):
        """Add a governance hook at runtime."""
        self.hooks.append(hook)

    def remove_hook(self, hook_class: type) -> bool:
        """Remove all hooks of a given class. Returns True if any removed."""
        before = len(self.hooks)
        self.hooks = [h for h in self.hooks if not isinstance(h, hook_class)]
        return len(self.hooks) < before

    def add_backend(self, name: str, host: str, port: int = 443, protocol: str = "https", **kwargs):
        """Register a custom backend provider."""
        self.backends[name] = {"host": host, "port": port, "protocol": protocol, **kwargs}

    def get_stats(self) -> dict:
        """Return gateway runtime stats."""
        return {
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "rate_limiter_rpm": self.rate_limiter.rpm if self.rate_limiter else 0,
            "hooks": [h.__class__.__name__ for h in self.hooks],
            "backends": list(self.backends.keys()),
        }
