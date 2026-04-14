# PLAN.md — V3 Project Board

**Updated**: 2026-04-14
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

No V3 code exists yet. The next few slices are **non-LLM foundations**: audit, cleanup, design system artifact, runtime library, runtime validation against `alternate-approach/build.py`. The LLM layer (planner, builder, reviewer) does not start until the foundations are reviewed and approved.

**2026-04-14 update**: Designer reference slides received (21 slides, 3 Ascendion-branded usable for direct decomposition, layout patterns from others to reimplement). Independent first-principles review (`BRAINSTORM_codex.md`) incorporated into `SPEC-v3.md`: archetype capacity metadata, pre-builder feasibility gate, section-level runtime composers, repair escalation, planner schema enrichment (`purpose` + `audience_takeaway`).

---

## Active Slice

### SLICE-001 — V1/V2 artifact keep/delete review
**Status**: Awaiting user review
**Owner**: User
**Description**: Claude has audited V1/V2 artifacts in the repo and proposed a keep/delete matrix. User reviews the matrix and confirms what to delete, what to keep during the V1 fallback period, and what to mine before deletion.
**Deliverable**: The table in this turn's chat reply.
**REVIEW-GATE**:
- [ ] User approves the `KEEP` list.
- [ ] User approves the `KEEP DURING V1 FALLBACK` list.
- [ ] User approves the `MINE THEN DELETE` list and confirms what "mine" means for each.
- [ ] User approves the `DELETE NOW` list (currently empty).
**Definition of done**: A follow-up slice (SLICE-002) captures the decisions as a cleanup task list in this plan.

---

## Review Queue (waiting on user)

| Item | Why it matters | Blocks |
|---|---|---|
| V1/V2 artifact keep/delete matrix (SLICE-001) | Controls what the next foundational slices can discard or reuse | SLICE-002, SLICE-004 |
| Archetype vocabulary + capacity metadata (`SPEC-v3.md §5`, now 13 active + 3 candidates) | Planner-to-builder contract; feasibility gate; examples must populate each label | SLICE-007, SLICE-010 |
| `presentation-writing.skill` as authoritative copy-quality contract for the planner | Decides whether the planner embeds the skill's rules as hard constraints or treats them as guidance | SLICE-010 (planner schema) |
| Design system authorship path | Decides whether Claude drafts `design_system.json` from existing catalogs or user hand-authors | SLICE-003 |

---

## Blocked on User Input

| Blocker | What's needed | Slices blocked |
|---|---|---|
| ~~Designer slides~~ | ~~Received 2026-04-14~~ | ~~SLICE-007~~ |
| V1/V2 cleanup decision | Outcome of SLICE-001 | SLICE-002 |
| Archetype vocabulary review | Confirmation / edits to the 13 active + 3 candidate archetypes (see `SPEC-v3.md §5`) | SLICE-007 |
| Hosting + diagrams scope | Confirmation these stay in backlog, not pulled forward | None (backlog only) |

---

## Up Next (Claude can build independently)

These slices are ready to start as soon as their blockers clear. Listed in execution order.

### SLICE-002 — V1/V2 cleanup execution
**Blocker**: SLICE-001 approval
**Description**: Execute the approved keep/delete matrix. Mine the V2-era catalogs into notes for `design_system.json` authoring. Delete approved files. Update imports and tests that break as a result.
**REVIEW-GATE**:
- [ ] User confirms the resulting `git status` + diff summary before commit.

### SLICE-003 — Draft `design_system.json`
**Blocker**: SLICE-001, user confirms draft-and-review path
**Description**: Author `assets/template/design_system.json` from `canvas_config.json`, `token_overrides.json`, `ground_truth/reference_slide_catalog.json`, and the mined V2 catalog notes. Schema per `SPEC-v3.md §4.0`.
**REVIEW-GATE**:
- [ ] User reads the draft file.
- [ ] User confirms grid cols, gutter values, type scale sizes, accent policy.
- [ ] User flags anything that should be derived from a reference slide but wasn't.

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

### SLICE-008 — Deterministic post-build scanner
**Blocker**: SLICE-006 (runtime available) — can run in parallel with SLICE-007
**Description**: `src/scan/scanner.py` implementing the checks in `SPEC-v3.md §4.6`. BLOCKING vs WARNING severity. `geometry_report.json` schema. Unit tests against fixture decks with injected bugs.
**REVIEW-GATE**:
- [ ] User reviews the check list and severity mapping.
- [ ] User confirms the `geometry_report.json` schema.

### SLICE-009 — Sandbox execution harness
**Blocker**: None (can start after SLICE-002)
**Description**: `src/sandbox/` with subprocess wrapper, AST pre-scan, `resource.setrlimit` limits, RO bind-mount configuration, attempt directory management, retry loop. Unit tests for import rejection, timeout, memory cap, successful execution.
**REVIEW-GATE**:
- [ ] User confirms the AST rejection list.
- [ ] User confirms the rlimit values.
- [ ] User runs a trivial builder script end-to-end.

### SLICE-010 — Planner schema + prompt
**Blocker**: SLICE-001 approved, SLICE-003 approved, archetype vocabulary approved, presentation-writing skill decision
**Description**: `src/v3/planner.py` with `deck_plan.json` schema, system prompt embedding archetype vocabulary, presentation-writing skill rules appendix, argument-spine requirement. Tests against one fixture content file. No builder yet.
**REVIEW-GATE**:
- [ ] User inspects planner output for one real prompt.
- [ ] User confirms copy quality passes the presentation-writing skill's checklist.

### SLICE-011 — Builder prompt + end-to-end plan→build→scan (no review)
**Blocker**: SLICE-007 has at least one working example per seeded archetype, SLICE-008 + SLICE-009 + SLICE-010 done
**Description**: Builder prompt assembly, runtime API docs generation, few-shot example injection. First end-to-end happy path: prompt → plan → build → sandbox-execute → scan → PPTX. No review loop yet.
**REVIEW-GATE**:
- [ ] User inspects the built PPTX on a real prompt.

### SLICE-012 — Multimodal review with rubric + repair loop
**Blocker**: SLICE-011 working
**Description**: Rubric-based reviewer, repair builder prompt, end-to-end plan → build → scan → review → repair → scan → PPTX.
**REVIEW-GATE**:
- [ ] User compares V1 vs. repaired V1 on the same prompt.
- [ ] User confirms the repair actually improved things.

### SLICE-013 — Quality gates + CLI wiring
**Blocker**: SLICE-012 working
**Description**: Quality gate evaluation, `generate-auto --mode v3` flag, `runs/<run_id>/` artifacts per `SPEC-v3.md §8`.
**REVIEW-GATE**:
- [ ] User runs the CLI end-to-end on a real prompt.

### SLICE-014 — Benchmark V1 vs V3
**Blocker**: SLICE-013 + benchmark prompt set from user
**Description**: Side-by-side V1 placeholder and V3 composed output on 5-10 benchmark prompts. Human rating by user on 1-5 scale per slice per axis. Cutover decision.
**REVIEW-GATE**:
- [ ] User rates the benchmark decks.
- [ ] User decides cutover default.

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

---

## Changelog

- **2026-04-14** — Designer slides received, cataloged (21 slides, 3 Ascendion-branded decomposable). `BRAINSTORM_codex.md` assessed; 5 ideas incorporated into SPEC-v3.md: archetype capacity metadata, feasibility gate, section composers, repair escalation, purpose/audience_takeaway. Archetype vocabulary expanded to 13 active + 3 candidates. SLICE-007 updated with two-track decomposition plan. `content_with_diagram` renamed to `content_with_visual`. `matrix_grid` and `timeline_roadmap` added. SLICE-006 expanded to include section composers.
- **2026-04-10** — Full rewrite of `PLAN.md` as a living project board. V1/V2 cleanup audit delivered as SLICE-001 review gate. Backlog seeded with architecture-diagrams and hosting items. `SPEC-v3.md` and `BRAINSTORM.md` referenced as source of truth.
- **2026-04-10** — `SPEC-v3.md` full rewrite incorporating runtime library, design system artifact, example library, deterministic scan before review, structured rubric reviewer.
- **2026-04-10** — `BRAINSTORM.md` created as first-principles derivation.
- **2026-04-09** — `SPEC-v3.md` initial revision (now replaced).
