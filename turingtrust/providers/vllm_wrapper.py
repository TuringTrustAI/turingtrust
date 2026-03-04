"""vLLM wrapper with TuringTrust governance."""

from turingtrust.providers.base import BaseProvider, Chat, AsyncChat


class VLLM(BaseProvider):
    """Drop-in replacement for vLLM client with governance."""

    PROVIDER_NAME = "vllm"

    def __init__(self, *, base_url=None, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url or "http://localhost:8000"
        self.chat = Chat(self)


class AsyncVLLM(BaseProvider):
    """Async vLLM client with governance."""

    PROVIDER_NAME = "vllm"

    def __init__(self, *, base_url=None, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url or "http://localhost:8000"
        self.chat = AsyncChat(self)
