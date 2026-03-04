"""OpenAI drop-in replacement with TuringTrust governance."""

from turingtrust.providers.base import BaseProvider, Chat, AsyncChat


class OpenAI(BaseProvider):
    """Drop-in replacement for openai.OpenAI with governance."""

    PROVIDER_NAME = "openai"

    def __init__(self, *, api_key=None, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.chat = Chat(self)


class AsyncOpenAI(BaseProvider):
    """Drop-in replacement for openai.AsyncOpenAI with governance."""

    PROVIDER_NAME = "openai"

    def __init__(self, *, api_key=None, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.chat = AsyncChat(self)
