# PPT-Gen: LLM-Assisted PPTX Generator

PPT-Gen generates editable, brand-consistent PowerPoint decks from a content brief and optional visualization cues. It is a research project exploring how to compose presentation-quality slides via a planner / builder / reviewer pipeline backed by a small runtime library.

## Current Status (2026-04-10)

**Active architecture**: `SPEC-v3.md` — planner / builder / reviewer with `ppt_runtime` library and hand-validated example grounding.

**Implementation status**: Foundations phase. No V3 code exists yet. The currently-shipped CLI runs the older V1 placeholder-fill pipeline, retained as a baseline and comparison path during V3 development.

**Source of truth documents**:
- [`SPEC-v3.md`](SPEC-v3.md) — active architecture, contracts, and phase specifications.
- [`PLAN.md`](PLAN.md) — living project board. Current slice, review queue, what's blocked, what's next, backlog. Updated after every working turn.
- [`BRAINSTORM.md`](BRAINSTORM.md) — first-principles derivation behind the current spec.
- [`AGENTS.md`](AGENTS.md) — operating guide for coding agents working on the repo.
- [`SPEC-v2.md`](SPEC-v2.md) — historical recipe-driven architecture (abandoned).

## Architecture At A Glance

```
User input
  → Normalize
  → Planner (LLM #1) — picks archetype + semantic content, no geometry
  → Pre-build enrichment — resolves assets, attaches design system, picks examples
  → Builder (LLM #2) — writes one disposable build_deck.py using ppt_runtime
  → Sandbox execute — subprocess + AST scan + rlimit + RO mounts
  → Deterministic scan — mechanical bugs caught before review
  → Multimodal review (LLM #3) — 8-axis rubric
  → Repair build — regenerate with preserve-list
  → Quality gates → PPTX
```

Key ideas:
- **Planner picks patterns, not coordinates.** Output is semantic (archetype, headline, body). No EMU values, no hex codes.
- **Builder composes against a runtime library.** `ppt_runtime` owns grid math, tokens, text measurement, shape helpers. The builder calls `grid.span(cols=4)`, not `Inches(4.33)`.
- **One deck, one code file, one LLM call.** Cross-slide consistency falls out of the single-call context window.
- **Examples populate archetypes.** Each archetype label is backed by one or more hand-decomposed designer slides stored as runtime code.
- **Mechanical bugs before aesthetic ones.** A deterministic scanner runs before the multimodal reviewer.

## Requirements

- Python 3.10+
- `uv` or `venv` + `pip`
- LLM credentials (`.env` with Azure OpenAI or Gemini) — only needed for LLM-backed phases
- System binaries for review image export:
  - LibreOffice (`soffice`)
  - Poppler (`pdftoppm`)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

macOS binaries for review image export:

```bash
brew install --cask libreoffice
brew install poppler
```

Codex cloud bootstrap:

```bash
./scripts/setup_codex_cloud.sh
```

## CLI (current V1 path — baseline)

The current CLI commands reflect the V1 placeholder pipeline. They will continue to work as a baseline during V3 development.

```bash
# validate template against layout catalog
python -m src.cli validate

# render a DeckIR JSON to PPTX
python -m src.cli render --deckir inputs/sample_deckir.json

# smoke: deterministic validate → preflight → render
python -m src.cli smoke --deckir inputs/sample_deckir.json

# single-pass generation (LLM planner → render, no review loop)
python -m src.cli generate --input inputs/legacy-system-navigator.combined.md --run-id run_single

# full automated one-loop run with multimodal review
python -m src.cli generate-auto --input inputs/legacy-system-navigator.combined.md --run-id run_auto
```

V3 CLI entry points (`--mode v3`) will land in SLICE-013. See `PLAN.md`.

## Run Artifacts (current V1)

Each run writes to `runs/<run_id>/`:
- planner outputs (`planner_deckir_v1.json`, `planner_deckir_v2.json`)
- remediated decks (`deckir_v1_1.json`, `deckir_v2_1.json`)
- PPTX outputs (`deck_v1.pptx`, `deck_v2.pptx`)
- diagnose reports (`diagnose_report_v1.json`, `diagnose_report_v2.json`)
- composition specs (`composition_spec_v1.json`, `composition_spec_v2.json`)
- quality gate report (`quality_gates_v2.json`)
- run summary (`run_summary.json`)
- structured logs (`run_log.jsonl`)

V3 artifacts (`deck_plan.json`, `builder_input.json`, `build_attempts/`, `build_deck.py`, `geometry_report_v*.json`, `review_feedback_v*.json`) are specified in `SPEC-v3.md §8` and will land as V3 slices ship.

## Project Board

For current slice, review queue, what's blocked, and what's next, see [`PLAN.md`](PLAN.md). It is the authoritative state of the project at any given time.

## Roadmap (high-level)

- **Now**: V3 foundations — audit, cleanup, design system, runtime library, sandbox, scanner.
- **Next**: example library seeding (needs designer slides from user).
- **After**: planner, builder, reviewer, quality gates, CLI wiring, benchmark.
- **Backlog**: architecture diagram generation, hosted multi-user deployment, automatic design system derivation. See `PLAN.md` backlog section.
