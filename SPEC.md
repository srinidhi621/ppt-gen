# SPEC.md — One-Loop Deck Generation Contract

## 0) Status
- Date: 2026-02-27
- Scope: implemented end-to-end one-loop pipeline with deterministic validation/rendering
- Output: editable `.pptx` (`deck_v2.pptx`)

Canonical flow:

`User Input -> Planner V1 -> Compose+Render V1 -> Diagnose+Review Images -> Multimodal Review -> Planner Rework V2 -> Compose+Render V2 -> Quality Gates -> Stop`

## 1) Pipeline Contract

### 1.1 Loop policy
- Max loops: `1`
- Max planner calls: `2` (V1, V2)
- Max review calls: `1`
- Total LLM calls per run: `3`

### 1.2 Stage outputs
1. Normalize:
- `content.md`
- `cues.json`
2. Planner V1:
- `planner_deckir_v1.json`
3. Deterministic V1:
- `deckir_v1_1.json`
- `validation_report_v1.json`
- `validation_report_v1_post.json`
- `composition_spec_v1.json`
- `deck_v1.pptx`
- `render_map_v1.json`
4. Review evidence:
- `review_images/v1/slide_*.png`
- `diagnose_report_v1.json`
5. Reviewer:
- `review_feedback_v1.json`
6. Planner V2:
- `planner_deckir_v2.json`
7. Deterministic V2:
- `deckir_v2_1.json`
- `validation_report_v2.json`
- `validation_report_v2_post.json`
- `composition_spec_v2.json`
- `deck_v2.pptx`
- `render_map_v2.json`
- `diagnose_report_v2.json`
8. Final checks:
- `quality_gates_v2.json`
- `run_summary.json`

## 2) Deterministic vs Non-Deterministic Boundary

Non-deterministic:
1. Planner V1 (LLM)
2. Multimodal review (LLM)
3. Planner V2 rework (LLM)

Deterministic:
1. input splitting + normalization
2. visual fill and relayout safety net
3. preflight remediation and post-validation
4. rendering
5. diagnose
6. review image conversion/ingestion
7. quality gates

## 3) Planner Contract

Planner emits schema-valid `DeckIR` only:
- allowed `layout_id`
- allowed `field_key`s for chosen layout
- valid `asset_refs`

Cue usage requirements:
- `layout_hint` honored when valid
- `icon_hints`, `image_hint`, and cue `notes` considered first-class
- image-capable layouts require non-empty visual plan

## 4) Deterministic Visual Fill + Relayout

After planner output, deterministic pass enforces visual feasibility:
- upgrades non-image layouts to image-capable sibling layouts when cues indicate visual-heavy intent
- remaps fields safely during layout upgrade
- applies image-first policy for cue-rich slides
- uses branded-image fallback resolution when icon-only output is weak
- logs unresolved visual attempts via `VISUAL_CUE_UNRESOLVED`

Current behavior:
- one primary visual asset per slide image slot (`ph_image*`)
- no freeform multi-object visual composition engine yet

## 5) CompositionSpec Contract

`CompositionSpec` is persisted for V1 and V2:
- per slide:
  - `slide_id`, `layout_id`, `archetype`
  - `text_blocks[]` with `overflow_action`
  - `visual_blocks[]` with `role` and `placement_mode`
  - `notes_additions[]`
  - `fit_diagnostics.before/after/remediations`

This spec is deterministic and used for diagnostics/comparison.

## 6) Review Image Conversion

Default exporter:
- `soffice` headless converts `deck_v1.pptx` -> PDF
- `pdftoppm` converts PDF -> PNG slides
- normalized naming: `slide_001.png`, ...

Hard checks before review call:
- expected image count match
- deterministic ordering
- minimum width threshold

## 7) Quality Gates (V2)

Run fails if any gate fails:
1. `no_blocking_overflow`
2. `visual_coverage_image_layouts`
3. `no_icon_hero_stretch`
4. `no_markdown_marker_leak`
5. `min_visual_density` (>= 50% of slides)
6. `min_image_asset_presence` (>= 20% of slides, minimum 1)

## 8) Logging Contract

`run_log.jsonl` must include:
- `NORMALIZE_DONE`
- `PLANNER_CONTEXT_DONE`
- `PLAN_V1_DONE`
- `VALIDATE_V1_DONE`
- `RENDER_V1_DONE`
- `REVIEW_IMAGES_INGESTED`
- `DIAGNOSE_V1_DONE`
- `QUALITY_GATES_V1`
- `MULTIMODAL_REVIEW_DONE`
- `PLAN_V2_DONE`
- `VALIDATE_V2_DONE`
- `RENDER_V2_DONE`
- `DIAGNOSE_V2_DONE`
- `QUALITY_GATES_V2`
- `RUN_COMPLETE` or `RUN_FAILED_QUALITY_GATES`

## 9) Known Limitations

1. Layout catalog has limited native image-capable templates.
2. Current renderer does not compose multi-object diagram scenes on a single slide.
3. Quality can still degrade into repetitive branded-image usage without stronger narrative composition rules.

## 10) Out of Scope (Current)

1. More than one review loop.
2. Arbitrary x/y freeform auto-layout engine.
3. PowerPoint AppleScript automation.
4. SmartArt/animation/chart auto-generation.

