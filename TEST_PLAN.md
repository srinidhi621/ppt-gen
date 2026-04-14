# TEST_PLAN.md — V3 Testing Strategy

**Updated**: 2026-04-14
**Source of truth for architecture**: `SPEC-v3.md`
**Companion artifacts**:
- `assets/benchmarks/v3_test_prompts.xlsx` — 26 benchmark prompts + 9-axis rubric
- `assets/benchmarks/v3_visual_hygiene_checks.xlsx` — 26 mechanical-correctness checks
- `scripts/generate_benchmark_xlsx.py` — regenerate benchmark Excel
- `scripts/generate_visual_hygiene_xlsx.py` — regenerate hygiene Excel

---

## 1) Testing Philosophy

The V3 pipeline has six stages (planner → feasibility gate → builder → sandbox → scanner → reviewer), each with distinct failure modes. Testing is layered accordingly:

- **Fast, automated, every run**: stage contracts, scanner, content fidelity, metrics ledger. No human in the loop. Sub-second to seconds.
- **Automated but heavier**: visual hygiene (scanner-automated subset), example regression suite. Seconds to minutes.
- **Human-in-the-loop**: benchmark evaluation, visual hygiene (LLM-verified subset). Hours. Run periodically, not per-commit.

The goal is to catch as many defects as possible in the fast layer, so that human evaluation is reserved for subjective quality judgments that machines cannot reliably make.

---

## 2) Test Categories

### 2.1 Unit Tests

**Scope**: individual functions and modules in isolation.
**Speed**: milliseconds each.
**When to run**: every code change, CI.

| Module | What to test |
|---|---|
| `ppt_runtime/grid.py` | Grid math: `span()`, `col_left()`, `col_right()`, gutter handling, edge alignment |
| `ppt_runtime/tokens.py` | Token lookup by name, fallback behavior, hex-to-RGBColor conversion |
| `ppt_runtime/canvas.py` | Named anchor positions (`body_left`, `title_area`, etc.), margin math |
| `ppt_runtime/measure.py` | `measure_text` against known strings at known sizes (verified against PowerPoint ground truth); `shrink_to_fit` convergence |
| `ppt_runtime/shapes.py` | `add_rect`, `add_text`, `add_image`, `add_line` produce correct python-pptx objects with expected properties |
| `ppt_runtime/patterns.py` | `draw_card`, `draw_header_bar`, `draw_kicker` — shape count, positions, styles |
| `ppt_runtime/composers.py` | `compose_card_row`, `compose_stat_grid`, `compose_split_columns`, `compose_timeline` — bounding box adherence, child shape count |
| `src/scan/scanner.py` | Each geometry check against a fixture deck with an injected defect. BLOCKING checks must fire; passing decks must return clean reports. |
| `src/scan/content_fidelity.py` | Known input → known output pairs. Coverage score calculation. Placeholder detection. Hallucination flagging. |
| `src/contracts/*.json` | Each contract schema validates a known-good payload and rejects a known-bad payload. |
| `src/sandbox/` | AST pre-scan rejects disallowed imports (`os`, `subprocess`, `socket`). Accepts valid `ppt_runtime` imports. Timeout enforcement. Memory cap enforcement. |
| `src/v3/planner.py` | Schema validation of planner output against contract. Archetype vocabulary membership. Field presence (`purpose`, `audience_takeaway`). |

### 2.2 Integration Tests

**Scope**: multi-stage pipeline segments.
**Speed**: seconds to minutes (involves LLM calls in some cases — mock for CI, live for local validation).
**When to run**: before merging any pipeline-stage change.

| Test | Stages exercised | What to verify |
|---|---|---|
| Single-slide happy path | Plan → feasibility → build → sandbox → scan → PPTX | Output PPTX exists, opens, passes scanner, has expected slide count |
| Multi-slide happy path | Same, with a 5-slide prompt | All slides present, cross-slide consistency checks pass |
| Feasibility gate rejection | Plan → feasibility (with overstuffed content) | Gate rejects, planner retries, second plan passes feasibility |
| Scanner triggers repair | Plan → build → scan (with injected BLOCKING defect) → repair → scan | Repair attempt produced, second scan passes |
| Reviewer triggers repair | Full pipeline with aesthetically weak build | Reviewer flags axes, repair builder runs, second review scores higher |
| Content fidelity integration | Plan → build → content fidelity check | Coverage score ≥ 0.85 for a prompt with 10+ verifiable facts |
| Contract violation handling | Each stage with a malformed handoff payload | Pipeline halts with structured error, no downstream stage executes |

### 2.3 Example Regression Suite

**Scope**: every example file in `examples/`.
**Speed**: seconds per example (no LLM — direct runtime execution).
**When to run**: after any change to `ppt_runtime/`.

**Method**:
1. Execute every `examples/<archetype>/<name>/build.py` against the current runtime.
2. Verify each produces a valid PPTX that passes the full geometry scan.
3. Verify slide count, shape count, and key shape properties match the example's metadata.

**Pass criteria**: zero failures. Any regression blocks the runtime change.

**Future extension** (SLICE B5): store geometry snapshots per example and diff against previous output to catch subtle layout regressions.

### 2.4 Stage Contract Validators

**Scope**: structural correctness of data flowing between pipeline stages.
**Speed**: sub-second (JSON schema validation + AST inspection).
**When to run**: automatically on every pipeline execution, at every handoff point.

| Handoff | Contract checks |
|---|---|
| Planner → Feasibility gate | Every slide has `archetype`, `purpose`, `audience_takeaway`; archetype ∈ active vocabulary; item count ≤ `max_items`; word count ≤ `max_words` |
| Planner → Builder | `deck_plan.json` passes JSON Schema; no duplicate `slide_id`; slide count ∈ [1, 20]; all referenced archetypes have examples |
| Builder → Sandbox | `build_deck.py` passes AST pre-scan; imports only `ppt_runtime.*`; no raw hex color literals; no hardcoded pixel positions |
| Sandbox → Scanner | Output file exists, is valid PPTX, slide count matches plan |
| Scanner → Reviewer | `geometry_report.json` passes schema; zero BLOCKING findings |
| Reviewer → Repair | `review_feedback.json` passes schema; all scored slides have all required axes |

**Implementation**: JSON Schema files in `src/contracts/`. Validator utility called at each stage boundary. Failure halts the pipeline with a structured error naming the contract, the violation, and the failing value.

### 2.5 Automated Content Fidelity Check

**Scope**: does the output PPTX contain what the user asked for?
**Speed**: seconds (text extraction + fuzzy matching).
**When to run**: every pipeline execution, after scanner, before reviewer.

**Method**:
1. Extract all text runs from slides and speaker notes in the output PPTX.
2. Extract key facts from the user's input: named entities, numbers, percentages, proper nouns, quoted phrases.
3. Fuzzy-match each input fact against extracted text (token overlap with configurable threshold).
4. Score: `coverage = matched_facts / total_facts`.

**Output**: `content_fidelity_report.json`:
```jsonc
{
  "coverage_score": 0.92,
  "total_facts": 12,
  "matched_facts": 11,
  "dropped_facts": ["Q3 revenue grew 14%"],
  "unmatched_output_segments": ["Leading the industry transformation"],
  "placeholder_leaks": [],
  "markdown_leaks": []
}
```

**Pass criteria**:
- `coverage_score ≥ 0.85`: PASS
- `0.60 ≤ coverage_score < 0.85`: WARNING (reported to reviewer as context)
- `coverage_score < 0.60`: BLOCKING (triggers repair)
- Any placeholder or markdown leak: BLOCKING

### 2.6 Visual Hygiene Checks

**Scope**: mechanical correctness of the output PPTX (brand, layout, rendering).
**Speed**: scanner-automated checks run in seconds; LLM-verified checks require image export + LLM call (30-60s).
**When to run**: scanner-automated checks on every run; LLM-verified checks on benchmark runs and spot checks.

26 binary pass/fail checks across 6 categories. Full definitions in `assets/benchmarks/v3_visual_hygiene_checks.xlsx`.

| Category | Check IDs | Scanner-automated | LLM-verified |
|---|---|---|---|
| Color | VH-01 – VH-05 | VH-01 (palette fills), VH-02 (text colors) | VH-03 (accent limit), VH-04 (contrast), VH-05 (invisible shapes) |
| Typography | VH-06 – VH-09 | VH-06 (font allowlist), VH-07 (type scale) | VH-08 (bold usage), VH-09 (ALLCAPS) |
| Spatial | VH-10 – VH-15 | VH-10 (off-canvas), VH-11 (overflow), VH-14 (gutters) | VH-12 (safe area), VH-13 (overlaps), VH-15 (grid alignment) |
| Content Rendering | VH-16 – VH-19 | VH-16 (markdown), VH-17 (placeholder), VH-18 (image resolution) | VH-19 (empty frames) |
| Cross-Slide | VH-20 – VH-23 | VH-20 (title position), VH-21 (title style) | VH-22 (kicker style), VH-23 (body font) |
| Structural | VH-24 – VH-26 | VH-24 (empty slides), VH-25 (slide count) | VH-26 (visual elements) |

**Severity**: 12 BLOCKING, 14 WARNING.
**Deck-level pass**: zero BLOCKING failures AND ≤ 3 WARNING failures.

### 2.7 Benchmark Evaluation

**Scope**: end-to-end output quality on realistic prompts.
**Speed**: slow (human scoring). Hours per full run.
**When to run**: before V3 cutover; after major pipeline changes; periodically for quality tracking.

26 test prompts in `assets/benchmarks/v3_test_prompts.xlsx` across 7 sections:

| Section | Tests | What it exercises |
|---|---|---|
| Core archetypes | TP-01 – TP-10 | One prompt per active archetype, mid-density |
| Untested archetypes | TP-11 – TP-13 | `quote_callout`, `section_break`, `stat_list_with_icons` |
| Edge cases | TP-14 – TP-16 | Sparse content, capacity overflow, ambiguous archetype |
| Audience variations | TP-17 – TP-18 | Board-level vs. technical team |
| Content type variations | TP-19 – TP-20 | Narrative case study, sales persuasion |
| Deck-level | TP-21 – TP-24 | Multi-slide decks (5-8 slides) |
| Stress tests | TP-25 – TP-26 | Minimal prompt, content dump |

Scored on 9 axes (7 base + 2 multi-slide-only):

| Axis | Scope |
|---|---|
| Content Fidelity | All |
| Archetype Selection | All |
| Visual Hierarchy | All |
| Density & Readability | All |
| Brand Consistency | All |
| Editability | All |
| Mechanical Defects | All |
| Cross-Slide Consistency | Multi-slide only |
| Narrative Flow | Multi-slide only |

**Per-prompt pass**: average ≥ 3.5, no axis ≤ 2.
**Benchmark pass**: ≥ 70% of prompts pass AND V3 rated higher than V1 on majority.

### 2.8 Run Metrics Ledger

**Scope**: operational telemetry for every pipeline run.
**Speed**: zero overhead (single CSV append at pipeline end).
**When to run**: every pipeline execution, automatically.

**Fields** (appended to `runs/metrics_ledger.csv`):
```
run_id, timestamp, prompt_hash, slide_count,
planner_tokens_in, planner_tokens_out,
builder_tokens_in, builder_tokens_out,
reviewer_tokens_in, reviewer_tokens_out,
build_attempts, repair_rounds,
scanner_blocking_count, scanner_warning_count,
content_fidelity_score,
reviewer_avg_score, reviewer_min_axis,
total_latency_sec, outcome
```

**Key metrics to track over time**:

| Metric | What it tells you | Alert threshold |
|---|---|---|
| First-pass build success rate | Builder prompt quality. Higher = builder produces valid code more often. | < 60% over 10 runs |
| Repair frequency | How often the reviewer finds issues worth fixing. | > 50% of runs need repair |
| Repair effectiveness | Does repair actually improve scores? | < 60% of repairs improve reviewer avg |
| Scanner blocking rate | How often builds have mechanical defects. | > 30% of first-pass builds |
| Content fidelity score (avg) | Are we preserving user content? | Average < 0.85 over 10 runs |
| Total tokens per run | Cost control. | > 2x baseline for same slide count |
| Total latency per run | Performance. | > 2x baseline for same slide count |

The ledger is append-only and observational. No pipeline logic reads from it.

---

## 3) Per-Stage Test Coverage

This table maps every pipeline stage to the tests that verify it. A stage should not be considered done until all its test categories are implemented.

| Stage | Unit | Contract | Integration | Content Fidelity | Scanner/Hygiene | Benchmark | Metrics |
|---|---|---|---|---|---|---|---|
| Planner | Schema validation, archetype membership, field presence | Planner → Feasibility, Planner → Builder | Single-slide & multi-slide happy path | -- | -- | Archetype Selection axis | planner_tokens |
| Feasibility gate | Capacity math | Planner → Feasibility | Feasibility rejection test | -- | -- | TP-15 (overflow) | -- |
| Builder | AST pre-scan, import restrictions | Builder → Sandbox | Happy path, repair path | -- | -- | All prompts | builder_tokens, build_attempts |
| Sandbox | Import rejection, timeout, memory cap | Sandbox → Scanner | Happy path | -- | -- | -- | -- |
| Scanner | Each check vs. fixture decks | Scanner → Reviewer | Scanner triggers repair | -- | All scanner-automated VH checks | Mechanical Defects axis | scanner_blocking, scanner_warning |
| Content fidelity | Coverage calculation, fact extraction | -- | Content fidelity integration | Primary owner | VH-16 (markdown), VH-17 (placeholder) | Content Fidelity axis | content_fidelity_score |
| Reviewer | Schema validation | Reviewer → Repair | Reviewer triggers repair | -- | LLM-verified VH checks | Visual Hierarchy, Density, Brand axes | reviewer_avg, reviewer_min |
| Repair loop | -- | -- | Repair integration | -- | -- | -- | repair_rounds |
| Runtime | Grid, tokens, canvas, measure, shapes, patterns, composers | -- | Example regression suite | -- | Spatial VH checks | -- | -- |

---

## 4) Test Execution Tiers

### Tier 1 — Per-Run (every pipeline execution)
Fully automated, no human effort. Results in run artifacts.

1. Stage contract validation (all 6 handoffs)
2. Deterministic scanner (10 checks from §4.6)
3. Content fidelity check
4. Metrics ledger append

**Cost**: seconds. **Coverage**: structural correctness, content preservation, mechanical defects.

### Tier 2 — Per-Change (every code change to runtime or pipeline)
Automated, runs in CI or locally before merge.

1. Unit test suite
2. Example regression suite (re-execute all examples)
3. Integration test suite (with mocked LLM calls)

**Cost**: seconds to minutes. **Coverage**: code correctness, runtime stability, pipeline wiring.

### Tier 3 — Periodic (before cutover, after major changes)
Requires human scoring and/or live LLM calls.

1. Full benchmark evaluation (26 prompts, 9-axis scoring)
2. Full visual hygiene audit (26 checks including LLM-verified)
3. Metrics ledger trend analysis (plot key metrics, flag regressions)

**Cost**: hours. **Coverage**: subjective quality, brand polish, quality trends.

---

## 5) Pass Criteria Summary

| Level | Criteria | Gating? |
|---|---|---|
| Per-run: contracts | All 6 handoff contracts pass | Yes — pipeline halts on failure |
| Per-run: scanner | Zero BLOCKING findings | Yes — triggers repair loop |
| Per-run: content fidelity | `coverage_score ≥ 0.60` | Yes (BLOCKING below 0.60) |
| Per-run: content fidelity | `coverage_score ≥ 0.85` | Advisory (WARNING below 0.85) |
| Per-run: visual hygiene (automated) | Zero BLOCKING in scanner-automated subset | Yes — triggers repair loop |
| Per-change: unit tests | All pass | Yes — blocks merge |
| Per-change: example regression | All examples execute and pass scanner | Yes — blocks runtime change |
| Periodic: benchmark | ≥ 70% of 26 prompts pass (avg ≥ 3.5, no axis ≤ 2) | Yes — gates V3 cutover |
| Periodic: benchmark | V3 rated higher than V1 on majority of prompts | Yes — gates V3 cutover |
| Periodic: visual hygiene (full) | Zero BLOCKING, ≤ 3 WARNING per deck | Advisory — informs iteration |
| Periodic: metrics trends | No metric regresses > 2x baseline over 10 runs | Advisory — flags investigation |

---

## 6) Test Artifacts and Locations

| Artifact | Location | Generated by |
|---|---|---|
| Benchmark prompts Excel | `assets/benchmarks/v3_test_prompts.xlsx` | `scripts/generate_benchmark_xlsx.py` |
| Visual hygiene checks Excel | `assets/benchmarks/v3_visual_hygiene_checks.xlsx` | `scripts/generate_visual_hygiene_xlsx.py` |
| Contract schemas | `src/contracts/*.json` | Hand-authored (SLICE-008) |
| Unit tests | `tests/` | Hand-authored (per-slice) |
| Example library | `examples/<archetype>/<name>/` | SLICE-007 |
| Geometry report | `runs/<run_id>/geometry_report.json` | Scanner (per-run) |
| Content fidelity report | `runs/<run_id>/content_fidelity_report.json` | Content fidelity check (per-run) |
| Review feedback | `runs/<run_id>/review_feedback.json` | Reviewer (per-run) |
| Metrics ledger | `runs/metrics_ledger.csv` | Pipeline (per-run, append-only) |
| Benchmark scores | `assets/benchmarks/v3_test_prompts.xlsx` Sheet 2 | Human (periodic) |
| Hygiene scores | `assets/benchmarks/v3_visual_hygiene_checks.xlsx` Sheet 2 | Human + LLM (periodic) |

---

## 7) Implementation Schedule

Tests are built alongside the slices they verify:

| Slice | Tests delivered |
|---|---|
| SLICE-004 (runtime skeleton) | Unit tests for grid, tokens, canvas |
| SLICE-005 (measure_text) | Unit tests for measurement, shrink_to_fit |
| SLICE-006 (shapes, patterns, composers) | Unit tests for shapes, patterns, composers |
| SLICE-006b (runtime validation) | Example regression suite bootstrap (1 example) |
| SLICE-007 (example seeding) | Example regression suite expansion |
| SLICE-008 (scanner + contracts + fidelity) | Scanner unit tests, contract schema files + validator, content fidelity unit tests, fixture decks with injected bugs |
| SLICE-009 (sandbox) | Sandbox unit tests (import rejection, timeout, memory) |
| SLICE-010 (planner) | Planner output validation tests, feasibility gate tests |
| SLICE-011 (builder + e2e) | Integration tests (happy path, contract violation handling) |
| SLICE-012 (reviewer + repair) | Integration tests (repair path, reviewer triggers repair) |
| SLICE-013 (CLI + metrics) | Metrics ledger implementation, end-to-end CLI tests |
| SLICE-014 (benchmark) | Full benchmark evaluation run, full visual hygiene audit, metrics trend analysis |
