"""Base class for TuringTrust provider wrappers."""

import httpx
import time
import logging
from typing import Optional, List, Dict, Any
from turingtrust.config import TuringTrustConfig

logger = logging.getLogger("turingtrust")


class BaseProvider:
    """Base class providing governance gateway integration."""

    PROVIDER_NAME = "base"

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        provider_api_key: Optional[str] = None,
        turingtrust_url: Optional[str] = None,
        turingtrust_api_key: Optional[str] = None,
        team: str = "default",
        user: Optional[str] = None,
        turingtrust_enabled: bool = True,
        turingtrust_fallback: bool = True,
        turingtrust_config: Optional[TuringTrustConfig] = None,
        config: Optional[TuringTrustConfig] = None,
        **kwargs,
    ):
        # api_key is the provider key in wrappers like OpenAI(api_key=...)
        self.provider_api_key = provider_api_key or api_key
        self.extra_kwargs = kwargs

        if turingtrust_config or config:
            self.config = turingtrust_config or config
        else:
            self.config = TuringTrustConfig(
                gateway_url=turingtrust_url or TuringTrustConfig().gateway_url,
                api_key=turingtrust_api_key,
                team=team,
                user=user,
                enabled=turingtrust_enabled,
                fallback_on_error=turingtrust_fallback,
            )

    def _build_headers(self) -> Dict[str, str]:
        """Backward-compatible header builder used by older tests/integrations."""
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
            headers["X-API-Key"] = self.config.api_key
        provider = getattr(self.config, "provider", None) or self.PROVIDER_NAME
        headers["X-Provider"] = provider
        if self.provider_api_key:
            headers["X-Provider-Key"] = self.provider_api_key
        return headers

    def _build_url(self, path: str) -> str:
        """Backward-compatible URL builder for direct gateway paths."""
        return f"{self.config.gateway_url.rstrip('/')}/{path.lstrip('/')}"

    def _build_gateway_payload(
        self,
        model: str,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> Dict[str, Any]:
        payload = {
            "provider": self.PROVIDER_NAME,
            "model": model,
            "messages": messages,
            "team": self.config.team,
        }
        if self.config.user:
            payload["user"] = self.config.user
        # Forward extra params
        for k in ("temperature", "max_tokens", "top_p", "stream"):
            if k in kwargs:
                payload[k] = kwargs[k]
        return payload

    def _call_gateway_sync(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous call to the governance gateway."""
        headers = self.config.headers_with_provider_key(self.provider_api_key)
        start = time.time()
        try:
            with httpx.Client(
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            ) as client:
                r = client.post(
                    self.config.gateway_chat_url,
                    json=payload,
                    headers=headers,
                )
                r.raise_for_status()
                data = r.json()
                data["_tt_latency_ms"] = int((time.time() - start) * 1000)
                return data
        except httpx.HTTPStatusError as e:
            # Sanitize: re-raise without request/response objects that contain headers
            status = e.response.status_code
            raise RuntimeError(
                f"Gateway returned HTTP {status}"
            ) from None
        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot connect to TuringTrust gateway at {self.config.gateway_url}"
            ) from None
        except httpx.TimeoutException:
            raise RuntimeError(
                f"Gateway request timed out after {self.config.timeout}s"
            ) from None
        except Exception as e:
            # Sanitize: log internally, re-raise without httpx internals
            logger.warning("TuringTrust gateway error: %s", type(e).__name__)
            raise RuntimeError("Gateway request failed") from None

    async def _call_gateway_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Async call to the governance gateway."""
        headers = self.config.headers_with_provider_key(self.provider_api_key)
        start = time.time()
        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout,
                verify=self.config.verify_ssl,
            ) as client:
                r = await client.post(
                    self.config.gateway_chat_url,
                    json=payload,
                    headers=headers,
                )
                r.raise_for_status()
                data = r.json()
                data["_tt_latency_ms"] = int((time.time() - start) * 1000)
                return data
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            raise RuntimeError(
                f"Gateway returned HTTP {status}"
            ) from None
        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot connect to TuringTrust gateway at {self.config.gateway_url}"
            ) from None
        except httpx.TimeoutException:
            raise RuntimeError(
                f"Gateway request timed out after {self.config.timeout}s"
            ) from None
        except Exception as e:
            logger.warning("TuringTrust gateway error: %s", type(e).__name__)
            raise RuntimeError("Gateway request failed") from None


class ChatCompletions:
    """Mimics the OpenAI chat.completions interface."""

    def __init__(self, provider: BaseProvider):
        self._provider = provider

    def create(self, *, model: str, messages: list, **kwargs):
        payload = self._provider._build_gateway_payload(model, messages, **kwargs)
        result = self._provider._call_gateway_sync(payload)
        return GatewayResponse(result)


class AsyncChatCompletions:
    """Async version of chat.completions."""

    def __init__(self, provider: BaseProvider):
        self._provider = provider

    async def create(self, *, model: str, messages: list, **kwargs):
        payload = self._provider._build_gateway_payload(model, messages, **kwargs)
        result = await self._provider._call_gateway_async(payload)
        return GatewayResponse(result)


class Chat:
    """Mimics the OpenAI client.chat namespace."""

    def __init__(self, provider: BaseProvider):
        self.completions = ChatCompletions(provider)


class AsyncChat:
    """Async version of chat namespace."""

    def __init__(self, provider: BaseProvider):
        self.completions = AsyncChatCompletions(provider)


class GatewayResponse:
    """Wraps the gateway response to match OpenAI-like interface."""

    def __init__(self, data: dict):
        self._data = data
        self.governance_action = data.get("governance_action") or data.get("action")
        self.cost = data.get("cost")
        self.decision_id = data.get("decision_id")
        self.sensitive_data = data.get("sensitive_data_findings", [])
        self._tt_latency_ms = data.get("_tt_latency_ms")

        # Build choices from either gateway envelope ("response") or plain LLM payload.
        if "choices" in data:
            self.choices = [Choice(c) for c in (data.get("choices") or [])]
        else:
            response = data.get("response", {})
            if isinstance(response, dict):
                choices_data = response.get("choices", [])
                if choices_data:
                    self.choices = [Choice(c) for c in choices_data]
                else:
                    content = response.get("content") or response.get("text", "")
                    self.choices = [Choice({"message": {"role": "assistant", "content": content}, "index": 0})]
            else:
                self.choices = [Choice({"message": {"role": "assistant", "content": str(response)}, "index": 0})]

        self.model = data.get("model", "")
        self.id = data.get("id", "")

    def __getattr__(self, name):
        return self._data.get(name)

    def to_dict(self):
        return self._data

    @classmethod
    def from_dict(cls, data: dict) -> "GatewayResponse":
        """Backward-compatible constructor."""
        return cls(data)


class Choice:
    def __init__(self, data: dict):
        self._data = data
        self.index = data.get("index", 0)
        self.message = Message(data.get("message", {}))
        self.finish_reason = data.get("finish_reason", "stop")


class Message:
    def __init__(self, data: dict):
        self.role = data.get("role", "assistant")
        self.content = data.get("content", "")

    def __str__(self):
        return self.content
