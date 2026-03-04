"""Azure OpenAI wrapper with TuringTrust governance."""

from turingtrust.providers.base import BaseProvider, Chat


class AzureOpenAI(BaseProvider):
    """Drop-in replacement for openai.AzureOpenAI with governance."""

    PROVIDER_NAME = "azure"

    def __init__(
        self,
        *,
        api_key=None,
        azure_endpoint=None,
        api_version="2024-02-15-preview",
        azure_deployment=None,
        **kwargs,
    ):
        super().__init__(api_key=api_key, **kwargs)
        self.azure_endpoint = azure_endpoint
        self.api_version = api_version
        self.azure_deployment = azure_deployment
        self.chat = Chat(self)

    def _build_gateway_payload(self, model, messages, **kwargs):
        payload = super()._build_gateway_payload(model, messages, **kwargs)
        payload["provider"] = "azure"
        if self.azure_deployment:
            payload["model"] = self.azure_deployment
        return payload
