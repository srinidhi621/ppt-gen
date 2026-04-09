# PLAN.md — V3 Planner / Builder / Reviewer Execution Plan

## 0) Objective

Implement the active V3 architecture from `SPEC-v3.md`:
- planner model produces the final deck blueprint and slide briefs;
- coding model builds the deck by composing native PowerPoint primitives with disposable `python-pptx` code;
- multimodal reviewer evaluates rendered slides and drives bounded repair;
- runs remain artifact-heavy, testable, and quality-gated.

## 1) Build Rules

1. Ship end-to-end slices only.
2. Keep the current CLI operational while V3 is landing.
3. CLI first; web and service layers are downstream concerns.
4. Do not commit generated builder code as product logic.
5. Execute builder code only in an isolated runtime with explicit safeguards.
6. Preserve native editable PPTX output.
7. Prefer blank and header-only template canvases for primitive-composed slides.
8. Keep deterministic diagnose, review-image export, logging, and quality gates.
9. Every slice requires persisted artifacts and tests.
10. No slice is complete until the new path is better than the placeholder baseline for that scope.

## 2) Starting Point (`2026-04-09`)

Already present:
- normalization and cue parsing;
- layout, asset, and vocabulary catalogs;
- placeholder renderer and preflight remediation;
- automated review-image export;
- multimodal review scaffold;
- quality gates and run logging;
- template canvas metadata and token overrides;
- reference primitive-composition prototype in `alternate-approach/build.py`.

Missing for V3:
- planner output schema for builder-oriented slide briefs;
- builder sandbox and retry harness;
- codex-oriented builder prompt + execution loop;
- primitive-composition helper runtime;
- build execution reports and attempt artifacts;
- builder repair loop;
- V3-specific quality gates and benchmark evaluation.

## 3) Program-Level Exit Metrics

The V3 program is complete when all are true:
1. One-slide primitive-composed generation works end-to-end from prompt to reviewed, repaired PPTX.
2. A multi-slide deck can be built through planner -> builder -> reviewer without manual edits.
3. Build retries recover from common syntax/runtime failures automatically.
4. Final decks are visibly stronger than the placeholder baseline on benchmark prompts.
5. Run artifacts make planner, builder, and reviewer behavior debuggable after failures.

## 4) Slice Tracker

Statuses: `planned | in_progress | complete | blocked`

| Slice | Focus | Status | User-visible Demo |
|---|---|---|---|
| S0 | V3 artifact contracts + doc alignment | complete | `SPEC-v3.md` + aligned repo plan |
| S1 | Builder sandbox + execution harness | planned | run disposable builder code safely |
| S2 | Primitive helper runtime + single-slide build | planned | one composed slide from code |
| S3 | Planner output schema + planner API flow | planned | prompt -> deck blueprint JSON |
| S4 | Planner -> builder integration | planned | prompt -> built PPTX without review |
| S5 | Multimodal review -> builder repair loop | planned | reviewed and repaired PPTX |
| S6 | Multi-slide deck support + deck-level gates | planned | 5-10 slide composed deck |
| S7 | Benchmarking, hardening, and baseline comparison | planned | benchmark report and release decision |

## 5) Vertical Slices

## S1 — Builder Sandbox + Execution Harness

### Goal

Safely run disposable generated builder code with retries and full artifact capture.

### Build

- Define builder attempt directory layout under `runs/<run_id>/build_attempts/`.
- Define import allowlist and execution policy.
- Implement builder code execution wrapper with:
  - timeout;
  - isolated writable root;
  - no network;
  - stdout/stderr capture;
  - traceback capture;
  - retry orchestration.
- Persist `build_exec_report_v1.json`.

### Demo

Run a trivial generated builder script that opens the template and writes a one-slide PPTX.

### Tests

- execution success case;
- syntax-error retry case;
- runtime-error retry case;
- import-policy rejection case;
- output-file existence assertions.

### Exit Criteria

1. Disposable builder code can run safely.
2. Common failures are persisted and surfaced clearly.
3. Retry behavior is deterministic and test-covered.

## S2 — Primitive Helper Runtime + Single-Slide Build

### Goal

Replace placeholder fill with direct primitive composition for one slide.

### Build

- Add a minimal approved helper runtime for builder code:
  - template loader;
  - canvas selection;
  - token access;
  - shape/text helpers;
  - image insertion helpers.
- Recreate one high-polish slide similar in spirit to `alternate-approach/build.py`.
- Use native shapes and text boxes on blank or header-only canvas.

### Demo

Generate one editable slide from builder code only.

### Tests

- slide contains native shapes/text boxes;
- output PPTX opens successfully;
- required title/header structure exists;
- diagnose and review-image export succeed.

### Exit Criteria

1. One composed slide is visibly better than placeholder output for the same content.
2. Slide remains editable in PowerPoint.
3. The helper runtime is sufficient for nontrivial composed layouts.

## S3 — Planner Output Schema + Planner API Flow

### Goal

Make the planner produce builder-ready slide briefs instead of placeholder-bound `DeckIR`.

### Build

- Define `deck_blueprint_v1.json` schema.
- Add planner prompt contract for:
  - slide purpose;
  - headline and subheadline;
  - body content;
  - visual intent;
  - density budget;
  - must-preserve constraints;
  - acceptance checks.
- Add planner artifact persistence.

### Demo

Prompt -> structured deck blueprint without rendering.

### Tests

- schema validation;
- prompt construction tests;
- basic planner retry tests;
- fixture coverage for one realistic prompt.

### Exit Criteria

1. Planner output is valid and builder-oriented.
2. Planner no longer depends on placeholder layout IDs as the main abstraction.
3. Artifacts are stable enough to drive downstream build prompts.

## S4 — Planner -> Builder Integration

### Goal

Build a full PPTX from planner output through generated primitive-composition code.

### Build

- Assemble `builder_input_v1.json` from planner output, tokens, canvas config, and asset paths.
- Create builder prompts for coding-model generation.
- Execute builder result and persist `build_deck_v1.py`.
- Produce `deck_v1.pptx`.

### Demo

Prompt -> planner -> builder -> PPTX.

### Tests

- end-to-end one-slide integration;
- end-to-end multi-slide smoke test;
- builder-input assembly tests.

### Exit Criteria

1. No manual code editing is required to get a composed PPTX.
2. Build retries recover common failures.
3. Output path is robust enough for review.

## S5 — Multimodal Review -> Builder Repair Loop

### Goal

Use visual feedback to improve composed slides rather than only re-planning text/layout placeholders.

### Build

- Update review prompt for primitive-composed slides.
- Feed reviewer:
  - review images;
  - planner output;
  - diagnose report;
  - build execution report;
  - optional build manifest.
- Create repair-focused builder prompt that preserves accepted slides where possible.
- Produce `deck_v2.pptx`.

### Demo

Prompt -> build V1 -> review -> repair build -> build V2.

### Tests

- reviewer schema validation;
- repair prompt construction;
- repair build retry test;
- end-to-end reviewed slide improvement flow.

### Exit Criteria

1. Review feedback becomes actionable for the builder.
2. Repair loop improves slide quality without rebuilding the deck blindly every time.
3. V2 artifacts are persisted cleanly.

## S6 — Multi-Slide Deck Support + Deck-Level Gates

### Goal

Scale the V3 path from one slide to real decks.

### Build

- Support 5-10 slide planner outputs.
- Add deck-level consistency checks:
  - headline hierarchy;
  - visual variety;
  - accent restraint;
  - slide density;
  - primitive presence.
- Adapt current quality gates to V3 outputs.

### Demo

Generate a small benchmark deck through the full V3 loop.

### Tests

- multi-slide integration tests;
- gate tests for planner/build/review artifacts;
- artifact completeness tests.

### Exit Criteria

1. Multi-slide deck generation is stable enough for repeated benchmark runs.
2. Quality gates catch obvious failures.
3. Final output is clearly beyond placeholder quality.

## S7 — Benchmarking, Hardening, And Baseline Comparison

### Goal

Decide whether V3 should replace the current default generation path.

### Build

- Define benchmark prompt set.
- Produce side-by-side V1 placeholder vs V3 primitive outputs.
- Track:
  - build success rate;
  - retry counts;
  - review improvement rates;
  - gate pass rates;
  - human-rated quality deltas.
- Harden prompts, helpers, and retries based on benchmark failures.

### Demo

Benchmark report comparing old and new generation paths.

### Tests

- regression suite for benchmark prompts;
- gate pass/fail assertions on curated fixtures.

### Exit Criteria

1. V3 is better than the baseline often enough to justify default routing.
2. Failure modes are understood and operationally manageable.
3. Default-path migration decision is backed by evidence.

## 6) Open Design Decisions

These remain intentionally configurable while implementation starts:
- exact planner model choice within the GPT-5.x family;
- exact coding-model identifier for builder calls;
- whether repair rebuilds only affected slides or regenerates deck-level code;
- whether `quality_gates_v2.json` is retained temporarily for compatibility or replaced immediately by `quality_gates_v3.json`.

## 7) Immediate Next Step

The next implementation step is S1:
- land builder attempt artifacts;
- land execution sandbox policy;
- prove disposable builder code can run safely inside the repo workflow.
