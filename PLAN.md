# PLAN.md — V3 Project Board

**Updated**: 2026-04-15
**Active phase**: Foundations (Phase 1 of `SPEC-v3.md §11`)
**Source of truth for architecture**: `SPEC-v3.md`

---

## How This Board Works

This is a living document. It is updated after every working turn.

**Operating mode**:
1. Claude builds one thin slice.
2. User reviews the deliverable against the review gate.
3. User steers (approve / revise / reprioritize).
4. Claude updates this board.
5. Repeat.

**Rules**:
- One active slice at a time. No batching multiple slices before a review.
- Every slice ends at a **review gate** — a specific thing the user inspects before the next slice starts.
- Slices blocked on user input are listed under "Blocked on User" and do not advance.
- Deletions, destructive operations, and scope changes are always review-gated.
- Review gates marked with **REVIEW-GATE** must be completed before the next slice starts.
- Items marked **INDEPENDENT** can be built without a review gate but are still reported in the changelog.

---

## Where We Are Right Now

The repo has been through two architectural iterations (V1 placeholder-fill, V2 recipe engine — abandoned). `SPEC-v3.md` was rewritten on `2026-04-10` around a planner / builder / reviewer pipeline backed by a small runtime library (`ppt_runtime`), a hand-validated example library, and a deterministic post-build scanner. `BRAINSTORM.md` captures the first-principles derivation behind that spec.

V3 foundation code now exists on the active PR branch, but it is still under review-gated validation. The current focus remains the **non-LLM foundations**: design system artifact, runtime library, and runtime validation against `alternate-approach/build.py`. The LLM layer (planner, builder, reviewer) does not start until those foundations are reviewed and approved.

**2026-04-14 update**: Designer reference slides received (21 slides, 3 Ascendion-branded usable for direct decomposition, layout patterns from others to reimplement). Independent first-principles review (`BRAINSTORM_codex.md`) incorporated into `SPEC-v3.md`: archetype capacity metadata, pre-builder feasibility gate, section-level runtime composers, repair escalation, planner schema enrichment (`purpose` + `audience_takeaway`).

**2026-04-14 (evening) update**: Three open decisions resolved: (1) archetype vocabulary (13 active + 3 candidates) approved as-is, (2) `presentation-writing.skill` rules are hard constraints for the planner, (3) hosting + diagrams confirmed deferred. SLICE-003 (`design_system.json`) drafted and ready for review.

---

## Active Slice

### SLICE-006b — Runtime validation: rewrite `alternate-approach/build.py` on runtime
**Status**: Built — awaiting user review
**Owner**: Claude
**Description**: Rewrite the 410-line `build.py` on `ppt_runtime`. Same content, same structural patterns, Ascendion branding via tokens.
**Deliverables**: `alternate-approach/build_v3.py` (507 lines), produces `10x_program_plan.v3_runtime.pptx` (6 placeholder-free slides, 20–44 shapes per slide)
**REVIEW-GATE**:
- [ ] User opens both decks side-by-side and confirms structural fidelity.
- [ ] User confirms the rewritten file is shorter, clearer, or at minimum no worse than the original.
- [ ] Any newly-added runtime primitives are explicitly listed in the review.

---

## Review Queue (waiting on user)

| Item | Why it matters | Blocks |
|---|---|---|
| _(empty — no items pending user review)_ | | |

---

## Blocked on User Input

| Blocker | What's needed | Slices blocked |
|---|---|---|
| ~~Designer slides~~ | ~~Received 2026-04-14~~ | ~~SLICE-007~~ |
| ~~V1/V2 cleanup decision~~ | ~~Approved 2026-04-14~~ | ~~SLICE-002~~ |
| ~~Archetype vocabulary review~~ | ~~Approved as-is 2026-04-14~~ | ~~SLICE-007~~ |
| ~~Hosting + diagrams scope~~ | ~~Confirmed deferred 2026-04-14~~ | ~~None~~ |
| ~~`presentation-writing.skill` authority~~ | ~~Hard constraints, confirmed 2026-04-14~~ | ~~SLICE-010~~ |

---

## Up Next (Claude can build independently)

These slices are ready to start as soon as their blockers clear. Listed in execution order.

### SLICE-004 — `ppt_runtime` skeleton: canvas, grid, tokens
**Blocker**: SLICE-003 approval
**Description**: Create `src/ppt_runtime/` with `canvas.py`, `grid.py`, `tokens.py`. No measurement, no shape helpers yet. Unit tests for grid math and token lookups.
**REVIEW-GATE**:
- [ ] User reads the public API surface.
- [ ] User confirms the named-anchor vocabulary (`canvas.body_left`, `grid.span(...)`) matches intent.

### SLICE-005 — `measure_text` primitive
**Blocker**: SLICE-004 approval
**Description**: Implement `measure.py` using Pillow + bundled substitute fonts. Unit tests against known strings at known sizes, verified against PowerPoint-rendered ground truth. `shrink_to_fit` helper.
**REVIEW-GATE**:
- [ ] User confirms measurement accuracy is within ~5% of PowerPoint's actual layout on a test string set.

### SLICE-006 — Shape helpers, patterns, and section composers
**Blocker**: SLICE-005 approval
**Description**: Implement `shapes.py` (`add_rect`, `add_text`, `add_image`, `add_line`), `patterns.py` (`draw_card`, `draw_header_bar`, `draw_kicker`), and `composers.py` (`compose_card_row`, `compose_stat_grid`, `compose_split_columns`, `compose_timeline`). Section composers take a bounding region + content and handle internal layout. Unit tests that produce real PPTX output and verify shape properties.
**REVIEW-GATE**:
- [ ] User opens the test-generated PPTX and confirms shapes look right.
- [ ] User confirms section composers produce sensible multi-shape layouts.

### SLICE-006b — Runtime validation: rewrite `alternate-approach/build.py` on runtime
**Blocker**: SLICE-006 approval
**Description**: Rewrite the existing 410-line `alternate-approach/build.py` on top of `ppt_runtime`. No LLM involved. This is the runtime's "can it reproduce a hand-polished deck" gate. Any missing primitive becomes a runtime addition.
**REVIEW-GATE**:
- [ ] User opens both decks side-by-side and confirms structural fidelity.
- [ ] User confirms the rewritten file is shorter, clearer, or at minimum no worse than the original.
- [ ] Any newly-added runtime primitives are explicitly listed in the review.

### SLICE-007 — Example library seeding
**Blocker**: ~~Designer slides arrive~~ (received 2026-04-14) + SLICE-006b approval + archetype vocabulary review
**Description**: Two tracks:
1. **Ascendion direct decomposition** (S01, S02, S06): parse shapes, identify archetype, write runtime-code decomposition against `ppt_runtime`, execute, visually diff, iterate. S06 is complex (22 shapes, connectors) and may require runtime extensions.
2. **Layout pattern reimplementation** (from non-Ascendion sources): study the layout structure of S14 (matrix grid), S21 (timeline), S09 (process flow), S07 (concept comparison), S18 (feature columns), and reimplement each on the Ascendion template using Ascendion tokens and grid.
Write metadata (`invariants`, `variables`) per `SPEC-v3.md §6.3`. Refine archetype capacity values based on actual measurement. Confirm or reject candidate archetypes.
**REVIEW-GATE** (per example):
- [ ] User confirms the archetype tag.
- [ ] User confirms the runtime-code reproduction is faithful (Ascendion) or structurally sound (reimplemented).
- [ ] User reviews the `invariants` and `variables` metadata.
- [ ] User confirms capacity values derived from measurement.
**Notes**: This is slow work. Expect ~1-2 hours per example. Do one, review, then next. Start with an Ascendion slide (S01) to prove the workflow, then alternate.

### SLICE-008 — Deterministic post-build scanner + stage contracts + content fidelity
**Blocker**: SLICE-006 (runtime available) — can run in parallel with SLICE-007
**Description**: Three components:
1. `src/scan/scanner.py` implementing all 26 objective hygiene checks from `SPEC-v3.md §10.6`. BLOCKING vs WARNING severity. `geometry_report.json` schema.
2. `src/contracts/` with JSON Schema files + AST/artifact validators for every pipeline handoff (§10.4). Covers normalize→planner, planner→feasibility, feasibility→builder, builder→sandbox, sandbox→scanner, scanner→reviewer, reviewer→repair, repair→accept.
3. `src/scan/content_fidelity.py` implementing the content fidelity check (§10.5). Separates visible text from notes. Detects dropped facts, hallucinated specifics, placeholder/markdown leaks. Produces `content_fidelity_report.json`.
4. Artifact/log completeness tests — verify required run artifacts and `run_log.jsonl` stage markers.
Unit tests against fixture decks with injected bugs (scanner), invalid handoff payloads (contracts), and known-content input/output pairs (fidelity).
**REVIEW-GATE**:
- [ ] User reviews the scanner check list and severity mapping.
- [ ] User confirms the `geometry_report.json` and `content_fidelity_report.json` schemas.
- [ ] User reviews the contract schemas for each handoff.
- [ ] User confirms content fidelity rules (hallucinated specifics blocking, visible-vs-notes distinction).

### SLICE-009 — Sandbox execution harness
**Blocker**: None (can start after SLICE-002)
**Description**: `src/sandbox/` with subprocess wrapper, AST pre-scan, `resource.setrlimit` limits, RO bind-mount configuration, attempt directory management, retry loop. Unit tests for import rejection, timeout, memory cap, successful execution.
**REVIEW-GATE**:
- [ ] User confirms the AST rejection list.
- [ ] User confirms the rlimit values.
- [ ] User runs a trivial builder script end-to-end.

### SLICE-010 — Planner + feasibility + normalize
**Blocker**: SLICE-001 approved, SLICE-003 approved, archetype vocabulary approved, presentation-writing skill decision
**Description**: `src/v3/planner.py` with `deck_plan.json` schema, system prompt embedding archetype vocabulary, presentation-writing skill rules appendix, argument-spine requirement. `src/normalize/parser.py` for input normalization and cue extraction. `src/v3/feasibility.py` for capacity gate. Tests: planner validation, normalize/cues, feasibility pass/fail boundary cases, asset-resolution failure handling. Tests against one fixture content file. No builder yet.
**REVIEW-GATE**:
- [ ] User inspects planner output for one real prompt.
- [ ] User confirms copy quality passes the presentation-writing skill's checklist.
- [ ] User confirms feasibility gate correctly rejects an overstuffed slide.

### SLICE-011 — Builder prompt + end-to-end plan→build→scan (no review)
**Blocker**: SLICE-007 has at least one working example per seeded archetype, SLICE-008 + SLICE-009 + SLICE-010 done
**Description**: Builder prompt assembly, runtime API docs generation, few-shot example injection. First end-to-end happy path: prompt → plan → build → sandbox-execute → scan → PPTX. No review loop yet. Integration tests for happy paths, contract-violation handling, review-image export smoke. Canary live benchmark on 3-5 release-gate prompts.
**REVIEW-GATE**:
- [ ] User inspects the built PPTX on a real prompt.
- [ ] User confirms canary prompts produce no catastrophic failures.

### SLICE-012 — Multimodal review with rubric + repair loop
**Blocker**: SLICE-011 working
**Description**: Rubric-based reviewer, repair builder prompt, end-to-end plan → build → scan → review → repair → scan → PPTX. Repair-path integration tests including preserve-list enforcement, dropped-fact repair, editability probe.
**REVIEW-GATE**:
- [ ] User compares V1 vs. repaired V1 on the same prompt.
- [ ] User confirms the repair actually improved things.
- [ ] User confirms preserve-list enforcement (non-flagged slides remain intact).

### SLICE-013 — Quality gates + CLI wiring + run metrics
**Blocker**: SLICE-012 working
**Description**: Quality gate evaluation, `generate-auto --mode v3` flag, `runs/<run_id>/` artifacts per `SPEC-v3.md §8`. Run metrics ledger (`runs/metrics_ledger.csv`) with threshold-to-action wiring per `SPEC-v3.md §10.8`. Artifact completeness verification on CLI runs.
**REVIEW-GATE**:
- [ ] User runs the CLI end-to-end on a real prompt.
- [ ] User confirms metrics ledger is populated with correct fields.
- [ ] User confirms artifact completeness check works on both success and failure paths.

### SLICE-014 — Benchmark V1 vs V3
**Blocker**: SLICE-013
**Description**: Full paired V1 vs V3 benchmark on the release-gate subset of prompts from `assets/benchmarks/v3_test_prompts.xlsx` per `SPEC-v3.md §10.7`. Separate reporting for forward-coverage and stress prompts. Editability audit on sampled decks. Metrics ledger trend review with explicit actions. Calibration step on 10-prompt anchor set before score bands become release gates.
**REVIEW-GATE**:
- [ ] User scores all release-gate prompts with paired V1/V3 comparison.
- [ ] User confirms no catastrophic failures on release-gate prompts.
- [ ] User confirms every active archetype has at least one passing prompt.
- [ ] User decides cutover default based on calibrated pass criteria.

---

## Backlog (out of current scope)

### B1 — Architecture diagram generation
**Why deferred**: Composition of text-and-card slides is a different problem from laying out a system architecture diagram (boxes, arrows, cloud service icons, hierarchical or topological layout). Different planner signals, different primitives, different review criteria. Has a real chance of being its own sub-pipeline.

**Outline of the sub-problem when we get to it**:
- New archetype: `architecture_diagram`.
- New runtime module: `diagrams.py` with `node`, `cluster`, `connector`, layered-layout or DAG-layout helpers.
- Integration with the existing 29K icon library (AWS, Azure, GCP icons are already in `assets/icons/png/external/`) — this is a real asset.
- Planner output would include a graph description (nodes, edges, groupings) instead of prose bullets.
- Review rubric needs architecture-specific axes (clarity of flow direction, grouping legibility, label readability).

**Not starting until**: V3 main pipeline is shipping and stable on non-diagram slides.

### B2 — Hosting / multi-user deployment
**Why deferred**: Current scope is a single-user local CLI. Hosting is a product and infrastructure problem, not a quality problem.

**Outline of the sub-problem when we get to it**:
- API surface: REST + async job model (runs are multi-minute, not request/response). Upload content → receive run_id → poll or webhook → download PPTX.
- Multi-tenancy: per-org templates, per-org brand assets, per-user auth.
- Sandbox hardening: the subprocess sandbox acceptable for single-developer use is **not** acceptable for a public service. A hosted build would need real container isolation (Firecracker, gVisor, or a managed sandbox service).
- LLM credential management: central vs. bring-your-own-key.
- Storage: `runs/` grows unbounded. Needs a backing store (Azure Blob / S3) with lifecycle policies.
- Render dependencies: `soffice` + `pdftoppm` need to be baked into the container image.
- Queue + worker architecture: runs are 1-5 minutes. Synchronous HTTP doesn't work.
- Cost model: each run is 5-8 LLM calls + sandbox compute + review images. Meter per run.

**Candidate stack once we get there**: Azure Container Apps + Azure Service Bus + Azure Blob + Azure OpenAI + a hardened sandbox image. All already in the Azure ecosystem, matches the LLM client the repo already has.

**Not starting until**: Local V3 is shipping and has been used by the user for real decks for at least a few weeks.

### B3 — Example library expansion beyond seed batch
**Why deferred**: 5-6 seed examples is a starting point, not a complete library. Coverage targets per `SPEC-v3.md §6.4` are 2-3 examples per archetype. Collecting and decomposing more examples is a slow trickle, not a phase.

**Not starting until**: Seed batch is decomposed and the first few real runs reveal which archetypes are weakest.

### B4 — Automatic design system derivation
**Why deferred**: Currently `design_system.json` is hand-authored. An automatic derivation script could scan reference slides and extract dominant type sizes, gutters, and spacing. Nice to have, not a blocker.

### B5 — Runtime versioning and example regression suite
**Why deferred**: Once the example library has more than a few entries, runtime changes need a regression gate (re-run every example, diff against previous output). Meaningful only after SLICE-007 produces a real library.

---

## Completed

| ID | Title | Date | Deliverable |
|---|---|---|---|
| PRE-01 | V3 architecture rewrite | 2026-04-10 | `SPEC-v3.md` (full rewrite) |
| PRE-02 | First-principles design exercise | 2026-04-10 | `BRAINSTORM.md` |
| PRE-03 | `presentation-writing.skill` added to repo | 2026-04-10 | `assets/presentation-writing.skill` |
| PRE-04 | Designer reference slides received | 2026-04-14 | `assets/ground_truth/internal_inbox/designer_reference_slides.pptx` (21 slides cataloged) |
| PRE-05 | Independent first-principles review incorporated | 2026-04-14 | `BRAINSTORM_codex.md` assessed; 5 ideas incorporated into `SPEC-v3.md` rev 2 |
| SLICE-001 | V1/V2 artifact keep/delete review | 2026-04-14 | Keep/delete matrix approved by user |
| SLICE-002 | V1/V2 cleanup execution | 2026-04-14 | 5 V1 catalogs mined → `v1_mined_notes.md`; 14 ground_truth scratch files deleted; -5,862 lines |
| PRE-06 | Benchmark test prompts + evaluation rubric | 2026-04-14 | `assets/benchmarks/v3_test_prompts.xlsx` (26 prompts, 9-axis rubric, reusable generator script) |
| PRE-07 | Visual hygiene checks | 2026-04-14 | `assets/benchmarks/v3_visual_hygiene_checks.xlsx` (26 binary checks, 6 categories, reusable generator script) |
| SLICE-003 | Draft `design_system.json` | 2026-04-14 | `assets/template/design_system.json` — 12-col grid, 6-level type scale, 15 color tokens, 3 canvases, accent policy |
| SLICE-004 | `ppt_runtime` skeleton | 2026-04-15 | `src/ppt_runtime/` — canvas, grid, tokens, errors. 35 unit tests |
| SLICE-005 | `measure_text` primitive | 2026-04-15 | `measure.py` — Pillow-based measurement, `shrink_to_fit`. 19 unit tests |
| SLICE-006 | Shape helpers, patterns, composers | 2026-04-15 | `shapes.py`, `patterns.py`, `composers.py`. 18 unit tests producing real PPTX |

---

## Changelog

- **2026-04-15** — PR #4 follow-up fixes applied on `feature/ppt-runtime-foundation`: `load_template()` now strips the template's seed slides, `Canvas.add_slide()` strips inherited layout placeholders, `measure_text()` preserves explicit newlines, `shrink_to_fit()` rejects width overflow, and `alternate-approach/build_v3.py` now runs standalone, uses named token styles from `design_system.json`, and exercises runtime fit logic on long text blocks. Added regressions for empty-template loading, placeholder stripping, multiline measurement, width-aware fit, and standalone `build_v3.py`. Affected test set: 79 passing.
- **2026-04-15** — SLICE-004 through SLICE-006b built in sequence. Runtime library complete: canvas (load_template, add_slide, body properties), grid (12-col, 1-indexed span/row), tokens (color/type/spacing from design_system.json), measure (Pillow text measurement, shrink_to_fit), shapes (add_rect, add_text, add_image, add_line), patterns (draw_card, draw_header_bar, draw_kicker, draw_stat_block), composers (compose_card_row, compose_stat_grid, compose_split_columns, compose_timeline). 72 unit tests, all passing. `alternate-approach/build_v3.py` rewrites the 410-line original on ppt_runtime (507 lines — longer due to reusable helper definitions, but token-driven with no hex literals or inline sizing). No new runtime primitives required.
- **2026-04-14 (evening)** — Three open decisions resolved: archetype vocabulary (13 active + 3 candidates) approved as-is; `presentation-writing.skill` confirmed as hard constraints for planner; hosting (B2) and diagrams (B1) confirmed deferred. SLICE-003 drafted: `assets/template/design_system.json` authored from `canvas_config.json`, `token_overrides.json`, `reference_slide_catalog.json`, `v1_mined_notes.md`, and `alternate-approach/build.py` spacing patterns. All prior user-input blockers cleared.
- **2026-04-14** — Visual hygiene checks added: 26 binary pass/fail checks across 6 categories (Color, Typography, Spatial, Content Rendering, Cross-Slide, Structural), 12 BLOCKING / 14 WARNING, with LLM review prompts. Generator at `scripts/generate_visual_hygiene_xlsx.py`. SPEC-v3.md updated: §4.6 cross-references hygiene suite, §10.2 added with full check taxonomy and deck-level pass criteria.
- **2026-04-14** — SLICE-001 approved, SLICE-002 executed (19 files deleted, 5 mined). Benchmark test bed expanded to 26 prompts across 7 sections (`v3_test_prompts.xlsx`): 20 single-slide + 6 multi-slide, 9-axis rubric (7 base + 2 multi-slide-only), reusable generator script at `scripts/generate_benchmark_xlsx.py`. Evaluation criteria added to `SPEC-v3.md §10.1` and `§13`. SLICE-003 (design_system.json) now active. Designer slides received, cataloged (21 slides, 3 Ascendion-branded decomposable). `BRAINSTORM_codex.md` assessed; 5 ideas incorporated into SPEC-v3.md: archetype capacity metadata, feasibility gate, section composers, repair escalation, purpose/audience_takeaway. Archetype vocabulary expanded to 13 active + 3 candidates. SLICE-007 updated with two-track decomposition plan. `content_with_diagram` renamed to `content_with_visual`. `matrix_grid` and `timeline_roadmap` added. SLICE-006 expanded to include section composers.
- **2026-04-10** — Full rewrite of `PLAN.md` as a living project board. V1/V2 cleanup audit delivered as SLICE-001 review gate. Backlog seeded with architecture-diagrams and hosting items. `SPEC-v3.md` and `BRAINSTORM.md` referenced as source of truth.
- **2026-04-10** — `SPEC-v3.md` full rewrite incorporating runtime library, design system artifact, example library, deterministic scan before review, structured rubric reviewer.
- **2026-04-10** — `BRAINSTORM.md` created as first-principles derivation.
- **2026-04-09** — `SPEC-v3.md` initial revision (now replaced).
