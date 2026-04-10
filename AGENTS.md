# AGENTS.md — Operating Guide

This repo generates editable PPTX via a planner / builder / reviewer pipeline backed by a small runtime library. This document is the operating guide for coding agents working on the repo. For architecture, read `SPEC-v3.md`. For current state, read `PLAN.md`.

## Source of Truth

- `SPEC-v3.md` — active architecture. Do not design around it without updating it first.
- `PLAN.md` — living project board. Current slice, review queue, blockers, backlog. **Update after every working turn.**
- `BRAINSTORM.md` — first-principles derivation. Historical context for why the spec looks the way it does.
- `SPEC-v2.md` — abandoned recipe-engine direction, kept for historical context.
- `README.md` — user-facing status and CLI.

## Operating Rules

### Rule 1 — Work in reviewable slices
The user operates this project in agile mode. One thin slice at a time. Every slice ends at an explicit review gate. Do not batch multiple slices before a review. Do not start the next slice without updating `PLAN.md` with the result of the current slice.

### Rule 2 — Update PLAN.md after every turn
`PLAN.md` is the jira board. It has to be accurate at all times. After any meaningful action:
- Move slices between sections (Active → Completed, Up Next → Active, etc.).
- Append to the changelog with a dated one-liner.
- Add anything the user asked for that wasn't already captured.
- Move items out of the Review Queue when the user has approved them.

### Rule 3 — No going blind on major actions
The user has made this explicit: every major task should be verified by them. That means:
- Deletions are always review-gated. Propose the keep/delete matrix in chat, wait for approval, then execute.
- Architectural changes require `SPEC-v3.md` updates first, then implementation.
- Any file added to or removed from the repo should be visible in a diff the user can read.
- Any new dependency is a review gate — ask before adding to `requirements.txt`.
- Destructive git operations (reset --hard, force push, branch deletion) require explicit user authorization for that specific action.

### Rule 4 — Scope discipline
Do only what the current slice asks for. Do not add features, refactor adjacent code, or introduce abstractions beyond what the slice requires. If you discover a needed change outside the current slice, note it in `PLAN.md` under Up Next or Backlog — do not implement it.

### Rule 5 — V3 is the target; V1 is the baseline
The current CLI runs the V1 placeholder pipeline. V1 code is kept as a baseline and comparison path during V3 development. Do not delete V1 code without a review gate. Once V3 ships and is approved by the user as the default, V1 may be retired — but that is its own slice.

### Rule 6 — Non-negotiable constraints from SPEC-v3.md
These are not opinions. They are spec requirements:
- Output is native editable PPTX. No rasterized slide bodies.
- Render and review are headless. No GUI automation.
- Render-path images are PNG/JPG/WebP. SVG stays in source catalogs only.
- Builder code runs only in the sandbox.
- Builder code uses `tokens.color(...)` and `tokens.type(...)`. No hex literals. No inline font sizes.
- Builder code uses `grid.span(...)` and canvas anchors. Inch literals are permitted only inside a small allowlist (spacing constants under `Inches(0.25)`).
- Markdown markers (`**`, `*`) must render as formatted runs, not leak as literal characters.

### Rule 7 — `python-pptx` does not autofit
Protect readability through planner density budgets, `measure_text` at build time, and the deterministic post-build scanner — not by hoping PowerPoint will do it.

### Rule 8 — The sandbox bar is explicit
Subprocess + AST pre-scan + `resource.setrlimit` + read-only asset bind mounts. No VM, no Firecracker, no container service. Anything beyond that for local development is yak-shaving.

## Pipeline (Target V3)

```
User Input
  → Phase 1: Normalize
  → Phase 2: Planner (LLM #1) — archetype + semantic content
  → Phase 3: Pre-build enrichment — assets, design system, examples
  → Phase 4: Builder (LLM #2) — writes build_deck.py using ppt_runtime
  → Phase 5: Sandbox execute
  → Phase 6: Deterministic post-build scan
      └ mechanical fail → Repair build loop
  → Phase 7: Review image export (soffice + pdftoppm)
  → Phase 8: Multimodal review (LLM #3, 8-axis rubric)
      └ aesthetic fail → Repair build loop
  → Phase 10: Quality gates
  → Stop
```

`Phase 0: Design System` is a one-time per-template artifact (`assets/template/design_system.json`), not part of the per-run flow.

## Pipeline (Current V1 Baseline)

```
User Input → Planner V1 → Compose+Render V1 → Diagnose+Review Images
  → Multimodal Review → Planner V2 → Compose+Render V2
  → Quality Gates → Stop
```

Entry point: `python -m src.cli generate-auto --input <combined.md> --run-id <id>`.

## Repository Conventions

### Paths

**Existing (V1 era)**:
- template: `assets/template/template.pptx`
- canvas config: `assets/template/canvas_config.json`
- token overrides: `assets/template/token_overrides.json`
- layout catalog: `assets/layout/layout_catalog.json`
- icon index: `assets/icons/icons.json`
- icon PNGs: `assets/icons/png/external/{pack}/`
- visual vocabulary: `assets/catalog/visual_vocabulary.json`
- branded images: `assets/catalog/branded_images.json`
- fonts: `assets/fonts/` (substitute fonts) + `assets/fonts/font_map.json`
- runs: `runs/<run_id>/`
- review images: `runs/<run_id>/review_images/v1/slide_*.png`

**V3 additions (as they land)**:
- design system: `assets/template/design_system.json` (SLICE-003)
- runtime library: `src/ppt_runtime/` (SLICE-004 onward)
- example library: `examples/<archetype>_<slug>.py` + `examples/source/<archetype>_<slug>.pptx` + `examples/<archetype>_<slug>.json` (SLICE-007)
- sandbox: `src/sandbox/` (SLICE-009)
- scanner: `src/scan/` (SLICE-008)
- V3 pipeline: `src/v3/` (SLICE-010 onward)

### Run Artifacts (target V3)

Per `SPEC-v3.md §8`:
- `normalized_content.json`
- `deck_plan.json` (planner output)
- `builder_input.json`
- `build_attempts/attempt_NN/{build_deck.py, build_exec_report.json, deck.pptx}`
- `deck.pptx` (copy of the accepted attempt at run root)
- `geometry_report_v{N}.json`
- `review_images/v{N}/slide_*.png`
- `review_feedback_v{N}.json`
- `quality_gates.json`
- `run_summary.json`
- `run_log.jsonl`

### Logging Stages

Per `SPEC-v3.md §9`. Stage markers include `NORMALIZE_DONE`, `PLANNER_DONE`, `ENRICHMENT_DONE`, `BUILD_ATTEMPT_STARTED/FAILED`, `BUILD_EXEC_DONE`, `GEOMETRY_SCAN_DONE`, `GEOMETRY_BLOCKING_FAILURE`, `REVIEW_IMAGES_READY`, `REVIEW_DONE`, `REPAIR_BUILD_TRIGGERED/DONE`, `QUALITY_GATES_PASS/FAIL`, `RUN_COMPLETE`, `RUN_FAILED_BUILD`, `RUN_FAILED_QUALITY_GATES`.

### Testing Expectations

- `python -m pytest -q` before pushing.
- Unit tests per module; integration tests per slice that crosses module boundaries.
- No pixel-perfect visual diff tests.
- Mock LLM clients; do not hit the API in unit tests.
- Every runtime change must pass the full example library regression (once SLICE-007 has produced one).

### Codex Cloud

- Default branch is `main`. Use `main`, not `master`.
- Bootstrap: `./scripts/setup_codex_cloud.sh`
- Verification: `./scripts/test_codex_cloud.sh`
- LLM-backed phases still require `.env` credentials.
- Review image export still requires `soffice` and `pdftoppm` on the cloud worker.

## Do Not Do

- Do not introduce an arbitrary x/y auto-layout engine. Use the grid primitive.
- Do not rely on PowerPoint autofit.
- Do not bypass schema validation for LLM outputs.
- Do not skip artifact persistence under `runs/<run_id>/`.
- Do not commit generated `build_deck.py` files. They belong in runs, not in the repo.
- Do not delete V1 code without an explicit review gate.
- Do not design new architecture without updating `SPEC-v3.md` and `PLAN.md` first.
- Do not batch multiple slices before a review.
- Do not skip updating `PLAN.md` after a turn.

## Content Quality Contract

The `assets/presentation-writing.skill` archive contains the authoritative content-quality rules for planner output: kill-on-sight AI lexicon, per-slide review checklist, audience awareness, argument spine discipline. When building the planner (SLICE-010), embed the skill's rules as hard constraints in the planner system prompt and as criteria on the reviewer's `message_clarity` axis. The skill owns copy quality; the runtime owns layout; they do not overlap.

## Active Priority

Phase 1 of `SPEC-v3.md §11` — foundations. Current slice and review queue live in `PLAN.md`.
