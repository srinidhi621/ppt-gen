# Azure OpenAI Capabilities Report

**Generated**: 2026-04-16 13:14 UTC
**Endpoint**: `https://aifoundry-openai-poc-tr-resource.cognitiveservices.azure.com`
**API**: Responses API only (`/openai/responses?api-version=2026-02-24`)
**Approved models**: `gpt-5.4`, `gpt-5.3-codex`, `gpt-5.2`

## Connectivity

- Endpoint reachable: Yes

## Model Probe Results

No models responded successfully.

### `gpt-5.4` — Failed

- **Error**: HTTP 404: {"error":{"code":"404","message": "Resource not found"}}

### `gpt-5.3-codex` — Failed

- **Error**: HTTP 404: {"error":{"code":"404","message": "Resource not found"}}

### `gpt-5.2` — Failed

- **Error**: HTTP 404: {"error":{"code":"404","message": "Resource not found"}}

## V3 Pipeline Configuration

No working models found. Check API key and endpoint configuration.

## API Constraints

- **Responses API only**. Chat Completions API is not used. (See AGENTS.md Rule 9.)
- **Minimum model floor**: gpt-5.2. No older models permitted in V3 code.
- **API endpoint**: `POST https://aifoundry-openai-poc-tr-resource.cognitiveservices.azure.com/openai/responses?api-version=2026-02-24`
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
