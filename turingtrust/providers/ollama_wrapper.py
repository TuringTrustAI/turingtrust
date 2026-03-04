"""Ollama wrapper with TuringTrust governance."""

from turingtrust.providers.base import BaseProvider, Chat


class Ollama(BaseProvider):
    """Drop-in replacement for Ollama with governance."""

    PROVIDER_NAME = "ollama"

    def __init__(self, *, host=None, **kwargs):
        super().__init__(**kwargs)
        self.host = host or "http://localhost:11434"
        self.chat = Chat(self)

    def _build_gateway_payload(self, model, messages, **kwargs):
        payload = super()._build_gateway_payload(model, messages, **kwargs)
        payload["provider"] = "ollama"
        return payload
