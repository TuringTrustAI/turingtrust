"""Anthropic drop-in replacement with TuringTrust governance."""

from turingtrust.providers.base import BaseProvider, Chat, AsyncChat


class Anthropic(BaseProvider):
    """Drop-in replacement for anthropic.Anthropic with governance."""

    PROVIDER_NAME = "anthropic"

    def __init__(self, *, api_key=None, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.chat = Chat(self)
        self.messages = self.chat.completions  # Anthropic uses messages.create()

    def _build_gateway_payload(self, model, messages, **kwargs):
        payload = super()._build_gateway_payload(model, messages, **kwargs)
        # Anthropic uses max_tokens not max_completion_tokens
        if "max_tokens" not in payload and "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
        return payload


class AsyncAnthropic(BaseProvider):
    """Drop-in replacement for anthropic.AsyncAnthropic with governance."""

    PROVIDER_NAME = "anthropic"

    def __init__(self, *, api_key=None, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.chat = AsyncChat(self)
        self.messages = self.chat.completions
