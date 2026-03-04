"""TuringTrust SDK configuration."""

import logging
import os
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger("turingtrust")


def _validate_gateway_url(url: str) -> str:
    """Warn if gateway URL uses HTTP for non-localhost targets."""
    parsed = urlparse(url)
    if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        logger.warning(
            "SECURITY: Gateway URL uses http:// for non-localhost target (%s). "
            "API keys and tokens will be sent in plaintext. "
            "Set TURINGTRUST_URL to an https:// URL in production.",
            parsed.hostname,
        )
    return url


@dataclass
class TuringTrustConfig:
    """Configuration for the TuringTrust governance gateway."""

    gateway_url: str = field(
        default_factory=lambda: _validate_gateway_url(
            os.getenv("TURINGTRUST_URL", "http://localhost:8033")
        )
    )
    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("TURINGTRUST_API_KEY")
    )
    # Backward-compat for older SDK/tests that passed provider via config.
    provider: str = field(
        default_factory=lambda: os.getenv("TURINGTRUST_PROVIDER", "openai")
    )
    team: str = field(
        default_factory=lambda: os.getenv("TURINGTRUST_TEAM", "default")
    )
    user: Optional[str] = field(
        default_factory=lambda: os.getenv("TURINGTRUST_USER")
    )
    timeout: int = field(
        default_factory=lambda: int(os.getenv("TURINGTRUST_TIMEOUT", "30"))
    )
    enabled: bool = field(
        default_factory=lambda: os.getenv("TURINGTRUST_ENABLED", "true").lower() == "true"
    )
    verify_ssl: bool = field(
        default_factory=lambda: os.getenv("TURINGTRUST_VERIFY_SSL", "true").lower() == "true"
    )
    retry_count: int = field(
        default_factory=lambda: int(os.getenv("TURINGTRUST_RETRY_COUNT", "3"))
    )
    fallback_on_error: bool = field(
        default_factory=lambda: os.getenv("TURINGTRUST_FALLBACK_ON_ERROR", "true").lower() == "true"
    )

    @property
    def gateway_chat_url(self) -> str:
        return f"{self.gateway_url.rstrip('/')}/api/gateway/chat"

    @property
    def gateway_providers_url(self) -> str:
        return f"{self.gateway_url.rstrip('/')}/api/gateway/providers"

    @property
    def headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["X-API-Key"] = self.api_key
        return h

    def headers_with_provider_key(self, provider_key: str = None) -> dict:
        """Return headers including the client's LLM provider key (BYOK)."""
        h = dict(self.headers)
        if provider_key:
            h["X-Provider-Key"] = provider_key
        return h
