# TuringTrust

> **v1.0.0 "Sentinel"** — Pilot Release, March 2026

**AI governance platform for LLM operations.**

TuringTrust is a full-stack governance layer for LLM applications. It sits between your code and your LLM providers — enforcing policies, detecting sensitive data, managing budgets, tracking compliance, and giving you visibility into every call your organization makes.

[![PyPI](https://img.shields.io/pypi/v/turingtrust?color=blue)](https://pypi.org/project/turingtrust/)
[![License](https://img.shields.io/badge/license-Proprietary-red)](LICENSE)
[![SDK License](https://img.shields.io/badge/SDK-MIT-green)](turingtrust/LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-green)](https://python.org)

---

## Platform Overview

| Category | What it does |
|----------|-------------|
| **AI Gateway** | Central proxy routing LLM requests. Policy enforcement, key stripping, per-provider timeouts, auto-fallback on 401/429 |
| **AI Chat** | SSE-streamed chat with conversation history, 4-mode key resolution, free-tier quota (200 msg/mo) |
| **Policy Engine** | Pluggable governance rules — 7 actions, 20 operators. Pre-request / post-response hooks |
| **Model Arena** | Multi-provider LLM benchmarking with LLM-as-judge scoring |
| **Red Team** | Adversarial prompt testing — jailbreak, injection, exfiltration, bias |
| **Agent Guardian** | Agentic AI runtime monitor — plan deviation, tool misuse, scope creep detection |
| **Compliance Certifier** | 850+ controls across 8 frameworks (NIST AI RMF, EU AI Act, ISO 42001, SOC2, HIPAA, GDPR, DPDPA, MIAS) |
| **Anomaly Detection** | Intelligent pattern analysis, cost spikes, behavioral deviations |
| **FinOps & Budgets** | Cost tracking with scope (global/team/user/provider), member budget allocation, alert thresholds |
| **Key Vault** | Multi-key per provider, AES-256-GCM encryption, health monitoring, auto-fallback, priority ordering |
| **PII Detection** | Regex-based scanner for 15+ entity types. Streaming PII scanner for real-time protection |

## Supported Providers

| Cloud | Self-Hosted |
|-------|-------------|
| OpenAI | Ollama |
| Anthropic | vLLM |
| Google Gemini | |
| Groq | |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18 + Vite + Tailwind CSS + Zustand (42 pages, 16 components) |
| **Backend** | FastAPI + SQLAlchemy + Alembic + JWT (33 routers, 62 services) |
| **Database** | SQLite (dev) / Neon PostgreSQL (prod) — 31 models, 17 migrations |
| **Auth** | JWT tokens + Google OAuth + GitHub OAuth + email/password |
| **Encryption** | AES-256-GCM for provider keys at rest |
| **Deployment** | Railway (backend) + Neon Postgres (prod DB) |

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/MiCodes2/TuringTrust-app.git
cd TuringTrust-app
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Required environment variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Database connection string |
| `JWT_SECRET` | Secret for JWT token signing |
| `PROVIDER_KEY_ENCRYPTION_KEY` | Base64-encoded 32-byte key for AES-256-GCM |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GITHUB_CLIENT_ID` | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth client secret |

Optional (for managed mode):

| Variable | Description |
|----------|-------------|
| `PLATFORM_OPENAI_API_KEY` | Platform-managed OpenAI key |
| `PLATFORM_ANTHROPIC_API_KEY` | Platform-managed Anthropic key |
| `PLATFORM_GOOGLE_API_KEY` | Platform-managed Gemini key |

### 3. Run migrations

```bash
alembic upgrade head
```

### 4. Start backend

```bash
uvicorn main:app --host 0.0.0.0 --port 8033 --reload
```

### 5. Start frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:5181
```

---

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │           React SPA (Vite + Tailwind)       │
                    │  42 pages · 16 components · Zustand stores  │
                    └──────────────────┬──────────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────────┐
                    │         FastAPI Backend (port 8033)         │
                    │   33 routers · 62 services · 6 middleware   │
                    ├─────────────────────────────────────────────┤
                    │  JWT Auth → RBAC → Rate Limiter → Logger   │
                    └──────────────────┬──────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────────────┐
                    │                  │                          │
                    ▼                  ▼                          ▼
          ┌─────────────┐   ┌──────────────────┐   ┌─────────────────┐
          │  Key Vault  │   │  Policy Engine   │   │  PostgreSQL/    │
          │  AES-256-GCM│   │  7 actions       │   │  SQLite         │
          │  Multi-key  │   │  20 operators    │   │  31 models      │
          │  Auto-fallback│  │  Sandbox testing │   │  17 migrations  │
          └──────┬──────┘   └──────────────────┘   └─────────────────┘
                 │
    ┌────────────┼────────────┬────────────┬──────────┐
    ▼            ▼            ▼            ▼          ▼
 OpenAI    Anthropic     Gemini        Groq     Ollama/vLLM
```

### Key Resolution (4 modes + key pools)

```
SDK BYOK → Org BYOK (org_provider_keys) → Admin BYOK (byok_admin) → Managed (env)
```

Platform key pools (`PLATFORM_*_API_KEY`) serve managed-mode free-tier users with round-robin and degradation tracking. Per-key spend caps (migration 017) prevent unlimited spend on any single key.

### Role Hierarchy

| Role | Scope | Access |
|------|-------|--------|
| `super_admin` | Platform | Full platform control, Admin Console, plan management |
| `org_admin` | Organization | Governance dashboard, policies, budgets, settings |
| `team_admin` | Team | Team-scoped governance features |
| `admin` | Organization | Governance dashboard access |
| `approver` | Organization | Approval workflows, decisions |
| `user` | Organization | AI Chat + Settings only |

---

## Project Structure

```
TuringTrust-app/
├── main.py                          # FastAPI app entry, mounts all routers at /api/*
├── alembic/versions/                # 17 database migrations (001 → 017)
├── turingtrust_backend/
│   ├── config.py                    # App configuration
│   ├── database.py                  # DB connection + session
│   ├── plans.py                     # Plan defaults & feature matrix
│   ├── security.py                  # JWT utilities
│   ├── routers/                     # 33 API routers
│   │   ├── registration.py          #   /api/auth (register, login, OAuth)
│   │   ├── gateway.py               #   /api/gateway (LLM proxy)
│   │   ├── chat.py                  #   /api/chat (SSE streaming)
│   │   ├── policies.py              #   /api/policies
│   │   ├── admin.py                 #   /api/admin
│   │   ├── admin_provider_keys.py   #   /api/admin/provider-keys
│   │   ├── admin_billing.py         #   /api/admin/billing
│   │   ├── arena.py                 #   Model Arena
│   │   ├── red_team.py              #   Red Team
│   │   ├── agent_guardian.py        #   Agent Guardian
│   │   ├── certifier.py             #   Compliance Certifier
│   │   ├── anomalies.py             #   Anomaly Detection
│   │   ├── budgets.py               #   Budget management
│   │   └── ...                      #   + 19 more
│   ├── services/                    # 62 business logic services
│   │   ├── gateway_service.py       #   LLM proxy + policy enforcement
│   │   ├── llm_proxy_service.py     #   SSE streaming proxy
│   │   ├── org_provider_key_service.py  # Key vault (multi-key, health, fallback)
│   │   ├── key_health_service.py    #   Background key health monitor
│   │   ├── chat_service.py          #   Chat + quota enforcement
│   │   ├── usage_metering_service.py#   Usage tracking + billing
│   │   ├── policy_engine.py         #   Governance rule evaluation
│   │   ├── encryption_service.py    #   AES-256-GCM encryption
│   │   ├── scoring_engine.py        #   LLM-as-judge (multi-provider fallback)
│   │   ├── background_tasks.py      #   APScheduler jobs
│   │   └── ...                      #   + 52 more
│   ├── models/                      # 31 SQLAlchemy models
│   │   ├── user.py                  #   User account
│   │   ├── org_member.py            #   Org membership
│   │   ├── provider_key.py          #   Provider API keys
│   │   ├── budget.py                #   Budget management
│   │   └── ...                      #   + 26 more
│   └── middleware/                   # 6 middleware layers
│       ├── auth.py                  #   JWT validation
│       ├── rbac.py                  #   Role-based access
│       ├── rate_limit.py            #   Per-org rate limits
│       ├── request_logging.py       #   Structured logging
│       └── spa_routing.py           #   React SPA fallback
├── frontend/
│   └── src/
│       ├── App.jsx                  # Routes + role-based access
│       ├── pages/                   # 42 React pages
│       ├── components/              # 16 shared components
│       ├── stores/                  # 3 Zustand stores (auth, theme, settings)
│       ├── services/api.js          # Axios instance + all API modules
│       └── utils/                   # Plan features, pricing, timezone
├── tests/                           # 14 test files
└── docs/                            # 13 documentation files
```

---

## Database Migrations

| # | Name | Description |
|---|------|-------------|
| 001 | RLS & Plans | Row-level security and plan definitions |
| 002 | NextGen Modules | Arena, Agent Guardian, Red Team tables |
| 003 | Security & Registration | OAuth, email verification, password reset |
| 004 | Platform Settings | Global platform configuration |
| 005 | Integrations | Third-party integration support |
| 006 | OAuth Password Fix | `hashed_password` nullable for OAuth users |
| 007 | Arena Regions | Arena region data and benchmark seeds |
| 008 | Chat Interface | Conversations, messages, org_provider_keys, usage_records |
| 009 | Free Quota | 200 msg/mo free tier, monthly reset |
| 010 | Policy Status | Policy active/draft/archived tracking |
| 011 | Onboarding | Org onboarding completion tracking |
| 012 | Key Vault Hardening | Priority, health checks, auto-fallback on org_provider_keys |
| 013 | Budget Name | Named budgets |
| 014 | Budget Members | Per-member budget allocation |
| 015 | Conversation Starred | `is_starred` column on conversations |
| 016 | Expanded Models & Pricing | Managed pricing for Gemini 3.x, Imagen 4, Nano models |
| 017 | Key Spend Caps | Per-key monthly spend limits on `org_provider_keys` |

---

## Plans & Pricing

| Plan | Calls/mo | Members | Keys | Rate (req/s) | Chat Msgs/mo |
|------|----------|---------|------|-------------|-------------|
| Free | 1,000 | 3 | 2 | 5 | 200 |
| Team | 10,000 | 15 | 10 | 20 | Unlimited |
| Compliance | 50,000 | 50 | 30 | 50 | Unlimited |
| Enterprise | Unlimited | Unlimited | Unlimited | 100 | Unlimited |

---

## TuringTrust Cloud vs Open Source

| Feature | Open Source | [Cloud](https://turingtrust.ai) |
|---------|-----------|------|
| LLM Gateway + BYOK | ✅ | ✅ |
| PII Detection (Tier 1 — regex) | ✅ | ✅ |
| PII Enforcement (REDACT / BLOCK) | — | ✅ |
| AI Chat with SSE Streaming | — | ✅ |
| Policy Engine (7 actions, 20 operators) | — | ✅ |
| Model Arena (multi-provider benchmarking) | — | ✅ |
| Red Team (adversarial testing) | — | ✅ |
| Agent Guardian (agentic AI monitoring) | — | ✅ |
| Compliance Certifier (8 frameworks, 850+ controls) | — | ✅ |
| Anomaly Detection | — | ✅ |
| FinOps & Budget Management | — | ✅ |
| Key Vault (multi-key, health monitor, auto-fallback) | — | ✅ |
| Approval Workflows | — | ✅ |
| Multi-tenant RBAC (6 roles) | — | ✅ |
| Webhooks (20+ event types) | — | ✅ |
| Governance Dashboard | — | ✅ |

> [turingtrust.ai](https://turingtrust.ai)

---

## SDK Quick Start

```python
from turingtrust import OpenAI

client = OpenAI(
    api_key="sk-your-openai-key",
    turingtrust_url="http://localhost:8033",
    turingtrust_api_key="tt_your_key",
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

Works for every provider:

```python
from turingtrust import Anthropic, Gemini, Groq, Ollama
```

---

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the full 11-step production deployment guide.

**Stack**: Railway (backend) + Neon PostgreSQL (prod DB)

```bash
# After every deploy
alembic upgrade head
```

---

## What's New in v1.0.0 "Sentinel"

### Security
- **Cross-org key isolation** — Removed portal-wide fallback from chat, gateway, and key vault services
- **Expanded key stripping** — Gateway now strips 13 credential fields (up from 3)
- **Hard-fail encryption** — `PROVIDER_KEY_ENCRYPTION_KEY` required in production (app refuses to start without it)
- **Auth on gateway endpoints** — Stats and health endpoints now require authentication

### Features
- **Platform key pools** — `PLATFORM_*_API_KEY` env vars support comma-separated pools with round-robin and degradation tracking
- **Per-key spend caps** — Monthly spend limits per provider key with auto-reset (migration 017)
- **Conversation starring** — Star/unstar conversations for quick access (migration 015)
- **Expanded model pricing** — Gemini 3.x, Imagen 4, Nano models (migration 016)

### Bug Fixes
- **SLA datetime comparison** — Fixed naive/aware datetime mixing in SLA breach detection
- **401 interceptor deadlock** — Fixed infinite retry loop in frontend API client token refresh
- **Vite host binding** — Fixed dev server binding for Codespaces / remote environments

---

## Contributing

We welcome contributions. Please open an issue first for significant changes.

```bash
git clone https://github.com/MiCodes2/TuringTrust-app.git
cd TuringTrust-app
pip install -r requirements.txt
pytest tests/ -v
```

## License

**TuringTrust Platform**: Proprietary. All rights reserved. See [LICENSE](LICENSE).

**TuringTrust SDK** (PyPI package): MIT License. See [turingtrust/LICENSE](turingtrust/LICENSE).

---

## Local Development

```bash
# Backend (port 8033)
uvicorn main:app --host 0.0.0.0 --port 8033 --reload

# Frontend (port 5181)
cd frontend && npm run dev
```
