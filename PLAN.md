# PLAN.md - One-Loop Review Pipeline Implementation Plan

## 0) Objective
Implement exactly this runtime flow:

`User Input -> LLM Planner V1 -> Compose+Render V1 -> Diagnose+Slide Images -> Multimodal Review -> LLM Planner Rework V2 -> Compose+Render V2 -> Stop`

Constraints:
- Max loops: 1
- Max planner calls: 2
- Max reviewer calls: 1
- Total LLM calls per run: 3

---

## 1) Current Gaps to Close

1. Review is not yet a first-class stage with strict contracts.
2. Diagnose output is mostly terminal text; reviewer needs machine-readable JSON.
3. Slide-image conversion stage is not formalized as a required pipeline step.
4. Planner rework mode is not formalized as separate input channel from original ask.
5. End-to-end orchestration for V1->Review->V2 is missing.

---

## 2) Phase Plan (Iterative MVP)

## Phase 1 - Contracts and Artifact Plumbing

Goal:
- Add all schemas and artifact conventions needed for one-loop execution.

Work:
1. Add/extend models:
- `PlannerContextPack`
- `PlannerDeckIR`
- `ReviewFeedback`
- `CompositionSpec`
2. Add artifact naming/versioning for V1/V2 outputs.
3. Add log event constants for V1 and V2 stages.

Deliverables:
- schema models in `src/models/`
- V1/V2 artifact writers in pipeline orchestration

Exit criteria:
- schema validation tests pass,
- run directory contains deterministic V1/V2 filenames.

---

## Phase 2 - Diagnose JSON + Review Evidence Stage

Goal:
- Produce deterministic review evidence after V1 render.

Work:
1. Upgrade `scripts/diagnose_pptx.py`:
- add JSON output mode (`diagnose_report_v1.json`).
2. Add `review_images` stage support:
- export manifest generation,
- ingestion validation (count/order/min resolution).
3. Add CLI hooks:
- prepare review assets,
- validate review image set before reviewer call.

Design decision:
- default exporter mode is `libreoffice_headless` (`soffice` + `pdftoppm`) for full automation.
- keep `manual_powerpoint` as fallback only for local debugging/fidelity checks.

Deliverables:
- `diagnose_report_v1.json`
- `review_images/v1/slide_*.png`
- ingestion validator

Exit criteria:
- reviewer stage cannot run until evidence is complete and validated.

---

## Phase 3 - Multimodal Review Stage

Goal:
- Add single multimodal review call with strict schema output.

Work:
1. Implement reviewer prompt and adapter in `src/llm/`.
2. Construct `review_context` bundle from:
- original ask,
- planner output,
- composer output,
- diagnose JSON,
- slide images,
- capability manifest.
3. Enforce `ReviewFeedback` schema with bounded retries.
4. Persist `review_feedback_v1.json`.

Deliverables:
- reviewer client function
- context pack builder for review call
- schema-validated feedback artifact

Exit criteria:
- reviewer outputs structured findings and actionable change requests.

---

## Phase 4 - Planner Rework Mode (V2)

Goal:
- planner can replan using feedback as delta while preserving original intent.

Work:
1. Add explicit dual-channel planner input:
- `original_request`
- `review_feedback`
2. Implement planner rework prompt mode and output validation.
3. Persist `planner_deckir_v2.json` with change rationale metadata.

Deliverables:
- planner rework API path
- V2 planner artifact

Exit criteria:
- V2 planner output valid,
- feedback influence is traceable per changed slide.

---

## Phase 5 - Orchestrate Full One-Loop Run

Goal:
- single command executes full V1->Review->V2 flow with hard stop.

Work:
1. Add orchestration command path in `src/cli.py`.
2. Sequence:
- normalize
- plan v1
- resolve/compose/preflight/render v1
- diagnose v1
- review-images stage
- multimodal review
- plan v2
- resolve/compose/preflight/render v2
- diagnose v2
- stop
3. Enforce no second review loop.

Deliverables:
- one-loop CLI pipeline
- robust stage-by-stage error handling

Exit criteria:
- one command produces final `deck_v2.pptx` and full artifact chain.

---

## Phase 6 - Quality Gates and Regression Protection

Goal:
- guarantee quality improvement and prevent backsliding.

Work:
1. Add hard gates on V2 output:
- blocking overflow = fail,
- missing visual in image-capable layout = fail (unless unresolved explicitly logged),
- icon stretched into hero slot = fail.
2. Add V1 vs V2 comparison summary:
- overflow count delta,
- visual coverage delta,
- unresolved cue delta.
3. Add regression tests for one-loop pipeline.

Deliverables:
- `run_summary.json` with before/after metrics
- gate checks integrated into pipeline

Exit criteria:
- V2 quality must be >= V1 on required metrics,
- benchmark runs pass gates.

---

## 3) Testing Matrix

1. Unit tests
- schema validation for new contracts
- diagnose JSON correctness
- review image ingestion validation
- planner rework input routing

2. Integration tests
- V1->Review->V2 pipeline smoke test
- deterministic replay for deterministic stages

3. Benchmark tests
- legacy 10-slide benchmark
- external provider samples (aws/microsoft/hybrid)
- branded samples

---

## 4) Immediate Execution Order

1. Phase 1 contracts and V1/V2 artifact plumbing.
2. Phase 2 diagnose JSON + review image stage.
3. Phase 3 multimodal review call.
4. Phase 4 planner rework mode.
5. Phase 5 one-loop CLI orchestration.
6. Phase 6 gates and regression suite.

---

## 5) Definition of Done

Overhaul is complete when:
1. Pipeline runs exactly one review loop and stops.
2. V1 and V2 artifacts are fully persisted and traceable.
3. Multimodal review is integrated with validated slide images and diagnose JSON.
4. Planner rework consumes structured feedback separately from original ask.
5. Final V2 deck passes quality gates.
