"""Mistral wrapper with TuringTrust governance."""

from turingtrust.providers.base import BaseProvider, Chat


class Mistral(BaseProvider):
    """Drop-in replacement for Mistral with governance."""

    PROVIDER_NAME = "mistral"

    def __init__(self, *, api_key=None, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.chat = Chat(self)
