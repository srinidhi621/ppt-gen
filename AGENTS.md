# AGENTS.md — Operating Guide (LLM-Assisted PPTX Generator)

This repo builds an automated PPTX generation system using:
- `python-pptx` deterministic rendering
- template-first layout and placeholder binding
- LLM planning + one multimodal review loop
- deterministic validation, composition metadata, and quality gates

Agent rule: do not invent new architecture without updating `SPEC-v2.md` and `PLAN.md`.

## 0) Source of Truth Artifacts

- `SPEC-v2.md` — architecture + contracts
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

## 0.1) Progress Snapshot (`2026-03-02`)

Recently landed:
- planner metadata loaders for component catalog + policy
- planner prompt sections for component guidance and diversity policy constraints
- benchmark manifest seed and planner metadata catalogs
- tests for metadata loading + planner prompt metadata wiring
- DeckIR v2 fixture directory scaffold

## 1) Non-Negotiable Constraints

### 1.1 No Auto-Layout Assumptions
`python-pptx` does not auto-fit like PowerPoint UI.
Preflight validation must protect readability before render.

### 1.2 Template-First Rendering
Use template masters/layouts/placeholders.
Do not hardcode ad-hoc typography or color styling unless explicitly required.

### 1.3 Placeholder Binding Contract
Binding is by placeholder alt-text `field_key` (`shape.alt_text == field_key`).
Do not rely on placeholder index ordering.

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

## 2) Implemented Pipeline

`User Input -> Planner V1 -> Compose+Render V1 -> Diagnose+Review Images -> Multimodal Review -> Planner V2 -> Compose+Render V2 -> Quality Gates -> Stop`

Key command:
- `python -m src.cli generate-auto --input <combined.md> --run-id <id>`

## 3) Repository Conventions

### 3.1 Paths
- template: `assets/template/template.pptx`
- layout catalog: `assets/layout/layout_catalog.json`
- runs: `runs/<run_id>/`
- review images: `runs/<run_id>/review_images/v1/slide_*.png`

### 3.2 Run Artifacts (minimum)
- planner decks: `planner_deckir_v1.json`, `planner_deckir_v2.json`
- remediated decks: `deckir_v1_1.json`, `deckir_v2_1.json`
- render outputs: `deck_v1.pptx`, `deck_v2.pptx`
- composition specs: `composition_spec_v1.json`, `composition_spec_v2.json`
- diagnose: `diagnose_report_v1.json`, `diagnose_report_v2.json`
- quality gates: `quality_gates_v2.json`
- summary: `run_summary.json`
- logs: `run_log.jsonl`

## 4) Logging Contract

`run_log.jsonl` should include stage markers such as:
- `NORMALIZE_DONE`
- `PLAN_V1_DONE`
- `VALIDATE_V1_DONE`
- `RENDER_V1_DONE`
- `REVIEW_IMAGES_INGESTED`
- `DIAGNOSE_V1_DONE`
- `MULTIMODAL_REVIEW_DONE`
- `PLAN_V2_DONE`
- `VALIDATE_V2_DONE`
- `RENDER_V2_DONE`
- `DIAGNOSE_V2_DONE`
- `QUALITY_GATES_V2`
- `RUN_COMPLETE` or `RUN_FAILED_QUALITY_GATES`

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

Current focus is composition quality recovery:
- improve cue-to-visual intent mapping
- reduce repetitive visual asset usage
- increase slide-level narrative polish and hierarchy quality
