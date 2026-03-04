"""Groq wrapper with TuringTrust governance."""

from turingtrust.providers.base import BaseProvider, Chat


class Groq(BaseProvider):
    """Drop-in replacement for Groq with governance."""

    PROVIDER_NAME = "groq"

    def __init__(self, *, api_key=None, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.chat = Chat(self)
