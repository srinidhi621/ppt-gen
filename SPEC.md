# SPEC.md - One-Loop Planner/Reviewer Architecture

## 0) Status
- Date: 2026-02-27
- Owner: project maintainer
- Scope: end-to-end pipeline overhaul with exactly one review loop
- Renderer: `python-pptx`
- Output: editable `.pptx`

This specification defines a fixed one-loop workflow:

`User Input -> Planner V1 -> Compose+Render V1 -> Slide Images + Diagnose -> Multimodal Review -> Planner Rework V2 -> Compose+Render V2 -> Stop`

---

## 1) Pipeline Contract

## 1.1 Canonical Run Flow
1. Normalize input (`content.md`, `cues.json`, `ContentModel`).
2. LLM Planner V1 outputs `planner_deckir_v1.json`.
3. Deterministic stages produce first draft:
- resolver -> `resolved_deckir_v1.json`
- composer -> `composition_spec_v1.json`
- preflight -> `deckir_v1_1.json`, `validation_report_v1.json`
- renderer -> `deck_v1.pptx`, `render_map_v1.json`
4. Generate review evidence:
- `diagnose_report_v1.json`
- slide images for V1 in `review_images/v1/`
5. Multimodal LLM Reviewer outputs `review_feedback_v1.json`.
6. LLM Planner Rework V2 consumes original ask + review feedback and outputs `planner_deckir_v2.json`.
7. Deterministic stages render final:
- resolver/composer/preflight/render
- `deck_v2.pptx`, `render_map_v2.json`, `validation_report_v2.json`
8. Stop. No second loop.

## 1.2 Loop Policy
- Maximum loops: 1.
- Maximum planner calls: 2 (`V1`, `V2 rework`).
- Maximum reviewer calls: 1 (multimodal review after V1 render).
- Total LLM calls per run: 3.

---

## 2) Determinism Boundary

Non-deterministic stages:
1. Planner V1
2. Multimodal Reviewer
3. Planner Rework V2

Deterministic stages:
1. context pack generation
2. resolver
3. composer
4. preflight remediation
5. renderer
6. diagnose script
7. review image ingestion/validation

Given the same inputs and LLM outputs, deterministic stages must produce identical outputs.

---

## 3) Slide Image Conversion Stage (Required)

A review image stage is mandatory between V1 render and multimodal review.

## 3.1 Clean Export Design
Implement a pluggable `SlideImageExporter` interface with two modes:

1. `libreoffice_headless` (default):
- convert `deck_v1.pptx` -> PDF using `soffice --headless`.
- convert PDF -> per-slide PNG using `pdftoppm`.
- normalize filenames to `slide_001.png`, `slide_002.png`, ... under `runs/<run_id>/review_images/v1/`.
- fail fast if required binaries are missing.

2. `manual_powerpoint` (fallback for local debugging only):
- user exports slide images from PowerPoint UI into the same target directory.
- ingestion validation remains identical.

## 3.2 Image Ingestion Requirements
- One image per slide, deterministic order by slide index.
- Minimum resolution threshold (configurable, e.g., >= 1600px width).
- Missing/misordered images cause hard failure before reviewer call.

---

## 4) Planner Architecture

## 4.1 Planner V1 Input
- original user ask
- `ContentModel`
- `cues.json`
- `PlannerContextPack` (deterministic feasible options)
- layout capabilities and fit budgets
- asset capability manifest

## 4.2 Planner V1 Output Contract (`PlannerDeckIR`)
Per slide:
- `slide_id`
- `section_id`
- `layout_id`
- `fields`
- `speaker_notes`
- `visual_plan`:
  - `archetype`
  - `selected_candidate_ids[]`
  - `cue_trace`

Rules:
- candidate IDs must come from context pack only.
- no raw hallucinated asset references.

## 4.3 Planner Rework V2 Input
Planner rework must receive two separate channels:
1. `original_request` (immutable)
2. `review_feedback` (separate structured object)

Also include:
- `planner_deckir_v1.json`
- `composition_spec_v1.json`
- `diagnose_report_v1.json`
- capability manifest (layout + assets + renderer limits)

Planner must treat `review_feedback` as delta instructions, not replacement of original ask.

## 4.4 Planner Rework V2 Output
- full `planner_deckir_v2.json` (not partial free text)
- each changed slide includes `change_rationale` and `feedback_refs[]`

---

## 5) Review Architecture

## 5.1 Multimodal Reviewer Input Bundle
Reviewer call must include:
1. original ask (`content.md`, `cues.json`)
2. planned output (`planner_deckir_v1.json`)
3. composed output (`composition_spec_v1.json`)
4. actual output diagnostics (`diagnose_report_v1.json`)
5. rendered evidence:
- `deck_v1.pptx` metadata summary
- slide images (`review_images/v1/*.png`)
6. capability manifest:
- allowed layouts/fields
- available assets/candidate lists
- renderer constraints

## 5.2 Reviewer Output Contract (`ReviewFeedback`)
Required fields:
- `summary`
- `slide_findings[]`
  - `slide_id`
  - `severity` (`S0`..`S3`)
  - `finding_type` (`overflow`, `visual_mismatch`, `hierarchy`, `density`, `asset_choice`, etc.)
  - `expected`
  - `observed`
  - `evidence_refs` (image index, diagnose field)
- `change_requests[]`
  - `target_stage` (`planner` only for this loop)
  - `instruction`
  - `constraint_refs`
  - `must_preserve[]`

Reviewer must stay within project capabilities and avoid requests outside available layouts/assets/rendering behavior.

---

## 6) CompositionSpec Contract

`CompositionSpec` is deterministic and consumed by renderer.

Per slide, include:
- `slide_id`, `layout_id`, `archetype`
- `text_blocks[]`:
  - `field_key`
  - `text`
  - `font_size_pt`
  - `line_spacing_pt`
  - `overflow_action`
- `visual_blocks[]`:
  - `target_field_key`
  - `asset_ref`
  - `role` (`hero`, `primary`, `secondary`, `accent`)
  - `placement_mode` (`fill`, `contain`, `centered_icon`, `grid`)
  - size caps where applicable
- `notes_additions[]`
- `fit_diagnostics` (`before`, `after`, `remediations`)

---

## 7) Diagnose Stage Contract

Diagnose script must emit machine-readable JSON:
- per slide:
  - planned layout/fields/assets
  - actual bound shapes/text/images
  - overflow checks
  - expected vs actual visual gaps
- deck summary metrics

Artifacts:
- `diagnose_report_v1.json`
- `diagnose_report_v2.json`

Human-readable stdout can remain, but JSON is required for reviewer and gates.

---

## 8) Logging and Artifacts

## 8.1 Required Run Artifacts
- `content.md`
- `cues.json`
- `planner_context.json`
- `planner_deckir_v1.json`
- `resolved_deckir_v1.json`
- `composition_spec_v1.json`
- `deck_v1.pptx`
- `render_map_v1.json`
- `validation_report_v1.json`
- `diagnose_report_v1.json`
- `review_images/v1/slide_*.png`
- `review_feedback_v1.json`
- `planner_deckir_v2.json`
- `resolved_deckir_v2.json`
- `composition_spec_v2.json`
- `deck_v2.pptx`
- `render_map_v2.json`
- `validation_report_v2.json`
- `diagnose_report_v2.json`
- `run_log.jsonl`

## 8.2 Required Log Events
- `NORMALIZE_DONE`
- `PLANNER_CONTEXT_DONE`
- `PLAN_V1_DONE`
- `RESOLVE_V1_DONE`
- `COMPOSE_V1_DONE`
- `VALIDATE_V1_DONE`
- `RENDER_V1_DONE`
- `REVIEW_IMAGES_READY`
- `REVIEW_IMAGES_INGESTED`
- `DIAGNOSE_V1_DONE`
- `MULTIMODAL_REVIEW_DONE`
- `PLAN_V2_DONE`
- `RESOLVE_V2_DONE`
- `COMPOSE_V2_DONE`
- `VALIDATE_V2_DONE`
- `RENDER_V2_DONE`
- `DIAGNOSE_V2_DONE`
- `RUN_COMPLETE`

---

## 9) Quality Gates

Gate after V1 (before review):
- V1 render successful.
- review images valid and complete.
- diagnose JSON generated.

Gate after V2 (final):
- no blocking overflow.
- no missing visual in image-capable layouts unless explicit unresolved log exists.
- no icon-stretch misuse in hero slots.
- markdown markers not visible in slide text.

---

## 10) Acceptance Criteria

A successful run must:
1. Follow the exact one-loop pipeline with no additional loops.
2. Produce final `deck_v2.pptx` and full artifact set.
3. Show measurable improvement from V1 to V2 on diagnosed quality metrics.
4. Stay within layout/asset/render constraints of this repo.

---

## 11) Out of Scope
- More than one review loop.
- Freeform layout engine outside template semantics.
- AppleScript-based GUI automation for image export.
