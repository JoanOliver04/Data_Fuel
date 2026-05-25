# AI Assistant

Data Fuel's conversational layer turns deterministic recommendations into
plain-language explanations. It is an **enrichment layer**: the LLM only writes
prose; every number, verdict and confidence comes from the platform's own ML and
ranking. It is fully optional and degrades to deterministic explanations when no
LLM is configured or the provider fails — recommendation endpoints are never
affected.

- [Architecture](#architecture)
- [Provider abstraction](#provider-abstraction)
- [Explanation flow](#explanation-flow)
- [Safety & hallucination control](#safety--hallucination-control)
- [Caching](#caching)
- [Endpoints](#endpoints)
- [Configuration](#configuration)
- [Observability](#observability)
- [Latency expectations](#latency-expectations)

## Architecture

```
backend/app/ai/
├── providers/      # LLMProvider Protocol + fallback + OpenAI-compatible + factory
├── prompts/        # versioned, anti-hallucination templates
├── services/       # explanation engine (orchestration)
├── cache.py        # context-keyed TTL caches
├── safety.py       # input sanitisation / prompt-injection mitigation
└── schemas.py      # conversation-safe Pydantic models (facts + responses)
```

The package is **isolated**: it depends only on `app.core` (config, metrics,
cache) and its own modules — never on domain entities, repositories or routing
providers. The API endpoints (`app/api/v1/endpoints/ai.py`) are the composition
root: they gather facts from existing services and hand pure `ai.schemas` models
to the engine. The LLM therefore enriches explanations and never drives business
logic.

## Provider abstraction

`LLMProvider` is a `Protocol` with one method:

```python
async def complete(self, system: str, user: str) -> LLMResult: ...
```

Providers **never raise** — transport, timeout, HTTP and parse failures all
return `LLMResult(ok=False, reason=...)`. Implementations:

- **`FallbackProvider`** (default) — no network; always `ok=False, reason="disabled"`.
- **`OpenAICompatibleProvider`** — any OpenAI-style `/chat/completions` API.
  Timeout-bounded (`asyncio.wait_for`), retries transient failures, requests
  JSON-mode output, omits `Authorization` for keyless providers (local Ollama).
  The API key is read from settings/env at call time — **never hard-coded**. Its
  `name` carries the concrete provider id for metrics/health labels.

The factory holds a **preset registry** mapping each provider id to its base URL,
default model and key requirement — one transport serves all of them:

| Provider | Base URL | Default model | Key |
| --- | --- | --- | --- |
| `openrouter` *(prod default)* | `openrouter.ai/api/v1` | `deepseek/deepseek-chat` | `OPENROUTER_API_KEY` |
| `groq` | `api.groq.com/openai/v1` | `llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| `ollama` | `localhost:11434/v1` | `llama3.1` | none |
| `openai` | `api.openai.com/v1` | `gpt-4o-mini` | `LLM_API_KEY` |

`get_llm_provider(settings)` resolves key (provider-specific → generic
`LLM_API_KEY`) and model (`LLM_MODEL` override → provider default), and degrades
to the fallback when the LLM is disabled, the id is unknown/reserved, or a
required key is missing. `anthropic` is **reserved** (recognised by config,
degrades to fallback) — wiring it later is a new provider class behind the same
Protocol, no orchestration changes. Each provider also exposes
`health_check() → ProviderHealth` (probes `GET /models`), surfaced at
`GET /api/v1/ai/health` as a diagnostic — it never gates request serving.

## Explanation flow

```
endpoint → build facts (ranking + prediction) → engine.explain(kind, facts, provider)
         → cache hit? ─yes→ return (cached=true)
                       │no
         → provider.complete(system, user)
              ├─ ok + valid JSON → AIExplanation(source="llm")   # prose from model
              └─ fail / invalid   → AIExplanation(source="fallback")  # deterministic
```

The returned `AIExplanation` is **prose-only from the model**; `verdict`,
`confidence`, `risk_level`, `prediction_summary` numbers and all station figures
are set from the validated facts in code. So even a model that returns a
different verdict cannot change the answer (covered by tests).

## Safety & hallucination control

- **Grounding** — prompts inject the facts JSON and forbid inventing prices,
  predictions, stations, traffic or confidence.
- **Structural guarantee** — numbers/verdict come from data, not the model, so a
  metric *cannot* be fabricated even on a successful injection.
- **Input sanitisation** (`safety.py`) — strips control chars, neutralises
  prompt-injection / role-override patterns (`ignore previous…`, `system prompt`,
  fenced blocks, …), collapses whitespace and hard-caps length
  (`LLM_MAX_INPUT_CHARS`).
- **Output validation** — model output must be a JSON object with a non-empty
  `summary`; otherwise it is rejected (`ai_hallucination_rejections_total`) and
  the deterministic fallback is used.
- **No leakage** — the system prompt is never echoed; unhandled errors return the
  sanitised 500 from `app/core/errors.py` (no stack traces or system prompts).

## Caching

`TTLCache` instances (`ai.cache`) keyed by `kind | prompt_version | provider |
question | facts_json`. The facts payload includes the **model version**, so a
retrain or prompt change produces a new key and old explanations age out — no
explicit invalidation. Only successful LLM output is cached, so transient
provider failures recover on the next request.

## Endpoints

| Endpoint | Method | Returns |
| --- | --- | --- |
| `/api/v1/ai/explain-recommendation` | GET | `AIExplanation` |
| `/api/v1/ai/explain-prediction` | GET | `AIExplanation` |
| `/api/v1/ai/trend-summary` | GET | `TrendSummary` |
| `/api/v1/ai/chat` | POST | `AIExplanation` |
| `/api/v1/ai/health` | GET | `AIProviderHealth` (diagnostic) |

All are rate-limited (`AI_RATE_LIMIT`). `404` when no stations in range; `422`
for missing trend area or empty/garbage chat input. `AIExplanation.source`
(`llm`/`fallback`) and `cached` make the provenance explicit to clients.

## Configuration

| Setting | Default | Notes |
| --- | --- | --- |
| `AI_ENABLED` | `true` | Master switch; false → always fallback. |
| `DATAFUEL_LLM_PROVIDER` | `fallback` | `fallback`/`openrouter`/`groq`/`ollama`/`openai` (alias of `LLM_PROVIDER`). Prod: `openrouter`. |
| `OPENROUTER_API_KEY` | — | Required for `openrouter`; env only. |
| `OPENROUTER_MODEL` | `deepseek/deepseek-chat` | OpenRouter model id. |
| `GROQ_API_KEY` | — | Required for `groq`; env only. |
| `LLM_API_KEY` | — | Generic/`openai` key; per-provider key wins. |
| `LLM_BASE_URL` | *(preset)* | Optional override of the provider base URL. |
| `LLM_MODEL` | *(preset)* | Optional override of the provider model. |
| `LLM_TIMEOUT_SECONDS` | `8.0` | Hard wall-clock cap per call. |
| `LLM_MAX_RETRIES` | `1` | Transient-failure retries. |
| `LLM_MAX_OUTPUT_TOKENS` | `600` | — |
| `LLM_MAX_INPUT_CHARS` | `2000` | Chat input cap. |
| `AI_CACHE_TTL_SECONDS` | `900` | — |
| `AI_RATE_LIMIT` | `20/minute` | — |

Default config makes **zero network calls** — safe for local dev and CI.

## Observability

Metrics (see [observability.md](observability.md)):
`datafuel_ai_requests_total{kind,result}`, `datafuel_ai_generation_duration_seconds{kind}`,
`datafuel_ai_provider_failures_total{provider,reason}`, `datafuel_ai_cache_operations_total{result}`,
`datafuel_ai_fallbacks_total{kind}`, `datafuel_ai_hallucination_rejections_total{reason}`,
`datafuel_ai_tokens_total{kind,type}`. Each LLM call logs structured failures
without leaking secrets.

## Latency expectations

- **Fallback / cache hit**: sub-millisecond (no network).
- **LLM call**: typically 1–5 s, bounded by `LLM_TIMEOUT_SECONDS`. AI endpoints
  are separate and opt-in, so recommendation latency is unaffected.
