# PPT-Gen: LLM-Assisted PPTX Generator

PPT-Gen generates editable PowerPoint decks from combined content + visual cues using:
- `python-pptx` for deterministic rendering
- template-first layout binding via placeholder alt-text (`field_key`)
- LLM planning and one-loop multimodal review/rework
- hard preflight fit checks to prevent overflow

## Current Status

Implemented:
- one-loop automated pipeline (`generate-auto`)
- planner V1 -> render V1 -> diagnose + slide images -> multimodal review -> planner V2 -> render V2
- deterministic composition artifacts (`composition_spec_v1.json`, `composition_spec_v2.json`)
- V2 quality gates with hard fail mode
- automated slide image conversion (`soffice` + `pdftoppm`)

Known gap:
- composition polish is still below target quality for consulting-style decks.
- visual coverage is now enforced, but visual storytelling quality still needs stronger per-slide composition logic.

## Architecture (Implemented)

Pipeline:
1. Normalize combined markdown into `content.md` + `cues.json`
2. Planner V1 (LLM) -> `planner_deckir_v1.json`
3. Deterministic compose/validate/render V1
4. Diagnose V1 + slide image export
5. Multimodal review (LLM) -> `review_feedback_v1.json`
6. Planner rework V2 (LLM) -> `planner_deckir_v2.json`
7. Deterministic compose/validate/render V2
8. Diagnose V2 + quality gates -> stop

## Requirements

- Python 3.10+
- Virtualenv `.venv`
- LLM credentials in `.env` (Azure OpenAI or Gemini)
- System binaries for automated review images:
  - LibreOffice (`soffice`)
  - Poppler (`pdftoppm`)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

macOS binaries:

```bash
brew install --cask libreoffice
brew install poppler
```

## CLI

Validate template/catalog:

```bash
python -m src.cli validate
```

Render DeckIR:

```bash
python -m src.cli render --deckir inputs/sample_deckir.json
```

Smoke test:

```bash
python -m src.cli smoke --deckir inputs/sample_deckir.json
```

Single-pass generation:

```bash
python -m src.cli generate --input inputs/legacy-system-navigator.combined.md --run-id run_single
```

Full automated one-loop run:

```bash
source .venv/bin/activate
set -a && source .env && set +a
python -m src.cli generate-auto \
  --input inputs/legacy-system-navigator.combined.md \
  --run-id run_auto
```

## Run Artifacts

Each run writes to `runs/<run_id>/`, including:
- planner artifacts (`planner_deckir_v1.json`, `planner_deckir_v2.json`)
- remediated decks (`deckir_v1_1.json`, `deckir_v2_1.json`)
- PPTX outputs (`deck_v1.pptx`, `deck_v2.pptx`)
- diagnose outputs (`diagnose_report_v1.json`, `diagnose_report_v2.json`)
- composition specs (`composition_spec_v1.json`, `composition_spec_v2.json`)
- quality gate report (`quality_gates_v2.json`)
- run summary (`run_summary.json`)
- structured logs (`run_log.jsonl`)

## Documentation

- [SPEC.md](SPEC.md): contracts and architecture
- [PLAN.md](PLAN.md): execution plan and next priorities
- [AGENTS.md](AGENTS.md): operating guide for coding agents

