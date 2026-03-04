<p align="center">
  <h1 align="center">TuringTrust SDK v2</h1>
  <p align="center">Open-source AI governance for LLM operations — BYOK & Managed modes</p>
</p>

<p align="center">
  <a href="https://pypi.org/project/turingtrust/"><img src="https://img.shields.io/pypi/v/turingtrust?color=blue" alt="PyPI"></a>
  <a href="https://pypi.org/project/turingtrust/"><img src="https://img.shields.io/pypi/pyversions/turingtrust" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
</p>

---

TuringTrust is an open-source LLM governance toolkit with a **freemium model**. It provides PII detection, multi-provider gateway routing, composable middleware, and pluggable policy hooks — everything you need to ship AI features responsibly.

## What's New in v2

| Feature | v1 | v2 |
|---------|----|----|
| Access modes | BYOK only | **BYOK + Managed** |
| Middleware | Hooks (sync) | **Composable async middleware pipeline** |
| Streaming | Not supported | **SSE streaming with governance metadata** |
| Error handling | Generic exceptions | **Structured error hierarchy** |
| Quotas | None | **Server-side quota management with caching** |
| Conversations | None | **Full CRUD conversation management** |
| Usage analytics | None | **By model, provider, user** |
| Auth | API key only | **JWT + refresh tokens + org API keys** |
| Retry | Manual | **Auto-retry with exponential backoff** |
| Unified client | None | **`TuringTrust` client with sub-modules** |

## Install

```bash
pip install turingtrust
```

With gateway server (FastAPI + uvicorn):

```bash
pip install turingtrust[gateway]
```

## Quick Start

### BYOK Mode (Bring Your Own Key)

You provide your own LLM provider API keys. Keys are passed per-request and never stored. Zero markup from TuringTrust.

```python
from turingtrust import OpenAI

# Drop-in replacement for openai.OpenAI
client = OpenAI(
    api_key="sk-your-openai-key",
    turingtrust_url="http://localhost:8080",
    turingtrust_api_key="tt_your_platform_key",
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Explain AI governance in one sentence."}],
)
print(response.content)       # Response text
print(response.governance)    # Governance metadata
```

### Managed Mode (TuringTrust provides keys)

No provider keys needed. Single invoice from TuringTrust (30% platform fee).

```python
from turingtrust import TuringTrust

client = TuringTrust(
    api_key="tt_your_platform_key",
    gateway_url="http://localhost:8080",
    access_mode="managed",
)

# Check quota before sending
quota = client.check_quota_sync()
print(f"{quota.used}/{quota.limit} messages used ({quota.usage_percent}%)")

# No provider key needed!
response = client.chat.send(
    model="gpt-4o",
    provider="openai",
    messages=[{"role": "user", "content": "What is AI governance?"}],
)
print(response.content)
```

### Unified Client

```python
from turingtrust import TuringTrust

client = TuringTrust(
    api_key="tt_your_platform_key",
    gateway_url="http://localhost:8080",
    access_mode="byok",
)

# Sub-modules
client.chat          # Send messages, stream, list models
client.quota         # Check & enforce quotas
client.conversations # List, get, delete conversations
client.usage         # Usage analytics
client.auth          # Login, refresh tokens, API key management
client.provider_keys # Manage org provider keys
```

## Freemium Plan Tiers

| Plan | Price | Users | Messages | Features |
|------|-------|-------|----------|----------|
| **Free** | $0 | 5 | 50 managed / 200 BYOK per month | PII detection, basic governance |
| **Starter** | $8/user/mo | 25 | Unlimited | + Approval workflows, budget controls |
| **Business** | $15/user/mo | Unlimited | Unlimited | + SSO, audit trail, custom policies |
| **Compliance** | $25/user/mo | Unlimited | Unlimited | + SOC2, HIPAA, dedicated support |

See [turingtrust.ai/pricing](https://turingtrust.ai/pricing) for details.

## PII Detection

```python
from turingtrust import detect_pii

result = detect_pii("Email me at john@acme.com, SSN 123-45-6789")

print(result.total_findings)   # 2
print(result.entity_counts)    # {"email": 1, "ssn": 1}
print(result.scan_time_ms)     # ~0.1 ms

for finding in result.findings:
    print(f"  {finding.entity_type.value}: {finding.masked_value} ({finding.confidence})")
```

## Middleware Pipeline (v2)

Composable async middleware replaces v1 hooks:

```python
from turingtrust.middleware import (
    PIIMiddleware, RetryMiddleware, CostTrackingMiddleware,
    LoggingMiddleware, build_pipeline,
)

# Stack middleware in order
pipeline = build_pipeline([
    LoggingMiddleware(),
    PIIMiddleware(block_on_high=True),
    RetryMiddleware(max_retries=3),
    CostTrackingMiddleware(),
], llm_handler)

response = await pipeline(request)
```

### Custom Middleware

```python
from turingtrust.middleware import Middleware, MiddlewareRequest, MiddlewareResponse, NextHandler

class ComplianceMiddleware(Middleware):
    async def process(self, request: MiddlewareRequest, call_next: NextHandler) -> MiddlewareResponse:
        # Pre-request logic
        if "investment advice" in request.prompt_text.lower():
            from turingtrust.errors import GovernanceBlockedError
            raise GovernanceBlockedError(
                policy_name="financial-compliance",
                reason="Blocked keyword detected",
            )

        response = await call_next(request)

        # Post-response logic
        response.governance["compliance"] = {"status": "approved"}
        return response
```

## Quota Management

```python
from turingtrust import TuringTrust

client = TuringTrust(api_key="tt_key", gateway_url="http://localhost:8080")

quota = client.check_quota_sync()
print(f"Plan: {quota.plan}")
print(f"Used: {quota.used}/{quota.limit} ({quota.usage_percent}%)")
print(f"Remaining: {quota.remaining}")
print(f"Reset: {quota.reset_date}")

if quota.is_exhausted:
    print("Upgrade at https://turingtrust.ai/pricing")
```

## Streaming (v2)

```python
from turingtrust.streaming import stream_chat

async for chunk in stream_chat(config, provider="openai", model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]):
    print(chunk.delta.content, end="", flush=True)
```

## Error Handling (v2)

Structured error hierarchy for precise exception handling:

```python
from turingtrust.errors import (
    QuotaExceededError, ProviderAuthError, GovernanceBlockedError,
    RateLimitError, PlanFeatureError,
)

try:
    response = client.chat.send(model="gpt-4o", provider="openai", messages=msgs)
except QuotaExceededError as e:
    print(f"Quota exhausted: {e.used}/{e.limit}. Upgrade: {e.upgrade_url}")
except ProviderAuthError:
    print("Invalid provider API key")
except GovernanceBlockedError as e:
    print(f"Blocked by policy '{e.policy_name}': {e.reason}")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except PlanFeatureError as e:
    print(f"Feature '{e.feature}' requires plan: {e.required_plan}")
```

## Supported Providers

| Provider | Wrapper Class | BYOK | Managed | Local |
|----------|--------------|------|---------|-------|
| OpenAI | `OpenAI` / `AsyncOpenAI` | ✅ | ✅ | — |
| Anthropic | `Anthropic` / `AsyncAnthropic` | ✅ | ✅ | — |
| Google Gemini | `Gemini` | ✅ | ✅ | — |
| Groq | `Groq` | ✅ | ✅ | — |
| Mistral | `Mistral` | ✅ | ✅ | — |
| Azure OpenAI | `AzureOpenAI` | ✅ | ✅ | — |
| Ollama | `Ollama` | ✅ | — | `localhost:11434` |
| vLLM | `VLLM` / `AsyncVLLM` | ✅ | — | `localhost:8000` |

## Gateway Server

```bash
pip install turingtrust[gateway]
turingtrust-server
```

BYOK request:

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Provider: openai" \
  -H "X-Provider-Key: sk-your-key" \
  -d '{"model": "gpt-4o", "messages": [{"role": "user", "content": "Hello"}]}'
```

Managed request (no provider key):

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Provider: openai" \
  -H "X-Access-Mode: managed" \
  -H "Authorization: Bearer tt_your_platform_key" \
  -d '{"model": "gpt-4o", "messages": [{"role": "user", "content": "Hello"}]}'
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TURINGTRUST_URL` | `http://localhost:8080` | Gateway URL |
| `TURINGTRUST_API_KEY` | — | Platform API key |
| `TURINGTRUST_ACCESS_MODE` | `byok` | Default access mode (`byok` or `managed`) |
| `TURINGTRUST_HOST` | `127.0.0.1` | Server bind address |
| `TURINGTRUST_PORT` | `8080` | Server port |
| `TURINGTRUST_RPM` | `60` | Rate limit (requests/min) |
| `TURINGTRUST_PII_DETECTION` | `true` | Enable PII scanning |
| `TURINGTRUST_LOGGING` | `true` | Enable request logging |
| `TURINGTRUST_RETRY_MAX` | `3` | Max retry attempts |

## Package Structure

```
turingtrust/
├── __init__.py          # Public API (v2.0.0)
├── config.py            # SDK configuration + plan features
├── auth.py              # JWT auth + refresh tokens + org API keys
├── client.py            # Unified TuringTrust client (v2)
├── errors.py            # Structured error hierarchy (v2)
├── quota.py             # Quota management with caching (v2)
├── streaming.py         # SSE streaming support (v2)
├── middleware.py         # Composable async middleware (v2)
├── conversations.py     # Conversation CRUD (v2)
├── usage.py             # Usage analytics (v2)
├── pii_detector.py      # PII detection (15 entity types)
├── gateway.py           # Multi-provider gateway proxy
├── hooks.py             # GovernanceHook ABC (v1 compat)
├── circuit_breaker.py   # Per-provider circuit breaker
├── rate_limiter.py      # Sliding window rate limiter
├── token_counter.py     # tiktoken-based token counting
├── server.py            # FastAPI server (optional)
├── langchain.py         # LangChain callback handler (optional)
└── providers/
    ├── base.py              # BaseProvider + response classes
    ├── openai_wrapper.py    # OpenAI / AsyncOpenAI
    ├── anthropic_wrapper.py # Anthropic / AsyncAnthropic
    ├── azure_wrapper.py     # AzureOpenAI
    ├── gemini_wrapper.py    # Gemini
    ├── groq_wrapper.py      # Groq
    ├── mistral_wrapper.py   # Mistral
    ├── ollama_wrapper.py    # Ollama
    └── vllm_wrapper.py      # VLLM / AsyncVLLM
```

## Testing

```bash
pip install turingtrust[dev]
pytest tests/ -v
```

## TuringTrust Cloud

The open-source package provides detection and routing. [TuringTrust Cloud](https://turingtrust.ai) adds:

- **Tier 2 PII verification** — LLM-powered false-positive elimination
- **Policy enforcement** — BLOCK / REDACT / ALLOW actions based on configurable rules
- **Approval workflows** — Human-in-the-loop for sensitive operations
- **Budget controls** — Per-team and per-user spend limits
- **Audit trail** — Full history of every LLM call with governance decisions
- **Dashboard** — Real-time monitoring and analytics
- **Model Arena** — Compare LLM providers side-by-side with automated benchmarks

## Contributing

Contributions are welcome. Please open an issue to discuss before submitting a PR.

1. Fork the repo
2. Create a feature branch
3. Add tests for new functionality
4. Run `pytest tests/ -v` to verify
5. Submit a pull request

## License

MIT — see [LICENSE](LICENSE) for details.
