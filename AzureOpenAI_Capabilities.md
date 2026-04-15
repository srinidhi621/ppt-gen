# Azure OpenAI Capabilities Report

**Generated**: 2026-04-15 12:04 UTC
**Endpoint**: `https://aifoundry-openai-poc-tr-resource.cognitiveservices.azure.com`
**API**: Responses API only (`/openai/responses?api-version=2025-04-01-preview`)
**Approved models**: `gpt-5.4`, `gpt-5.3-codex`, `gpt-5.2`

## Connectivity

- Endpoint reachable: Yes

## Model Probe Results

| Model | Status | JSON Mode | Vision | Code Gen | Requests/min | Tokens/min |
|---|---|---|---|---|---|---|
| `gpt-5.4` | Working | Yes | Yes | Yes | 2500 | 250000 |
| `gpt-5.3-codex` | Working | Yes | No | Yes | 2500 | 250000 |
| `gpt-5.2` | Working | Yes | Yes | Yes | 2500 | 250000 |

### `gpt-5.4`

- **Model returned**: `gpt-5.4`
- **Test response**: `PROBE_OK`
- **Usage**: 13 input, 7 output, 20 total
- **Rate limits**:
  - `x-ratelimit-abusepenalty-active`: False
  - `x-ratelimit-limit-requests`: 2500
  - `x-ratelimit-limit-tokens`: 250000
  - `x-ratelimit-remaining-requests`: 2499
  - `x-ratelimit-remaining-tokens`: 249993
  - `x-ratelimit-renewalperiod-requests`: 60
  - `x-ratelimit-renewalperiod-tokens`: 60
  - `x-ratelimit-reset-requests`: 24
  - `x-ratelimit-reset-tokens`: 1
- **JSON mode**: Supported
  - Response: `{"status":"ok","count":42}`
- **Vision**: Supported
  - Response: `red`
- **Code generation**: Supported
  - Tokens: 44 in, 62 out

### `gpt-5.3-codex`

- **Model returned**: `gpt-5.3-codex`
- **Test response**: `PROBE_OK`
- **Usage**: 13 input, 7 output, 20 total
- **Rate limits**:
  - `x-ratelimit-abusepenalty-active`: False
  - `x-ratelimit-limit-requests`: 2500
  - `x-ratelimit-limit-tokens`: 250000
  - `x-ratelimit-remaining-requests`: 2499
  - `x-ratelimit-remaining-tokens`: 249993
  - `x-ratelimit-renewalperiod-requests`: 60
  - `x-ratelimit-renewalperiod-tokens`: 60
  - `x-ratelimit-reset-requests`: 24
  - `x-ratelimit-reset-tokens`: 1
- **JSON mode**: Supported
  - Response: `{"status":"ok","count":42}`
- **Vision**: Not supported
- **Code generation**: Supported
  - Tokens: 44 in, 65 out

### `gpt-5.2`

- **Model returned**: `gpt-5.2`
- **Test response**: `PROBE_OK`
- **Usage**: 13 input, 7 output, 20 total
- **Rate limits**:
  - `x-ratelimit-abusepenalty-active`: False
  - `x-ratelimit-limit-requests`: 2500
  - `x-ratelimit-limit-tokens`: 250000
  - `x-ratelimit-remaining-requests`: 2499
  - `x-ratelimit-remaining-tokens`: 249993
  - `x-ratelimit-renewalperiod-requests`: 60
  - `x-ratelimit-renewalperiod-tokens`: 60
  - `x-ratelimit-reset-requests`: 24
  - `x-ratelimit-reset-tokens`: 1
- **JSON mode**: Supported
  - Response: `{"status":"ok","count":42}`
- **Vision**: Supported
  - Response: `Red`
- **Code generation**: Supported
  - Tokens: 44 in, 99 out

## V3 Pipeline Configuration

| Role | Requirements | Model | Status |
|---|---|---|---|
| **Planner** | JSON mode | `gpt-5.4` | Ready |
| **Builder** | Code generation | `gpt-5.3-codex` | Ready |
| **Reviewer** | Vision + JSON mode | `gpt-5.4` | Ready |

### Recommended .env

```
AZURE_OPENAI_ENDPOINT=https://aifoundry-openai-poc-tr-resource.cognitiveservices.azure.com
AZURE_OPENAI_API_VERSION=2025-04-01-preview
V3_PLANNER_MODEL=gpt-5.4
V3_BUILDER_MODEL=gpt-5.3-codex
V3_REVIEWER_MODEL=gpt-5.4
```

### Rate Limits

| Model | Requests/min | Tokens/min |
|---|---|---|
| `gpt-5.4` | 2500 / 60s | 250000 / 60s |
| `gpt-5.3-codex` | 2500 / 60s | 250000 / 60s |
| `gpt-5.2` | 2500 / 60s | 250000 / 60s |

## API Constraints

- **Responses API only**. Chat Completions API is not used. (See AGENTS.md Rule 9.)
- **Minimum model floor**: gpt-5.2. No older models permitted in V3 code.
- **API endpoint**: `POST https://aifoundry-openai-poc-tr-resource.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview`
- **Model selection**: via `model` field in request body (not URL path)

## Available GPT-5.x Models on This Endpoint

| Model ID |
|---|
| `gpt-5-2025-08-07` |
| `gpt-5-mini-2025-08-07` |
| `gpt-5-nano-2025-08-07` |
| `gpt-5-chat-2025-08-07` |
| `gpt-5-chat-2025-08-15` |
| `gpt-5-codex-2025-09-15` |
| `gpt-5-chat-2025-10-03` |
| `gpt-5-pro-2025-10-06` |
| `gpt-5.1-2025-11-13` |
| `gpt-5.1-chat-2025-11-13` |
| `gpt-5.1-codex-2025-11-13` |
| `gpt-5.1-codex-mini-2025-11-13` |
| `gpt-5.1-codex-max-2025-12-04` |
| `gpt-5-mini-lite-2025-08-07` |
| `gpt-5.2-2025-12-11` |
| `gpt-5.2-chat-2025-12-11` |
| `gpt-5.2-codex-2026-01-14` |
| `gpt-5.2-chat-2026-02-10` |
| `gpt-5.3-codex-2026-02-20` |
| `gpt-5.3-codex-2026-02-24` |
| `gpt-5.4-2026-03-05` |
| `gpt-5.3-chat-2026-03-03` |
| `gpt-5.4-pro-2026-03-05` |
| `gpt-5.4-mini-2026-03-17` |
| `gpt-5.4-nano-2026-03-17` |
| `gpt-5-mini-2025-08-07-lite` |
| `gpt-5.1` |
