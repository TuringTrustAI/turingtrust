"""Google Gemini wrapper with TuringTrust governance."""

from turingtrust.providers.base import BaseProvider, Chat


class Gemini(BaseProvider):
    """Drop-in replacement for Gemini with governance."""

    PROVIDER_NAME = "gemini"

    def __init__(self, *, api_key=None, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.chat = Chat(self)

    def generate_content(self, prompt: str, *, model: str = "gemini-pro", **kwargs):
        """Gemini-style generate_content method."""
        messages = [{"role": "user", "content": prompt}]
        payload = self._build_gateway_payload(model, messages, **kwargs)
        return self._call_gateway_sync(payload)
