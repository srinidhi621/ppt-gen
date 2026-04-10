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
- planner metadata/policy ingestion for stronger visual routing + diversity constraints

Known gap:
- composition polish is still below target quality for consulting-style decks.
- visual coverage is now enforced, but visual storytelling quality still needs stronger per-slide composition logic.

Active redesign (`2026-04-09`):
- `SPEC-v3.md` is now the active architecture target.
- V3 shifts the repo toward `planner -> primitive-code builder -> multimodal reviewer`.
- The builder phase is intended to generate disposable `python-pptx` code that composes slides from native primitives on blank/header-only template canvases.
- The current implementation in this repo is still the older placeholder/layout-bound path until V3 lands.

Latest progress (`2026-03-02`):
- Added planner metadata catalogs:
  - `assets/catalog/component_catalog_v1.json`
  - `assets/catalog/component_examples_v1.json`
  - `assets/catalog/planner_policy_v1.json`
  - `assets/catalog/template_style_baselines_v1.json`
- Added benchmark manifest: `assets/benchmarks/benchmark_manifest_v1.json`
- Wired planner prompt to component metadata + policy constraints via:
  - `src/assets.py` (`load_component_catalog`, `load_planner_policy`)
  - `src/llm/planner.py` (`_build_system_prompt` policy sections/rules)
- Added tests:
  - `tests/test_assets_metadata.py`
  - `tests/test_planner_prompt_metadata.py`
- Added DeckIR v2 fixture scaffold: `tests/fixtures/deckir_v2/README.md`

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

Codex cloud bootstrap:

```bash
./scripts/setup_codex_cloud.sh
```

macOS binaries:

```bash
brew install --cask libreoffice
brew install poppler
```

## Codex Cloud

Use `main` as the repo ref for cloud tasks. This repository does not use `master` as its primary branch.

Recommended task entry points:

```bash
./scripts/setup_codex_cloud.sh
./scripts/test_codex_cloud.sh
```

Notes:
- full LLM-backed generation still requires `.env` credentials
- review-image export still requires `soffice` and `pdftoppm`
- `./scripts/test_codex_cloud.sh` is the safe default verification command for cloud tasks

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

Builder sandbox execution (V3 S1 slice):

```bash
python -m src.cli builder-exec \
  --builder-code alternate-approach/build.py \
  --builder-input runs/demo/builder_input_v1.json \
  --run-id run_builder_sandbox
```

## Run Artifacts

Each run writes to `runs/<run_id>/`, including:
- planner artifacts (`planner_deckir_v1.json`, `planner_deckir_v2.json`)
- remediated decks (`deckir_v1_1.json`, `deckir_v2_1.json`)
- PPTX outputs (`deck_v1.pptx`, `deck_v2.pptx`)
- diagnose outputs (`diagnose_report_v1.json`, `diagnose_report_v2.json`)
- composition specs (`composition_spec_v1.json`, `composition_spec_v2.json`)
- quality gate report (`quality_gates_v2.json`)
- builder execution report (`build_exec_report_v1.json`) and attempt artifacts under `build_attempts/`
- run summary (`run_summary.json`)
- structured logs (`run_log.jsonl`)

## Documentation

- [SPEC-v3.md](SPEC-v3.md): active architecture for planner -> builder -> reviewer primitive composition
- [SPEC-v2.md](SPEC-v2.md): historical V2 recipe-driven architecture
- [PLAN.md](PLAN.md): active execution plan and rollout slices
- [AGENTS.md](AGENTS.md): operating guide for coding agents
