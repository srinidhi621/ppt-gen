# PLAN.md — Vertical Slice Build Plan for the GPT-5.4 Presentation Composer

## 0) Objective

Build a presentation generation agent that can produce branded, editable, high-polish PowerPoint decks through:
- `gpt-5.4` planning;
- reusable skills;
- element-level slide composition;
- deterministic PowerPoint rendering;
- per-slide visual review and repair;
- progressive delivery from CLI to local web UI to cloud endpoint.

This plan fully replaces the prior `PLAN.md`.

---

## 1) Build Rules

1. Ship end-to-end slices only.
2. Every slice must produce user-visible functionality.
3. CLI comes first, then local web UI, then cloud endpoint.
4. Do not widen archetype coverage until at least one archetype works end-to-end.
5. Do not build a general freeform drawing engine.
6. Keep `python-pptx` as the baseline renderer.
7. Use OpenAI-hosted `gpt-5.4` capability as the canonical AI target where available.
8. Keep internal skills provider-agnostic so they can run with or without native OpenAI Skills support.
9. Every slice requires tests and persisted artifacts.
10. No slice is complete until exit criteria are met and evidenced.

---

## 2) Starting Point (`2026-03-11`)

Already present in the repo:
- deterministic Python rendering pipeline;
- template/layout catalog scaffolding;
- placeholder-based rendering;
- validation/remediation logic;
- review-image export;
- multimodal review loop scaffold;
- planning metadata and policy scaffolding;
- solid test baseline.

What is still missing for the target architecture:
- element-level slide composition plans;
- true composed slide rendering layer;
- skill repository and skill loader;
- `gpt-5.4`-first planning runtime;
- per-slide review packets and targeted slide repair;
- visual recipe catalog;
- PowerPoint primitive catalog;
- local web UI and cloud endpoint on the new architecture.

---

## 3) Program-Level Exit Metrics

The build program is only complete when all are true:
1. One-slide archetype path works end-to-end from prompt to reviewed/repaired PPTX.
2. At least 5 archetypes render through the composed path.
3. A 10-15 slide benchmark deck passes hard quality gates.
4. Slide-level repair improves review outcomes measurably.
5. The same backend supports CLI, local web UI, and cloud API.

---

## 4) Slice Tracker

Statuses: `planned | in_progress | complete | blocked`

| Slice | Focus | Status | User-visible Demo |
|---|---|---|---|
| S0 | Runtime reset: `gpt-5.4` + skill loader + artifact contracts | planned | plan-only CLI run with resolved skills |
| S1 | Template inspection + design tokens + primitive catalog | planned | inspect template and emit tokens |
| S2 | One-slide composed render (`executive_summary`) | planned | generate one editable composed slide |
| S3 | Per-slide visual review + repair for one archetype | planned | regenerate one slide from review feedback |
| S4 | Add `process_flow` and `roadmap` archetypes | planned | 3-slide microdeck with varied visuals |
| S5 | Multi-slide deck planner with diversity/rhythm rules | planned | 5-slide deck from one prompt |
| S6 | Reference-backed quality evaluation and benchmark gates | planned | benchmark report for fixture deck |
| S7 | Local web UI over the same pipeline | planned | local browser workflow |
| S8 | Cloud-hosted endpoint | planned | async API job flow |
| S9 | Hardening, cleanup, de-bloat | planned | stable release candidate |

---

## 5) Vertical Slices

## S0 — Runtime Reset: `gpt-5.4`, Responses API, Skill Loader, Artifact Contracts

### Goal
Create the canonical AI runtime and artifact model for the new architecture without yet changing the renderer.

### Build
- Add a Responses-API-capable OpenAI client path for `gpt-5.4`.
- Define provider abstraction so Azure-compatible deployments can still run when feature parity differs.
- Add skill loader that resolves internal skill bundles for a run.
- Persist `resolved_skills.json`.
- Add `plan-only` CLI command that produces:
  - `normalized_content.json`
  - `resolved_skills.json`
  - `deck_blueprint_v1.json`
  - `slide_briefs_v1.json`

### User-visible demo
Run one command that ingests a prompt and shows:
- deck blueprint;
- chosen slide archetypes;
- selected skill bundles.

### Tests
- unit tests for skill manifest parsing and resolution;
- unit tests for provider selection;
- schema tests for deck blueprint and slide briefs;
- one integration test for `plan-only` artifacts.

### Exit criteria
1. `gpt-5.4` planning works in a reproducible CLI flow.
2. Skill resolution is persisted and test-covered.
3. The repo can produce a valid deck blueprint without rendering.

---

## S1 — Template Inspection, Design Tokens, Primitive Catalog

### Goal
Make the presentation layer explicit and deterministic.

### Build
- Build template inspection artifact generation.
- Extract theme tokens from the template.
- Create `ppt_primitive_catalog_v1.json`.
- Create `visual_recipes_v1.json` scaffold.
- Add CLI command to inspect template and emit tokens.

### User-visible demo
Run a command that prints and persists:
- template summary;
- token set;
- available layouts/routes;
- allowed primitive families.

### Tests
- unit tests for token extraction;
- unit tests for placeholder/layout detection;
- snapshot-like structural tests for primitive catalog validity;
- integration test for template inspection artifact generation.

### Exit criteria
1. Every run can produce `template_inspection.json` and `design_tokens.json`.
2. Primitive catalog exists and is schema-valid.
3. Visual recipes scaffold exists for at least 3 archetypes.

---

## S2 — One-Slide Composed Render (`executive_summary`)

### Goal
Prove the new architecture on a single archetype using the composed path.

### Build
- Define `executive_summary` skill.
- Define one `executive_summary` visual recipe.
- Introduce `SlidePlan` and `SlideElementPlan` schemas.
- Add a minimal bounded layout solver.
- Render one composed slide using native PowerPoint primitives.
- Keep output editable.

### User-visible demo
CLI command:
- generate one `executive_summary` slide from prompt;
- emit `slide_plan_v1/<slide_id>.json`;
- render `deck_v1.pptx` containing that slide.

### Tests
- unit tests for `SlidePlan` schema;
- solver unit tests for bounds and non-overlap;
- renderer tests for text, shapes, connectors, and background blocks;
- one end-to-end test for prompt -> slide plan -> PPTX.

### Exit criteria
1. One-slide composed render works end-to-end.
2. Slide contains native text and shapes, not rasterized layout.
3. Blocking overflow is zero for the fixture case.
4. The slide is clearly better than placeholder-only output for the same input.

---

## S3 — Per-Slide Visual Review and Repair for One Archetype

### Goal
Close the loop on a single slide: render, review, repair, rerender.

### Build
- Produce per-slide review packets.
- Add `visual_review_v1/<slide_id>.json` schema.
- Add `repair_plan_v1/<slide_id>.json` schema.
- Make the multimodal reviewer explicitly score each slide for:
  - content quality/message clarity;
  - placement/alignment/spacing;
  - visual appeal/polish.
- Route structured review feedback back into the slide composer/repair planner.
- Add repair planner that updates only the target slide plan.
- Rerender only changed slides.

### User-visible demo
CLI command:
- generate one slide;
- export review image;
- run review;
- inspect targeted feedback for content, placement, and visual appeal;
- apply repair;
- produce `deck_v2.pptx`.

### Tests
- unit tests for review-output schema;
- integration test for image export and review packet generation;
- end-to-end test for one-slide review/repair loop;
- assertions that the repaired slide plan changes only bounded fields.

### Exit criteria
1. One-slide repair loop works without manual intervention.
2. Repair changes only the target slide.
3. Review outputs actionable, structured instructions on content, placement, and visual appeal.
4. Repaired slide passes review-specific gates better than v1.

---

## S4 — Add `process_flow` and `roadmap` Archetypes

### Goal
Prove that the architecture generalizes beyond one slide type.

### Build
- Add skills and visual recipes for:
  - `process_flow`
  - `roadmap`
- Expand primitive rendering for connectors, chevrons, swimlanes, and milestone markers.
- Add archetype-specific caps and validation rules.

### User-visible demo
CLI command creates a 3-slide microdeck:
- `executive_summary`
- `process_flow`
- `roadmap`

### Tests
- unit tests for new archetype contracts;
- renderer tests for flows and timeline/roadmap elements;
- integration test for 3-slide microdeck generation.

### Exit criteria
1. Three archetypes work through the composed path.
2. Adjacent slides show clear visual variety.
3. All three slides remain editable and reviewable.

---

## S5 — Multi-Slide Deck Planner with Diversity and Rhythm Rules

### Goal
Generate a coherent short deck, not just isolated slides.

### Build
- Add deck-level variety constraints.
- Add neighbor-aware slide composition planning.
- Add rhythm rules for title zones, backgrounds, and density.
- Add review summaries that consider adjacent slide continuity.
- Feed slide-level multimodal review results back into planning for targeted slide repair inside a multi-slide deck.

### User-visible demo
Generate a 5-slide deck from a single input prompt with:
- coherent narrative order;
- varied slide visuals;
- no repeated recipe streaks beyond configured limits.

### Tests
- unit tests for deck variety enforcement;
- integration test for 5-slide generation;
- structural tests for recipe repetition and asset reuse;
- review tests that include neighboring slide context.

### Exit criteria
1. 5-slide deck generation works end-to-end.
2. Deck variety and rhythm rules are visibly enforced.
3. Review loop can flag and repair a single weak slide within the deck based on content, placement, and visual appeal.

---

## S6 — Reference-Backed Quality Evaluation and Benchmark Gates

### Goal
Stop relying on intuition alone; evaluate against reference-backed thresholds.

### Build
- Finalize benchmark manifest and threshold files.
- Add rubric scoring hooks tied to archetypes and reference packets.
- Add benchmark report artifact.
- Add ship/no-ship quality gate command.

### User-visible demo
Run benchmark command and get:
- overall status;
- archetype scores;
- blocking issues;
- v1/v2 deltas where available.

### Tests
- schema tests for benchmark manifest;
- deterministic scorer tests;
- integration test for benchmark report generation.

### Exit criteria
1. Benchmark artifact is versioned and reproducible.
2. Hard quality thresholds exist and are enforced in CI/local runs.
3. At least one reference-backed archetype floor is measured, not guessed.

---

## S7 — Local Web UI

### Goal
Wrap the CLI pipeline in a locally run UI suitable for iterative use on a laptop.

### Build
- Add local web app shell backed by the same backend pipeline.
- Support input prompt entry, template selection, run launch, slide thumbnails, review status, and per-slide regenerate.
- Support artifact inspection for current run.

### User-visible demo
A local browser workflow where the user can:
- paste prompt + cues;
- generate deck;
- inspect slides;
- click regenerate for one slide;
- download the deck.

### Tests
- API contract tests for local endpoints;
- one minimal browser-flow integration test if practical;
- backend regression tests to ensure CLI and UI use same contracts.

### Exit criteria
1. Local UI can drive the full run pipeline.
2. Per-slide regenerate works from the UI.
3. No divergence between CLI artifacts and UI artifacts.

---

## S8 — Cloud-Hosted Endpoint

### Goal
Expose the same engine as a hosted asynchronous API.

### Build
- Add job-based API endpoints.
- Add artifact storage strategy.
- Add status polling and run retrieval.
- Add provider/config controls for local/OpenAI-hosted/Azure-hosted runtime.

### User-visible demo
Remote client can:
- submit generation job;
- poll status;
- fetch final PPTX and review results;
- trigger single-slide repair.

### Tests
- API contract tests;
- async job lifecycle tests;
- artifact persistence tests under hosted mode.

### Exit criteria
1. Hosted API reproduces local pipeline behavior.
2. Job artifacts remain inspectable.
3. Slide repair is supported remotely.

---

## S9 — Hardening, Cleanup, and De-Bloat

### Goal
Remove temporary scaffolding and prepare for sustained development.

### Build
- delete dead code and abandoned branches;
- align README and docs to actual architecture;
- tighten tests and runbooks;
- audit OOXML bridge usage;
- lock down skill versioning policy.

### User-visible demo
Stable release candidate with:
- clean docs;
- reproducible benchmark results;
- simplified operational path.

### Tests
- full test suite;
- benchmark smoke suite;
- targeted regression runs on critical archetypes.

### Exit criteria
1. Obsolete V1-only assumptions are removed where no longer needed.
2. Docs match implementation.
3. Release candidate is operationally stable.

---

## 6) Commands and MVP Surfaces

The plan assumes the following command progression:
- `plan-only`
- `inspect-template`
- `generate-slide`
- `review-slide`
- `generate-deck`
- `serve-local`
- `serve-api`

Command names may vary, but the surface progression may not.

---

## 7) Required Artifacts by Milestone

By S0:
- `resolved_skills.json`
- `deck_blueprint_v1.json`
- `slide_briefs_v1.json`

By S1:
- `template_inspection.json`
- `design_tokens.json`
- `ppt_primitive_catalog_v1.json`

By S2:
- `slide_plan_v1/<slide_id>.json`
- `deck_render_plan_v1.json`
- `deck_v1.pptx`

By S3:
- `visual_review_v1/<slide_id>.json`
- `repair_plan_v1/<slide_id>.json`
- `deck_v2.pptx`
- planner-facing review feedback for content, placement, and visual appeal

By S5:
- `deck_review_summary_v1.json`
- deck-level diversity/rhythm metrics

By S6:
- `benchmark_report_v1.json`
- thresholded quality decision

---

## 8) Definition of Done

The build program is done only when:
1. CLI, local UI, and cloud endpoint all run the same core pipeline.
2. At least 5 archetypes render with acceptable review quality.
3. Per-slide multimodal review and planner-driven repair is operational.
4. Benchmark gating is real and enforced.
5. The resulting decks are editable, branded, and operationally reproducible.
