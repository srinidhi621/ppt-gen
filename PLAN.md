# PLAN.md — Thin-Slice Plan With Ground-Truth First (TDD-First)

## 0) Objective

Build a high-quality AI consulting deck generator through small, end-to-end vertical slices, anchored to a curated ground-truth corpus of good slides.

Primary failure to avoid:
- shipping large feature sets without evidence that slide quality improved.

---

## 1) Operating Rules (Non-Negotiable)

1. Ground truth first, feature breadth second.
2. Thin vertical slices only:
- `normalize -> plan -> validate/remediate -> render -> diagnose -> quality gates -> artifacts`.
3. Red/Green/Refactor TDD for every slice.
4. Evidence gate between slices:
- do not start next slice until current exit criteria are met.
5. Anti-bloat policy:
- no speculative modules/catalogs;
- no dead flags;
- remove temporary shims within one following slice.
6. Reuse before rewrite:
- rewrite only when measured complexity/regression cost is worse than replacement.

---

## 2) Baseline (As of 2026-03-03)

Already in place:
1. One-loop `generate-auto` pipeline (V1 review V2).
2. Deterministic validation/remediation/rendering.
3. Review image export (`soffice` + `pdftoppm`).
4. Prompt-level planner metadata wiring (`component_catalog_v1`, `planner_policy_v1`).
5. Initial metadata tests for loader and prompt sections.

Current weaknesses:
1. Quality still inconsistent despite technical correctness.
2. Diversity and intent logic are not fully deterministic.
3. KPI reporting is incomplete for benchmark-driven decisions.
4. No formal ground-truth corpus yet.

---

## 3) Ground-Truth Program (Do This Before Broad Buildout)

## GT0 — Source Collection and Permissions

Goal:
- gather high-quality reference decks/slides for north-star guidance.

Internal sourcing actions:
1. Request candidate decks from sales, strategy, delivery, and GTM leads for:
- proposals/RFPs
- solution approach
- case studies
- GTM offerings
- AI strategy
2. Prioritize decks with known positive outcomes:
- won proposals
- strong client feedback
- reused internal exemplars.
3. Redact sensitive client data (names, pricing specifics, confidential architecture details).
4. Record usage permission and confidentiality class per deck.

External sourcing actions:
1. Collect public examples from:
- consulting thought leadership decks
- public case studies
- AI strategy/governance frameworks
- proposal template structures from public procurement guidance.
2. Use external material for structure/style signals, not direct content copying.
3. Record source URL + usage notes in metadata.

Deliverables:
1. `assets/ground_truth/raw_manifest_v1.json`
2. `assets/ground_truth/source_log_v1.json`

Exit criteria:
1. At least 20 candidate decks total.
2. Coverage across all target blueprint types.
3. Permission and redaction status recorded.

---

## GT1 — Blueprint, Archetype, and Rubric Codification

Goal:
- convert examples into machine-usable structure for planning and validation.

Deck blueprint set (required):
1. `proposal_rfp`
2. `solution_approach`
3. `case_study`
4. `gtm_offering`
5. `ai_strategy`
6. `opportunity_assessment`
7. `business_case_roi`
8. `responsible_ai_governance`
9. `data_ai_platform_blueprint`
10. `executive_steering_update`

Actions:
1. Define `required_sections`, `optional_sections`, and `target_slide_range` per blueprint.
2. Define reusable slide archetypes and map each blueprint to required archetypes.
3. Define quality rubric dimensions for both content and presentation:
- message clarity
- narrative fit
- evidence specificity
- visual hierarchy
- layout balance/spacing
- visual relevance/non-repetition.
4. Build annotation schema for each reference slide:
- blueprint ID, archetype ID, story role, content pattern, visual pattern, quality scores.

Deliverables:
1. `assets/ground_truth/deck_blueprints_v1.json`
2. `assets/ground_truth/slide_archetypes_v1.json`
3. `assets/ground_truth/quality_rubric_v1.json`
4. `assets/ground_truth/ground_truth_manifest_v1.json`
5. `assets/ground_truth/annotations/*.json`

Exit criteria:
1. All reference slides are schema-valid annotations.
2. Only slides scoring `>= 4.0/5.0` are kept as north-star set.

---

## GT2 — First-Slide North-Star Validator (Start Small)

Goal:
- validate one generated slide against ground truth before broader functionality.

Pilot scope:
1. Blueprint: `proposal_rfp`
2. Archetype: `executive_summary`
3. Output: one-slide generation path, end-to-end.

TDD:
1. RED:
- tests for archetype structural checks;
- tests for rubric scorer determinism;
- integration test requiring `ground_truth_eval_v1.json`.
2. GREEN:
- implement deterministic evaluator using composition/diagnose outputs;
- add first-slide quality gate.
3. REFACTOR:
- simplify scorer/evaluator modules and remove duplication.

Deliverables:
1. `runs/<run_id>/ground_truth_eval_v1.json`
2. rubric and alignment score in `run_summary.json`

Exit criteria:
1. Pilot slide passes hard safety gates.
2. Pilot slide passes minimum ground-truth quality floor.

---

## GT3 — Ground-Truth Benchmark Pack v1

Goal:
- create stable benchmark set used by all later slices.

Actions:
1. Select final benchmark corpus from annotated references.
2. Ensure each deck blueprint has representative benchmark coverage.
3. Define go/no-go benchmark thresholds.

Deliverables:
1. `assets/benchmarks/benchmark_manifest_v2.json`
2. `assets/benchmarks/benchmark_thresholds_v1.json`

Exit criteria:
1. Benchmark pack is versioned and reproducible.
2. All later slices consume this benchmark contract.

---

## 4) Slice Tracker

Statuses: `planned | in_progress | complete | blocked`

| Slice | Focus | Status | Evidence Required |
|---|---|---|---|
| GT0 | Source collection + permissions | planned | source log + raw manifest |
| GT1 | Codify blueprints/archetypes/rubric | planned | schema-valid annotations |
| GT2 | First-slide validator pilot | planned | ground_truth_eval artifact |
| GT3 | Benchmark pack v1 | planned | versioned benchmark manifest |
| S0 | KPI scaffold into run artifacts | planned | KPI block in run summary/gates |
| S1 | Deterministic asset diversity enforcement | planned | tests + enforced remediation traces |
| S2 | Deterministic cue intent classifier | planned | intents persisted in artifacts |
| S3 | Intent-to-layout routing guard | planned | routing mismatch class reduced |
| S4 | Recipe 1: technical deep dive | planned | benchmark delta for targeted slides |
| S5 | Recipes 2-3: comparison + roadmap | planned | layout variety and repetition improvements |
| S6 | Review-loop delta discipline | planned | measurable V1->V2 KPI improvement |
| S7 | Benchmark ship/no-ship gates | planned | benchmark report + decision output |
| S8 | Cleanup/de-bloat hardening | planned | dead code removed + docs aligned |

---

## 5) TDD Contract (All Slices)

For every slice:
1. Define acceptance criteria first.
2. Write failing tests first (unit + one integration/e2e contract test).
3. Implement minimal code to pass.
4. Refactor without behavior change.
5. Run:
- `python -m pytest -q`
- targeted integration command(s) for touched behavior.
6. Persist evidence under `runs/<run_id>/`.
7. Update this plan with outcome and keep/pivot call.

Test mix target:
1. Unit: 70%
2. Integration: 20%
3. End-to-end benchmark checks: 10%

No pixel-perfect visual tests.

---

## 6) Implementation Slices After Ground Truth

## S0 — KPI Scaffold in Artifacts

Goal:
- baseline measurement for all future comparisons.

Exit criteria:
1. KPI block added to `quality_gates_v2.json` and `run_summary.json`.
2. Baseline metrics recorded in this file.

## S1 — Deterministic Diversity Enforcement

Goal:
- enforce max reuse, adjacent icon constraints, and minimum unique asset targets deterministically.

Exit criteria:
1. Policy violations are remediated post-plan.
2. Remediation traces are persisted.

## S2 — Deterministic Cue Intent Classifier

Goal:
- assign explicit visual intent tags per slide before routing.

Exit criteria:
1. Intent tags persisted in planner/composition artifacts.
2. Cue-rich slide fallback rate decreases.

## S3 — Intent-to-Layout Routing Guard

Goal:
- ensure intent-compatible layout choice using deterministic upgrades when needed.

Exit criteria:
1. Fewer cue-rich slides on non-image-capable layouts.
2. No overflow regression from routing upgrades.

## S4 — Recipe 1 (`technical_deep_dive`)

Goal:
- prove recipe-driven composition on one high-value archetype.

Exit criteria:
1. Target slides improve versus GT baseline and S0 baseline.
2. Existing safety gates remain green.

## S5 — Recipes 2-3 (`comparison`, `roadmap`)

Goal:
- expand carefully after S4 evidence.

Exit criteria:
1. Layout variety KPI improves.
2. Visual repetition KPI improves.

## S6 — Review Loop Delta Discipline

Goal:
- enforce measurable V1->V2 improvement, not cosmetic churn.

Exit criteria:
1. `v1_vs_v2_delta` persisted in run summary.
2. At least one quality KPI improves when review issues are present.

## S7 — Benchmark Ship/No-Ship Gates

Goal:
- convert benchmark metrics into release decisions.

Exit criteria:
1. Benchmark report emitted in deterministic schema.
2. Clear pass/fail ship decision is generated.

## S8 — Cleanup and De-Bloat

Goal:
- keep repo compact and agent-friendly.

Exit criteria:
1. Remove dead modules/flags.
2. Consolidate temporary compatibility paths.
3. Refresh docs to match shipped behavior.

---

## 7) Baseline Metrics (Fill Starting GT2/S0)

1. Blocking overflow count:
2. Visual density:
3. Unique visual assets per 10 slides:
4. Max single-image reuse:
5. Layout variety:
6. Ground-truth alignment score:
7. Ground-truth rubric score:
8. V1->V2 improvement score:

---

## 8) Commit Cadence

Per slice:
1. `RED` commit: tests only (expected fail).
2. `GREEN` commit: minimal implementation.
3. `REFACTOR` commit: cleanup only.
4. Add slice note in this plan:
- shipped scope
- KPI deltas
- keep or pivot decision.

---

## 9) Definition of Done

Done when:
1. Ground-truth benchmark gates pass consistently.
2. Pilot-to-full archetype rollout maintains quality floor.
3. Deck quality improvements are measurable against baseline.
4. Pipeline remains deterministic and artifact-complete.
5. Codebase is free from significant dead/experimental paths.

