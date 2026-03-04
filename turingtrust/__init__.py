"""
TuringTrust — AI Governance for LLM Operations.

pip install turingtrust

Client SDK:
    from turingtrust import OpenAI
    client = OpenAI(api_key="sk-...", turingtrust_url="http://localhost:8033", turingtrust_api_key="tt_...")
    response = client.chat.completions.create(model="gpt-4o", messages=[...])

Gateway / PII Detection:
    from turingtrust import detect_pii, GatewayService, GovernanceHook
"""

# ── SDK Client ────────────────────────────────────────────────────────────────
from turingtrust.config import TuringTrustConfig
from turingtrust.auth import TuringTrustAuth

# Provider wrappers (client-side — sends calls through the governance gateway)
from turingtrust.providers.openai_wrapper import OpenAI, AsyncOpenAI
from turingtrust.providers.anthropic_wrapper import Anthropic, AsyncAnthropic
from turingtrust.providers.ollama_wrapper import Ollama
from turingtrust.providers.vllm_wrapper import VLLM, AsyncVLLM
from turingtrust.providers.gemini_wrapper import Gemini
from turingtrust.providers.groq_wrapper import Groq
from turingtrust.providers.mistral_wrapper import Mistral
from turingtrust.providers.azure_wrapper import AzureOpenAI

# LangChain integration
from turingtrust.langchain import TuringTrustCallbackHandler

# ── Gateway (server-side) ────────────────────────────────────────────────────
from turingtrust.pii_detector import detect_pii, EntityType, DetectionResult, PIIFinding
from turingtrust.gateway import GatewayService, GatewayError, ProviderError
from turingtrust.hooks import GovernanceHook, PIIDetectionHook, LoggingHook
from turingtrust.circuit_breaker import CircuitBreaker
from turingtrust.rate_limiter import RateLimiter
from turingtrust.token_counter import TokenCounter

__version__ = "1.0.0"
__all__ = [
    # SDK
    "TuringTrustConfig",
    "TuringTrustAuth",
    "OpenAI",
    "AsyncOpenAI",
    "Anthropic",
    "AsyncAnthropic",
    "Ollama",
    "VLLM",
    "AsyncVLLM",
    "Gemini",
    "Groq",
    "Mistral",
    "AzureOpenAI",
    "TuringTrustCallbackHandler",
    # Gateway
    "detect_pii",
    "EntityType",
    "DetectionResult",
    "PIIFinding",
    "GatewayService",
    "GatewayError",
    "ProviderError",
    "GovernanceHook",
    "PIIDetectionHook",
    "LoggingHook",
    "CircuitBreaker",
    "RateLimiter",
    "TokenCounter",
]
