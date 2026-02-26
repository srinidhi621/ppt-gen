# CLAUDE.md — Project Instructions for Claude Code

## Python Environment
- Virtual environment: `.venv/` (project-local)
- Always activate before running anything: `source .venv/bin/activate`
- Source `.env` for API keys: `source .env`
- Combined: `source .venv/bin/activate && source .env && <command>`

## LLM Constraints
- **Preferred model: Gemini 3 Flash Preview** (`gemini-3-flash-preview`) — use when API key has access.
- **Fallback: Gemini 2.5 Flash** (`gemini-2.5-flash`) — current default in code.
- To switch models: set `GEMINI_MODEL=gemini-3-flash-preview` in `.env`, or pass `--llm-model gemini-3-flash-preview`.
- Do not use other models (no Gemini Pro, no GPT-4, no other providers) without explicit user approval.

## Running Tests
```bash
source .venv/bin/activate && python -m pytest tests/ -v
```

## Running the Pipeline
```bash
source .venv/bin/activate && source .env && python -m src.cli generate --input <file> --planner llm --llm-provider gemini
```

## Repository Conventions (from AGENTS.md)

### Primary Artifacts
- `SPEC.md` / `PLAN.md` / `AGENTS.md` — source of truth docs
- `assets/template/template.pptx` — corporate template
- `assets/layout/layout_catalog.json` — allowed layouts + fit budgets
- `assets/icons/icons.json` — icon metadata (30,700+ entries)
- `assets/catalog/asset_catalog.json` — unified asset catalog (30,771 entries)
- `assets/catalog/visual_vocabulary.json` — concept-to-icon mapping
- `assets/catalog/branded_images.json` — Dimensional Keyword illustrations
- `inputs/` — content inputs
- `runs/<run_id>/` — all run outputs (never use `output/` directories)

### Agent Policies
- **No new `.md` files** for reviews/analysis unless user explicitly asks.
- **No new dependencies** without user approval.
- Follow `AGENTS.md` strictly. Do not invent new architecture.

### Non-Negotiable Constraints
- Preflight validation must prevent overflow before rendering (no autofit).
- Template-first rendering: use masters/layouts/placeholder formatting.
- Placeholder binding via `shape.alt_text` == `field_key` (not indexes).
- PNG icons only in render path (SVG conversion is offline).
- Markdown formatting (`**bold**`, `*italic*`) must be parsed into python-pptx runs, never leaked as literal text.
- Do not send raw icon IDs to the LLM planner; use the visual vocabulary abstraction.

### Current Work Order
See `PLAN.md` Section 3 — Visual Polish Phase (Steps 1-7).
