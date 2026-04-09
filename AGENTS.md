# AGENTS.md — Operating Guide (LLM-Assisted PPTX Generator)

This repo builds an automated PPTX generation system using:
- `python-pptx` deterministic rendering
- template-anchored slide composition
- planner + primitive-code builder + multimodal reviewer
- deterministic validation, composition metadata, and quality gates

Agent rule: do not invent new architecture without updating `SPEC-v3.md`, `SPEC-v2.md` status notes, and `PLAN.md`.

## 0) Source of Truth Artifacts

- `SPEC-v3.md` — active architecture + contracts
- `SPEC-v2.md` — historical recipe-driven architecture
- `PLAN.md` — active execution plan
- `README.md` — user-facing usage and setup
- `assets/template/template.pptx`
- `assets/layout/layout_catalog.json`
- `assets/icons/icons.json`
- `assets/catalog/asset_catalog.json`
- `assets/catalog/visual_vocabulary.json`
- `assets/catalog/branded_images.json`
- `assets/catalog/component_catalog_v1.json`
- `assets/catalog/component_examples_v1.json`
- `assets/catalog/planner_policy_v1.json`
- `assets/catalog/template_style_baselines_v1.json`
- `assets/benchmarks/benchmark_manifest_v1.json`
- `inputs/`
- `runs/<run_id>/`

## 0.1) Progress Snapshot (`2026-04-09`)

Recently landed:
- active V3 architecture reset in `SPEC-v3.md`
- execution plan rewritten around planner -> builder -> reviewer
- V2 spec retained as historical context rather than active target

## 1) Non-Negotiable Constraints

### 1.1 No Auto-Layout Assumptions
`python-pptx` does not auto-fit like PowerPoint UI.
Preflight validation must protect readability before render.

### 1.2 Template-Anchored Primitive Composition
Use template masters, theme tokens, and approved canvas layouts.
Do not constrain new generation paths to placeholder binding when primitive composition is the intended route.

### 1.3 Placeholder Binding Contract
When placeholders are used, binding is by placeholder alt-text `field_key` (`shape.alt_text == field_key`).
Do not rely on placeholder index ordering.
Primitive-composed slides may use blank or header-only canvases and add native objects directly.

### 1.4 Image/Icon Format
Render path supports raster assets (PNG/JPG/WebP).
Do not introduce SVG in render path.

### 1.5 Review Image Generation
Default automated conversion is headless:
- `soffice` (PPTX->PDF)
- `pdftoppm` (PDF->PNG slides)

Do not use AppleScript/PowerPoint GUI automation in core pipeline.

### 1.6 Markdown Markers
Markdown inline markers (`**`, `*`) must be rendered as text-run formatting, not leaked literally.

## 2) Pipeline

Current implemented pipeline:

`User Input -> Planner V1 -> Compose+Render V1 -> Diagnose+Review Images -> Multimodal Review -> Planner V2 -> Compose+Render V2 -> Quality Gates -> Stop`

Target V3 pipeline:

`User Input -> Planner -> Builder Attempts -> Execute Primitive Composition Code -> Diagnose+Review Images -> Multimodal Review -> Builder Repair -> Quality Gates -> Stop`

Key command:
- `python -m src.cli generate-auto --input <combined.md> --run-id <id>`

## 3) Repository Conventions

### 3.1 Paths
- template: `assets/template/template.pptx`
- layout catalog: `assets/layout/layout_catalog.json`
- runs: `runs/<run_id>/`
- review images: `runs/<run_id>/review_images/v1/slide_*.png`

### 3.3 Codex Cloud
- default branch is `main`
- if a cloud task asks for a git ref, use `main`, not `master`
- bootstrap command: `./scripts/setup_codex_cloud.sh`
- verification command: `./scripts/test_codex_cloud.sh`

### 3.2 Run Artifacts (minimum)
- current pipeline artifacts: `planner_deckir_v1.json`, `planner_deckir_v2.json`, `deck_v1.pptx`, `deck_v2.pptx`, `composition_spec_v1.json`, `composition_spec_v2.json`
- V3 target additions: `deck_blueprint_v1.json`, `builder_input_v1.json`, `build_deck_v1.py`, `build_exec_report_v1.json`
- diagnose: `diagnose_report_v1.json`, `diagnose_report_v2.json`
- quality gates: `quality_gates_v2.json` or `quality_gates_v3.json`
- summary: `run_summary.json`
- logs: `run_log.jsonl`

## 4) Logging Contract

`run_log.jsonl` should include stage markers such as:
- `NORMALIZE_DONE`
- `PLAN_V1_DONE` or `PLANNER_DONE`
- `VALIDATE_V1_DONE`
- `RENDER_V1_DONE` or `BUILD_EXEC_V1_DONE`
- `REVIEW_IMAGES_INGESTED`
- `DIAGNOSE_V1_DONE`
- `MULTIMODAL_REVIEW_DONE`
- `PLAN_V2_DONE` or `REPAIR_BUILD_ATTEMPT_STARTED`
- `VALIDATE_V2_DONE`
- `RENDER_V2_DONE` or `BUILD_EXEC_V2_DONE`
- `DIAGNOSE_V2_DONE`
- `QUALITY_GATES_V2` or `QUALITY_GATES_V3`
- `RUN_COMPLETE`, `RUN_FAILED_BUILD`, or `RUN_FAILED_QUALITY_GATES`

## 5) Quality Gates

Final V2 gate checks:
- no blocking overflow
- image-layout visual coverage
- no hero icon misuse
- no markdown marker leaks
- minimum deck visual density
- minimum image-asset presence

## 6) Testing Expectations

Before pushing changes:
- `python -m pytest -q`
- run targeted integration command(s) when pipeline behavior is changed

Do not add pixel-perfect visual tests.

## 7) Do Not Do

- do not add arbitrary x/y auto-layout engine
- do not rely on PowerPoint autofit
- do not bypass schema validation for LLM outputs
- do not skip artifact persistence under `runs/<run_id>/`

## 8) Active Priority

Current focus is landing the V3 runtime:
- planner outputs builder-ready slide briefs
- builder composes slides from native primitives using disposable code
- multimodal review drives bounded repair
