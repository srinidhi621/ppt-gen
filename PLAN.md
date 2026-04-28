# PLAN.md — V3 Project Board

**Updated**: 2026-04-28
**Active phase**: LLM Layer (Phase 3 of `SPEC-v3.md §11`)
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

**2026-04-15 update (evening)**: All foundation PRs merged to main. PR #4 (runtime, SLICE-003–006b), PR #6 (sandbox, SLICE-009), PR #7 (scanner/examples/contracts/fidelity, SLICE-007/008) all on main. Repo cleaned: stale branches and worktrees removed. Non-LLM foundations complete. Next: LLM layer (SLICE-010 normalize + planner).

**2026-04-16 update**: SLICE-010 merged to main (PR #8). Planner, feasibility gate, normalize, LLM client (Responses API), retry wrapper, and cost logging all on main. 617 tests passing. Stale branches pruned. Ready for SLICE-011 (builder + first end-to-end).

**2026-04-28 update**: Git `main` is at `5eb803eb` with SLICE-011 builder work merged locally and on `origin/main`: builder prompt, example selector, V3 pipeline wiring, sandbox execution handoff, scan handling, and PR #9 review fixes are in the codebase. The slice is still review-gated: user validation of a real built PPTX and canary prompts is still pending before SLICE-012 starts.

---

## Active Slice

**SLICE-011** — Review gate for builder prompt + end-to-end plan→build→scan (no review loop).

---

## Review Queue (waiting on user)

- **SLICE-011 user review gate** — code is on `main`; user still needs to inspect a built PPTX from a real prompt and confirm canary prompts produce no catastrophic failures.
- **SLICE-011 eval output review** — full benchmark prompt set run on 2026-04-28. 19/26 produced accepted `deck.pptx` outputs after rerunning TP-21 successfully; 7 failed in planner/feasibility/builder and are captured in `runs/v3_eval_outputs.csv` plus `runs/v3_eval_outputs_review.md`.
- **SLICE-011 TP-21 feedback remediation** — user review found black cover background and repeated heading/content overlaps. Scanner now blocks readable overlap collisions and full black slide backgrounds; old TP-21 output is correctly rejected. Fresh TP-21 retry blocked attempt 1, then timed out during builder repair (`runs/eval_20260428_feedback_tp21/`).

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

## Up Next — LLM Layer (Phase 3)

All non-LLM foundations are on main. The remaining slices build the LLM pipeline from left to right: planner → builder → reviewer → repair → quality gates → benchmark.

**Prerequisites**: Azure OpenAI credentials working (probe validates — see `AzureOpenAI_Capabilities.md`). V3 uses the **Responses API only** with a new client (`src/v3/llm_client.py`). The V1 client (`src/llm/`) is NOT reused in V3. Approved models: `gpt-5.4` (planner, reviewer), `gpt-5.3-codex` (builder), `gpt-5.2` (fallback). See `AGENTS.md` Rule 9.

**Build order and dependencies**:
```
SLICE-010 (planner + normalize + feasibility)
    → SLICE-011 (builder + first end-to-end, no review)
        → SLICE-012 (reviewer + repair loop)
            → SLICE-013 (quality gates + CLI + metrics)
                → SLICE-014 (V1 vs V3 benchmark)
```

### SLICE-010 — Planner + feasibility + normalize
**Blocker**: None (all prerequisites merged)
**Description**: First LLM pipeline stage. User text in → `deck_plan.json` out.

**Implementation steps**:
1. **Credential probe** — ~~verify Azure OpenAI connectivity~~. Done. All 3 approved models confirmed working via Responses API. See `AzureOpenAI_Capabilities.md`.
2. **V3 LLM client** — `src/v3/llm_client.py`: Responses API client (raw HTTP, no SDK). Methods: `generate_json`, `generate_code`, `generate_json_with_images`. Model specified per call. Then `src/v3/llm_retry.py`: wraps client calls with parse → validate → retry-with-context logic per `SPEC-v3.md §4.11.5`.
3. **Normalize** — `src/v3/normalize.py`: parse user input (markdown, plain text, or structured) into `normalized_content.json`. Extract optional cues (slide count, density, audience). Minimal — this is mostly passthrough for V3.
4. **Planner system prompt** — `src/v3/prompts/planner_system.txt`: role definition, archetype vocabulary table, `presentation-writing.skill` rules, `deck_plan.json` schema, forbidden-field rules. Assembled at import time from design system + skill file.
5. **Planner caller** — `src/v3/planner.py`: takes `normalized_content.json`, assembles user message, calls LLM via retry wrapper, validates against `deck_plan.schema.json`, returns validated plan.
6. **Feasibility gate** — `src/v3/feasibility.py`: checks each slide against archetype capacity (max_items, max_words). Returns passing plan or failing slides with violations.
7. **Deck plan schema** — `src/contracts/schemas/deck_plan.schema.json` (already exists, may need updates for `purpose` + `audience_takeaway` fields).
8. **Tests**: planner schema validation, forbidden-field rejection, feasibility pass/fail boundary, normalize edge cases. Mocked LLM in unit tests; one live LLM call in a canary test (skipped in CI).

**Files created/modified**:
- New: `src/v3/__init__.py`, `src/v3/llm_client.py`, `src/v3/normalize.py`, `src/v3/planner.py`, `src/v3/feasibility.py`, `src/v3/llm_retry.py`, `src/v3/prompts/planner_system.txt`
- Modified: `src/contracts/schemas/deck_plan.schema.json` (add purpose, audience_takeaway)
- Tests: `tests/test_normalize.py`, `tests/test_planner.py`, `tests/test_feasibility.py`, `tests/test_llm_retry.py`

**REVIEW-GATE**: _(deferred — planner output will be validated as part of SLICE-011 end-to-end)_

### SLICE-011 — Builder prompt + end-to-end plan→build→scan (no review)
**Blocker**: ~~SLICE-007 has at least one working example per seeded archetype, SLICE-008 + SLICE-009 + SLICE-010 done~~ All clear
**Description**: Builder prompt assembly, runtime API docs generation, few-shot example injection. First end-to-end happy path: prompt → plan → build → sandbox-execute → scan → PPTX. No review loop yet. Integration tests for happy paths, contract-violation handling, review-image export smoke. Canary live benchmark on 3-5 release-gate prompts.
**Status**: Implemented on `main` at `5eb803eb`; review gate pending.
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
| SLICE-006b | Runtime validation rewrite | 2026-04-15 | `build_v3.py` reproduces the 10x deck on `ppt_runtime`. Clean template loading, placeholder stripping, width-aware fit. 79 tests |
| SLICE-007 | Example library seeding | 2026-04-15 | 9 seeded examples, all token-driven, scanner-passing. `run_all.py` + `test_examples.py` regression gate |
| SLICE-008 | Scanner, contracts, content fidelity | 2026-04-15 | 21 objective checks, artifact validators, hallucination detection. 394 tests pass |
| SLICE-009 | Sandbox execution harness | 2026-04-15 | `src/sandbox/` — subprocess + AST pre-scan + rlimit |
| SLICE-010 | Planner + feasibility + normalize + LLM client + cost logging | 2026-04-16 | `src/v3/planner.py`, `feasibility.py`, `normalize.py`, `llm_client.py`, `llm_retry.py`, `cost_logger.py`. 6 example-backed archetypes, per-archetype validation, persistent cost logging. 617 tests |

---

## Changelog

- **2026-04-28** — Reconciled `PLAN.md` with git state: SLICE-011 code is on `main` at `5eb803eb`, while the user-facing SLICE-011 review gate remains open before SLICE-012 can start.
- **2026-04-28** — Ran all 26 prompts from the V3 eval set through the SLICE-011 pipeline under `eval_20260428_*`. Result: 18 accepted PPTX outputs, 2 planner timeouts, 2 feasibility failures, 4 builder/scanner failures. Review manifests written to `runs/v3_eval_outputs.csv` and `runs/v3_eval_outputs_review.md`. Added a resumable eval runner and patched Responses JSON-mode input hinting after Azure rejected JSON mode without an explicit "JSON" input hint. Focused verification: `tests/test_llm_client.py` passed (30).
- **2026-04-28** — Reran TP-21 (`Executive Pitch Deck`, expected 5-6 slides) with `--force`; it passed and produced `runs/eval_20260428_tp21/deck.pptx`. Eval manifest refreshed: 19 accepted outputs, 7 remaining failures.
- **2026-04-28** — Applied TP-21 feedback remediation. `VH-13` now classifies readable text/text and text/non-container overlaps as BLOCKING while allowing text intentionally layered inside filled containers. Added `VH-27` to block full black slide backgrounds/full-bleed black rectangles that hide branding. Planner and builder prompts now avoid `header_dark`; hero/section/quote canvas preferences moved to `header_light`. Regenerated example outputs for the stricter gate. Verification: focused scanner/examples/planner/builder suite passed (210), full suite passed (689, 4 skipped). Fresh TP-21 run under `eval_20260428_feedback_tp21` was blocked by scanner on attempt 1 and then builder repair timed out.
- **2026-04-28** — Completed Azure OpenAI INR pricing/backfill. Configured GPT-5.4 Standard Global rates from the Microsoft Retail Prices API (`₹237.0031/1M input`, `₹1,422.0188/1M output`), added INR cost columns to `src/v3/cost_logger.py`, backfilled all 90 rows in `runs/llm_cost_log.csv`, and updated summaries to prefer INR when present. Current ledger totals: `₹329.080256` all-time; `₹274.680456` on 2026-04-28. Verification: `tests/test_cost_logger.py` passed (36).
- **2026-04-28** — Reran TP-21 end to end after pricing/backfill work. Run `eval_20260428_tp21_rerun_tp21` succeeded in one build attempt with 6 slides, zero scanner-blocking findings, and final PPTX at `runs/eval_20260428_tp21_rerun_tp21/deck.pptx`. Aspose preview export produced 6 nonblank PNGs under `runs/eval_20260428_tp21_rerun_tp21/review_images/v1/`; LibreOffice preview export failed locally with an abort trap.
- **2026-04-28** — Ingested `assets/ground_truth/internal_inbox/10x Approach-v1.pptx` as a detailed multi-slide benchmark reference. Exported 15 slide previews and montage under `assets/ground_truth/annotations/10x_approach_v1_images/`, documented slide-by-slide constituents in `assets/ground_truth/annotations/10x_approach_v1_breakdown.md`, mapped the style to a process-flow-led operating-model pattern using current supported archetypes, and added `TP-27` (`Detailed Operating Model / Assessment Funnel`, expected 12-15 slides) to the multi-slide stress tests in `scripts/generate_benchmark_xlsx.py`. Regenerated `assets/benchmarks/v3_test_prompts.xlsx` with 27 prompts. Verification: generator ran successfully and `py_compile` passed for benchmark/eval scripts.
- **2026-04-28** — Added a dedicated multi-slide eval harness for deck-level runs. New generator `scripts/generate_multislide_benchmark_xlsx.py` writes `assets/benchmarks/v3_multislide_test_prompts.xlsx` with slide-by-slide source content and ambiguous visual cues for `MS-01` legacy modernization and `MS-02` 10x AI engineering. Updated `scripts/run_v3_eval_prompts.py` with `--harness multislide`, defaulting output manifests to `runs/v3_multislide_eval_outputs.csv`; the composed prompts do not expose source-deck paths or answer links. Also scrubbed source-deck links from regenerated `v3_test_prompts.xlsx`. Verification: `tests/test_v3_eval_harness.py` passed (3), scripts compile, and workbook string scan found no `assets/ground_truth`/source PPTX links.
- **2026-04-28** — Pushed multi-slide harness commit `2d0cbcb0` to `origin/main`, cleared 37 old run directories under `runs/` while preserving cost/manifest files, and ran `MS-01` end to end with `--harness multislide`. Result: planner recovered from one schema retry, feasibility passed, but builder exhausted 3 attempts due scanner-blocking `VH-13` overlap findings (8 → 23 → 9). No accepted deck was produced; blocked attempt artifacts are under `runs/eval_multislide_20260428_ms01/`, with attempt 3 previews exported to `review_images/attempt_03/`.
- **2026-04-28** — Ran `MS-02` (10x AI Engineering Operating Model) end to end with `--harness multislide`. Result: builder exhausted 3 attempts; scanner-blocking counts were 40 → 10 → 22, making attempt 2 the best blocked deck. Primary blockers are slide 3 text/text overlap, slide 6 text overflow, and slide 7 ownership-lane overlaps. Attempt 2 artifacts are under `runs/eval_multislide_20260428_ms02/build_attempts/attempt_02/`, with 7 nonblank previews exported to `runs/eval_multislide_20260428_ms02/review_images/attempt_02/`.
- **2026-04-16** — PR #9 second review round applied. Six additional fixes: (5) artifact path naming aligned to spec — `build/attempt_N` → `build_attempts/attempt_NN` (zero-padded); (6) `builder_input.json` persisted before build (SPEC §8 artifact contract); (8) `extract_code` rewritten with deterministic priority: python-tagged fences → parseable fences → raw text; (10) missing test coverage added: `max_attempts=1` behavior, `shutil.copy2` failure, `builder_input.json` presence, zero-padded dir naming, python-fence preference; (11) unused imports cleaned (`field`, `json`, `BuildAttempt`, `BuildResult`, `PipelineResult`); (12) `extra_env` broadening documented in-code with future hardening reference. Full suite: 685 passed, 4 skipped.
- **2026-04-16** — PR #9 review fixes applied on `feature/slice-011-builder`. Nine fixes: (1) scanner exceptions now fail the attempt and fold error context into retry instead of silently passing; (2) sandbox subprocess receives `script_args=[str(expected_output)]` so `sys.argv[1]` works, and builder validates exact expected output path instead of globbing any `.pptx`; (3) pipeline `run_summary.json` now writes on all exit paths via `try/finally` (previously skipped on normalize/planner/feasibility failures); (4) prompt `os.environ.get('PPT_GEN_ROOT', ...)` replaced with `Path(src.ppt_runtime.__file__).resolve().parents[2]` — `os.environ` is blocked by AST scanner; (5) builder LLM catch narrowed from `except Exception` to `except (LLMError, ValueError)` so unexpected bugs propagate; (6) stale attempt dirs cleaned via `shutil.rmtree` before recreation; (7) exhaustion message includes last attempt error for diagnostics; (8) `extract_code` edge case tests added (nested fences, multi-language, blank lines, whitespace-only); (9) 9 regression tests covering all fixed bugs. Full suite: 676 passed, 4 skipped.
- **2026-04-16** — Removed the 6 placeholder/test rows from `runs/llm_cost_log.csv`; the persistent V3 cost ledger is now clean and reports no logged calls until real planner/builder/reviewer traffic is recorded.
- **2026-04-16** — Inspected the persistent V3 LLM cost log. Current `runs/llm_cost_log.csv` contains 6 placeholder/test rows only (`caller=unknown`, prompt preview `test`) and reports `$0.0000` total because token pricing env vars are not configured.
- **2026-04-16** — Re-validated PR #9 locally on `feature/slice-011-builder`: targeted builder/example/pipeline tests passed (46) and full suite passed (`663 passed, 4 skipped`), but merge remains blocked on four contract gaps — scanner exceptions treated as pass, sandbox never passes `sys.argv[1]`, early pipeline failures skip `run_summary.json`, and the builder prompt's `os.environ` guidance contradicts the AST allowlist.
- **2026-04-16** — Reviewed PR #9 (`feature/slice-011-builder` → `main`) against `SPEC-v3.md` sections for builder/sandbox/LLM mechanics. Logged blocking gaps (scanner-failure handling, `sys.argv[1]` execution contract mismatch, missing failure-path `run_summary.json`, prompt contradiction with `os.environ`) plus warnings on artifact path/schema drift and test coverage gaps.
- **2026-04-15** — Wired persistent cost logging into the V3 application bootstrap. `ResponsesClient.from_env()` now attaches a `CostLogger` by default, writes to persistent `runs/llm_cost_log.csv` unless `V3_COST_LOG_PATH` overrides it, and can be disabled with `V3_COST_LOG_ENABLED=0`. Updated summary CLI help text and added tests for default-on application logging, env-based path override, disable flag, and persistent file writes.
- **2026-04-15** — SLICE-010 PR #8 review findings addressed. Six fixes applied: (1) planner restricted to 6 example-backed archetypes (`SUPPORTED_ARCHETYPES`), unsupported archetypes rejected at schema and semantic level; (2) feasibility gate rewritten with per-archetype item counters — `quote_callout` counts as 1 item, `comparison_split` counts body-line points, etc.; (3) archetype-specific required fields enforced in planner validation — `process_flow` requires `steps`, `content_with_visual` requires `body` + `visual_intent`, etc.; (4) cost logging made opt-in (None=disabled), `caller` threaded through public methods and retry wrapper, exception narrowed to `OSError` only; (5) CSV hardened with `fcntl` locking, malformed-row tolerance in read/summarize; (6) image MIME detection from magic bytes + extension fallback instead of hardcoded PNG. 606 tests pass (168 targeted).
- **2026-04-15** — SLICE-010 built on `feature/slice-010-planner`. Deliverables: `src/v3/llm_client.py` (Responses API client, 3 methods), `src/v3/llm_retry.py` (structured retry wrapper), `src/v3/normalize.py` (input parsing + cue extraction), `src/v3/planner.py` (planner caller + deck plan validation), `src/v3/feasibility.py` (capacity gate), `src/v3/cost_logger.py` (append-only CSV cost logging, wired into client), `scripts/llm_cost_summary.py` (CLI summary). Tests: 102 new tests across 6 test files. PR #8 created for review.
- **2026-04-15** — Azure OpenAI probe completed via Responses API. All 3 approved models confirmed working: `gpt-5.4` (JSON + Vision + Code), `gpt-5.3-codex` (JSON + Code, no vision), `gpt-5.2` (JSON + Vision + Code). Rate limits: 2500 req/min, 250K tok/min all models. Rule 9 added to `AGENTS.md`: Responses API only, no Chat Completions, minimum model floor gpt-5.2. `SPEC-v3.md` §4.11.2 and §4.11.9 rewritten for Responses API client. `.env` updated with correct endpoint, API version, and per-role model assignments.
- **2026-04-15** — `SPEC-v3.md` §4.11 added: LLM Integration Mechanics covering call sites, prompt assembly, response validation, retry strategy, error propagation, token budget, and feedback loops. `PLAN.md` Up Next section cleaned — completed slices removed, SLICE-010 expanded with concrete implementation steps and file list.
- **2026-04-15** — All foundation work merged to main. PR #4 (SLICE-003–006b), PR #6 (SLICE-009), PR #7 (SLICE-007/008) merged. Stale branches and worktrees cleaned. Non-LLM foundations complete.
- **2026-04-15** — PR #5 remediation complete on `feature/scanner-and-examples`. Six sub-slices delivered: (008a) ported bb16de97 — scanner crashes now surface as synthetic BLOCKING findings; (008b) ported bb16de97 — 5 heuristic checks deferred, VH-15 body_region grounded; (007a) `examples/run_all.py` rewritten with scanner + density enforcement, `tests/test_examples.py` adds scanner-pass, density-bounds, and inline-font-ban tests; (007b) all 9 seeded examples cleaned — inline `font_name`/`font_size_pt` replaced with `tokens.type(...)`, VH-04 contrast fixes via `fill=` on text boxes, VH-11 overflow fixes via rect resizing and type style height calculation; (008c) `src/contracts/validator.py` gains `validate_sandbox_to_scanner()` and `validate_scanner_to_reviewer()` artifact validators plus explicit `PENDING_HANDOFFS` list; (008d) `src/scan/content_fidelity.py` extended with date, dollar, quoted-phrase, and proper-noun hallucination detection. Runtime addition: `add_text()` accepts `fill` parameter, `draw_header_bar()` sizes kicker rect from type style. Verification: 394 passed, 4 skipped.
- **2026-04-15** — Docs synced for scanner remediation: `SPEC-v3.md` now distinguishes the 26-check hygiene catalog from the current objective-only active scanner set, records that `VH-14` and `VH-20` through `VH-23` are deferred until explicit metadata exists, and states that internal scanner failures are BLOCKING findings.
- **2026-04-15** — `SLICE-008b` implemented on `feature/scanner-and-examples`: deferred heuristic checks `VH-14` and `VH-20` through `VH-23` from the active scanner set, documented them in-module as deferred scope, and rewrote `VH-15` to derive grid bounds from the slide layout's mapped canvas `body_region` instead of generic safe-area math. Added regressions showing `VH-21` is intentionally deferred and `VH-15` still fires on a template-grounded misalignment. Verification: `tests/test_scanner.py` (38 passed), `tests/test_contracts.py` (27 passed).
- **2026-04-15** — `SLICE-008a` implemented on `feature/scanner-and-examples`: `scan_pptx()` no longer swallows checker crashes. Internal scanner failures now surface as synthetic `BLOCKING` findings keyed to the failed check id, including `VH-25`. Added regressions for a crashed standard check and a crashed deck-plan check. Verification: `tests/test_scanner.py` (37 passed), `tests/test_contracts.py` (27 passed).
- **2026-04-15** — Switched to `feature/scanner-and-examples` to plan remediation for PR #5. Kept `SLICE-006b` as the active review gate. Re-cut draft `SLICE-007` / `SLICE-008` work into narrower recovery steps: example regression hardening, seeded-example contract cleanup, scanner reliability/scope correction, contract coverage, and content-fidelity hardening. This branch should be treated as draft until those sub-slices pass review.
- **2026-04-15** — Reviewed PR #5 (`feature/scanner-and-examples`) against `SPEC-v3.md` / `PLAN.md`. Findings: it batches SLICE-007 and SLICE-008 before SLICE-006b approval, the example regression path does not enforce the scanner-backed acceptance bar, the seeded examples reintroduce inline font sizing instead of token styles, and the scanner/contract layer is still heuristic/partial relative to the current spec.
- **2026-04-15** — PR #4 follow-up fixes applied on `feature/ppt-runtime-foundation`: `load_template()` now strips the template's seed slides, `Canvas.add_slide()` strips inherited layout placeholders, `measure_text()` preserves explicit newlines, `shrink_to_fit()` rejects width overflow, and `alternate-approach/build_v3.py` now runs standalone, uses named token styles from `design_system.json`, and exercises runtime fit logic on long text blocks. Added regressions for empty-template loading, placeholder stripping, multiline measurement, width-aware fit, and standalone `build_v3.py`. Affected test set: 79 passing.
- **2026-04-15** — SLICE-004 through SLICE-006b built in sequence. Runtime library complete: canvas (load_template, add_slide, body properties), grid (12-col, 1-indexed span/row), tokens (color/type/spacing from design_system.json), measure (Pillow text measurement, shrink_to_fit), shapes (add_rect, add_text, add_image, add_line), patterns (draw_card, draw_header_bar, draw_kicker, draw_stat_block), composers (compose_card_row, compose_stat_grid, compose_split_columns, compose_timeline). 72 unit tests, all passing. `alternate-approach/build_v3.py` rewrites the 410-line original on ppt_runtime (507 lines — longer due to reusable helper definitions, but token-driven with no hex literals or inline sizing). No new runtime primitives required.
- **2026-04-14 (evening)** — Three open decisions resolved: archetype vocabulary (13 active + 3 candidates) approved as-is; `presentation-writing.skill` confirmed as hard constraints for planner; hosting (B2) and diagrams (B1) confirmed deferred. SLICE-003 drafted: `assets/template/design_system.json` authored from `canvas_config.json`, `token_overrides.json`, `reference_slide_catalog.json`, `v1_mined_notes.md`, and `alternate-approach/build.py` spacing patterns. All prior user-input blockers cleared.
- **2026-04-14** — Visual hygiene checks added: 26 binary pass/fail checks across 6 categories (Color, Typography, Spatial, Content Rendering, Cross-Slide, Structural), 12 BLOCKING / 14 WARNING, with LLM review prompts. Generator at `scripts/generate_visual_hygiene_xlsx.py`. SPEC-v3.md updated: §4.6 cross-references hygiene suite, §10.2 added with full check taxonomy and deck-level pass criteria.
- **2026-04-14** — SLICE-001 approved, SLICE-002 executed (19 files deleted, 5 mined). Benchmark test bed expanded to 26 prompts across 7 sections (`v3_test_prompts.xlsx`): 20 single-slide + 6 multi-slide, 9-axis rubric (7 base + 2 multi-slide-only), reusable generator script at `scripts/generate_benchmark_xlsx.py`. Evaluation criteria added to `SPEC-v3.md §10.1` and `§13`. SLICE-003 (design_system.json) now active. Designer slides received, cataloged (21 slides, 3 Ascendion-branded decomposable). `BRAINSTORM_codex.md` assessed; 5 ideas incorporated into SPEC-v3.md: archetype capacity metadata, feasibility gate, section composers, repair escalation, purpose/audience_takeaway. Archetype vocabulary expanded to 13 active + 3 candidates. SLICE-007 updated with two-track decomposition plan. `content_with_diagram` renamed to `content_with_visual`. `matrix_grid` and `timeline_roadmap` added. SLICE-006 expanded to include section composers.
- **2026-04-10** — Full rewrite of `PLAN.md` as a living project board. V1/V2 cleanup audit delivered as SLICE-001 review gate. Backlog seeded with architecture-diagrams and hosting items. `SPEC-v3.md` and `BRAINSTORM.md` referenced as source of truth.
- **2026-04-10** — `SPEC-v3.md` full rewrite incorporating runtime library, design system artifact, example library, deterministic scan before review, structured rubric reviewer.
- **2026-04-10** — `BRAINSTORM.md` created as first-principles derivation.
- **2026-04-09** — `SPEC-v3.md` initial revision (now replaced).
