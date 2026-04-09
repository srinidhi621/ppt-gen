# SPEC-v3.md — Planner / Builder / Reviewer Primitive Composition Architecture

Status (`2026-04-09`):
- `SPEC-v3.md` is the active architecture for new development.
- `SPEC-v2.md` is retained as historical context for the recipe-driven direction that was explored but not completed.
- The currently shipped CLI pipeline is still the placeholder/layout-bound path until V3 is implemented.

## 0) Purpose

V3 defines a presentation-generation architecture optimized for one thing the repo still does not do well enough: high-polish native slide composition.

The core idea is:
- a `planner` model decides the final narrative, slide intent, and content structure;
- a `builder` coding model writes disposable `python-pptx` code that composes each slide from native PowerPoint primitives;
- a `reviewer` multimodal model inspects rendered slides and requests bounded repairs;
- the system retries build and repair within controlled limits.

V3 keeps the required business constraints:
- output must remain a fully editable native `.pptx`;
- the branded template remains the visual anchor;
- rendering remains local and `python-pptx`-based;
- deterministic validation, artifact persistence, and quality gates remain mandatory.

## 0.1) Why V3 Exists

V1 proved that the repo can:
- ingest user content and cues;
- produce valid PPTX files;
- enforce text budgets and basic visual coverage;
- run a review loop with persisted artifacts.

V1 also proved its main limitation:
- placeholder binding produces acceptable form-fill output, not strong composition.

V2 moved in the right direction conceptually by defining recipe-driven composed slides, but it still required a substantial internal composition engine, slot schema system, and recipe catalog before strong slides could ship consistently.

V3 changes the tradeoff:
- instead of building a large internal recipe engine up front,
- the system uses a coding model as a disposable slide-composition worker,
- while the repo owns the execution harness, safeguards, review loop, and quality gates.

## 0.2) Relationship To `alternate-approach/build.py`

`alternate-approach/build.py` validated an important point:
- the repo can produce stronger slides by composing native PowerPoint text boxes and shapes directly;
- this can be done with the same `python-pptx` library already used in the repo;
- blank or near-blank template layouts are a viable canvas for branded slide construction.

What `alternate-approach/build.py` is not:
- a planner;
- a reusable runtime contract;
- a safe execution harness;
- a repairable multi-stage pipeline.

V3 generalizes the same rendering style into a controlled planner -> builder -> reviewer system.

## 1) Core Architectural Decision

The central V3 decision is:

**The planner decides what the slide should say and what it should feel like. The builder writes disposable primitive-composition code that decides how to realize that slide.**

This means:
- the planner does not output coordinates;
- the builder is not constrained to template placeholders;
- the builder is allowed to author arbitrary slide-building code inside a sandboxed environment;
- the generated code is a per-run artifact, not a durable source-code asset.

## 1.1) What V3 Keeps

V3 keeps and reuses as much of the current repo as possible:
- markdown normalization and cue parsing;
- asset catalogs and visual vocabulary;
- multimodal review-image export;
- diagnose reports and quality gates;
- run artifact persistence under `runs/<run_id>/`;
- branded template, theme, and canvas metadata.

## 1.2) What V3 Replaces

V3 replaces the current production rendering contract:
- from `layout_id + fields + asset_refs` bound into template placeholders;
- to `planner brief + builder code + executed primitive composition`.

The current placeholder renderer remains useful for:
- historical reference;
- regression comparison;
- fallback debugging during migration.

It is not the target production path for V3.

## 2) Non-Negotiable Constraints

### 2.1 Editable Native PPTX

Slides must be built from native PowerPoint objects wherever feasible:
- text boxes;
- shapes;
- connectors;
- pictures;
- tables;
- charts when practical.

Rasterized slide screenshots are not acceptable as the final slide body.

### 2.2 Template-Anchored Composition

The branded template remains the source of:
- theme;
- masters;
- color identity;
- typography defaults;
- reusable canvas layouts.

V3 is not template-placeholder-first, but it is still template-anchored.

### 2.3 No GUI Automation In Core Render Path

Core generation and review must remain headless.

Allowed review export paths:
- `soffice -> pdf -> png`;
- Aspose export when available and license-safe for review artifacts.

### 2.4 Raster Assets In Render Path

Render-time visuals must resolve to raster-compatible assets:
- PNG;
- JPG;
- WebP.

SVG may exist in source catalogs, but not as the final direct render dependency.

### 2.5 Sandbox Execution For Builder Code

Generated builder code must execute only inside an isolated runtime with:
- no network access;
- restricted filesystem access;
- import allowlist;
- runtime timeout;
- retry budget;
- full logging of attempts and failures.

### 2.6 No PowerPoint Autofit Assumptions

`python-pptx` does not replicate PowerPoint UI autofit behavior.

V3 must still protect readability through:
- planner-side text budgets;
- builder-side composition heuristics;
- deterministic post-render diagnostics;
- multimodal review and bounded repair.

## 3) High-Level Pipeline

V3 target flow:

`User Input -> Normalize -> Planner -> Asset/Canvas Prep -> Builder Attempt(s) -> Execute Builder Code -> Render PPTX -> Diagnose + Review Images -> Multimodal Reviewer -> Builder Repair Attempt(s) -> Render V2 -> Quality Gates -> Stop`

## 3.1) Planner Phase

The planner is a reasoning-focused model call. It takes:
- the user prompt and source content;
- normalized markdown and cues;
- template/canvas metadata;
- brand tokens;
- asset inventory summaries;
- slide-count and density constraints;
- any optional user style directives.

It outputs a structured deck plan that is final on:
- narrative arc;
- slide roster;
- per-slide title and key messages;
- content hierarchy;
- visual intent;
- density expectations;
- must-preserve constraints.

It does not output:
- coordinates;
- raw `python-pptx` code;
- shape-by-shape geometry.

## 3.2) Builder Phase

The builder is a coding-model call. It takes:
- the planner output;
- concrete asset paths and design tokens;
- allowed helper API docs;
- canvas metadata;
- execution constraints;
- prior failure traces or reviewer feedback when retrying.

It returns disposable Python code that:
- opens the branded template;
- selects blank or header-only canvas layouts as needed;
- composes slides from native primitives;
- writes the final PPTX to the run directory.

Builder code may be arbitrarily different across runs.

That is acceptable by design.

## 3.3) Reviewer Phase

The reviewer is a multimodal model call over:
- rendered slide images;
- planner output;
- diagnose report;
- build execution report;
- optional code summary or slide manifest.

It returns structured repair requests focused on:
- narrative clarity;
- visual hierarchy;
- spacing and alignment;
- slide density;
- inconsistent treatment across slides;
- ugly or awkward primitive composition choices.

It does not request raw coordinate deltas as the primary interface.
It requests intended changes to slide behavior and appearance.

## 4) Contracts

## 4.1) Planner Output Contract

The planner output should be a structured JSON artifact, tentatively `deck_blueprint_v1.json`.

Minimum shape:

```json
{
  "deck_id": "legacy_system_navigator",
  "run_id": "run_20260409_120000",
  "global_style": {
    "tone": "executive_consulting",
    "theme": "light",
    "design_keywords": ["clean", "assertive", "high-contrast"]
  },
  "slides": [
    {
      "slide_id": "modernization_case",
      "purpose": "Explain why the current estate creates risk and delay.",
      "headline": "Legacy complexity is now a growth constraint",
      "subheadline": "Fragmentation slows delivery and compounds operational risk.",
      "body_content": [
        "Point one",
        "Point two",
        "Point three"
      ],
      "speaker_notes": "Optional overflow or presenter support.",
      "visual_intent": {
        "pattern": "comparison_cards",
        "must_include": ["risk callout", "before_vs_after"],
        "avoid": ["stock_photo_only"]
      },
      "density_budget": {
        "max_words": 75,
        "max_visual_groups": 4
      },
      "must_preserve": [
        "headline wording",
        "brand-safe color usage"
      ],
      "acceptance_checks": [
        "clear left-to-right reading order",
        "single dominant headline",
        "at least one non-text visual anchor"
      ]
    }
  ]
}
```

## 4.2) Builder Input Contract

The runtime should assemble a builder input packet, tentatively `builder_input_v1.json`, containing:
- planner output;
- canvas config;
- token overrides;
- resolved asset manifest;
- allowed helper references;
- execution limits;
- prior failure traces or reviewer deltas.

The builder should see:
- concrete asset paths, not just concept names;
- concrete canvas choices, not only abstract slide types;
- explicit constraints on file writes and imports.

## 4.3) Builder Output Contract

The builder returns:
- `build_deck_v1.py` or `build_deck_v2.py`;
- optional `build_manifest_v1.json` summarizing slide strategy;
- no shell commands;
- no external downloads;
- no dependency installation steps.

The runtime then executes the code in the VM and persists:
- stdout/stderr;
- exit code;
- traceback on failure;
- output PPTX path;
- slide count and output sanity checks.

## 4.4) Reviewer Output Contract

The reviewer output should be structured, slide-addressable, and repair-oriented.

Minimum fields:
- summary;
- slide findings;
- repair requests;
- must-preserve constraints;
- severity.

Example repair request types:
- promote a metric into a hero treatment;
- reduce card count from 4 to 3;
- replace stacked bullets with a comparison block;
- increase whitespace and simplify footer treatment;
- align icon style or reduce accent overuse.

## 5) Builder Runtime And Safeguards

## 5.1) Disposable Code Policy

Generated builder code is disposable.

It is acceptable for:
- the code to differ across identical prompts;
- the code to be thrown away after the run;
- the code to be regenerated on retries or review repair.

The durable product is:
- the generated PPTX;
- the run artifacts;
- the planner/reviewer records;
- the sandbox and evaluation framework.

## 5.2) Execution Environment

Builder code must execute with:
- isolated VM or equivalent container boundary;
- network disabled;
- workspace limited to a run-scoped writable directory;
- fixed installed library set;
- allowed imports only.

Initial import allowlist should be narrow, for example:
- `pptx`
- `json`
- `math`
- `pathlib`
- `typing`
- `dataclasses`
- approved local helper modules

## 5.3) Retry Policy

Default retry budgets:
- up to 3 build attempts before visual review;
- up to 2 repair attempts after review;
- early stop on hard safety violation.

Retry reasons:
- syntax error;
- import error;
- runtime exception;
- missing PPTX output;
- slide count mismatch;
- catastrophic render defect detected by diagnose.

## 5.4) Failure Handling

The system must persist every failed attempt for debugging:
- prompt given to builder;
- returned code;
- execution log;
- traceback;
- summarized failure reason.

Failures must not be silently overwritten.

## 6) Canvas, Theme, And Asset Usage

V3 should use the template as a canvas provider rather than as a placeholder prison.

Primary V3 canvases:
- `Header Only - Light`
- `Header Only - Dark`
- `Blank`

These are already captured in `assets/template/canvas_config.json`.

Theme and token guidance comes from:
- `assets/template/token_overrides.json`
- template theme fonts and colors
- existing asset catalogs under `assets/catalog/` and `assets/icons/`

The builder may:
- add text boxes;
- add shapes;
- add pictures;
- add connector-like structures;
- edit an inherited title placeholder if appropriate;
- leave placeholder binding unused for fully composed slides.

## 7) Diagnostics And Review

V3 still depends on deterministic post-render checks.

The current diagnose/review stack should be preserved and adapted, not discarded.

Required post-build checks:
- deck file exists;
- expected slide count matches planner output;
- no empty slides;
- no failed image paths;
- diagnose report generated;
- review images generated at acceptable resolution.

## 7.1) Review Scope

The multimodal reviewer should score:
- message clarity;
- hierarchy and emphasis;
- alignment and spacing;
- primitive composition quality;
- deck-level consistency and variation.

The reviewer should explicitly compare what the planner intended versus what the builder delivered.

## 7.2) Repair Scope

Repair should be bounded where possible:
- patch only affected slides;
- preserve accepted slides;
- preserve headline and must-preserve fields unless the reviewer explicitly flags them.

The repair loop may still regenerate the deck-level code artifact if needed, but the prompts should make local repair the default.

## 8) Quality Gates

V3 keeps the spirit of existing gates and adds builder-specific checks.

Minimum V3 final gates:
- no blocking overflow;
- build executed successfully;
- slide count matches planner output;
- no markdown marker leaks;
- minimum visual density;
- minimum primitive presence on composed slides;
- no catastrophic alignment or empty-slide failures in review;
- image asset rendering success where requested.

V3 should continue to persist:
- `quality_gates_v2.json` for backward compatibility during migration, or
- a new `quality_gates_v3.json` once the CLI path formally upgrades.

## 9) Run Artifacts

V3 minimum run artifacts should include:
- `planner_input.json`
- `deck_blueprint_v1.json`
- `builder_input_v1.json`
- `build_attempts/attempt_01/`
- `build_attempts/attempt_02/`
- `build_attempts/attempt_03/`
- `build_deck_v1.py`
- `build_exec_report_v1.json`
- `deck_v1.pptx`
- `review_images/v1/slide_*.png`
- `diagnose_report_v1.json`
- `review_feedback_v1.json`
- `build_deck_v2.py`
- `build_exec_report_v2.json`
- `deck_v2.pptx`
- `review_images/v2/slide_*.png`
- `diagnose_report_v2.json`
- `quality_gates_v2.json` or `quality_gates_v3.json`
- `run_summary.json`
- `run_log.jsonl`

## 10) Logging Contract

V3 should emit stage markers such as:
- `NORMALIZE_DONE`
- `PLANNER_DONE`
- `ASSET_PREP_DONE`
- `BUILD_ATTEMPT_STARTED`
- `BUILD_ATTEMPT_FAILED`
- `BUILD_CODE_READY`
- `BUILD_EXEC_V1_DONE`
- `REVIEW_IMAGES_INGESTED`
- `DIAGNOSE_V1_DONE`
- `MULTIMODAL_REVIEW_DONE`
- `REPAIR_BUILD_ATTEMPT_STARTED`
- `REPAIR_BUILD_ATTEMPT_FAILED`
- `BUILD_EXEC_V2_DONE`
- `DIAGNOSE_V2_DONE`
- `QUALITY_GATES_V2` or `QUALITY_GATES_V3`
- `RUN_COMPLETE`
- `RUN_FAILED_BUILD`
- `RUN_FAILED_QUALITY_GATES`

## 11) Testing Strategy

Before shipping V3 slices:
- unit tests for planner and reviewer schemas;
- unit tests for builder sandbox policy and import restrictions;
- unit tests for retry orchestration;
- integration tests for one-slide primitive composition;
- integration tests for build failure -> retry -> success;
- integration tests for review -> repair -> rerender;
- structural visual tests based on diagnose/review artifacts, not pixel-perfect snapshots.

Do not rely on pixel-perfect image diffs as the primary test mechanism.

## 12) Migration Strategy

Migration should be incremental.

Phase 1:
- add planner and builder schemas;
- add VM execution harness;
- keep current pipeline intact.

Phase 2:
- add one primitive-composed slide path on header-only or blank canvas;
- compare against placeholder baseline.

Phase 3:
- route full decks through planner -> builder -> reviewer;
- keep old renderer as debug fallback only.

Phase 4:
- retire placeholder-first generation from the default path once V3 quality is clearly better.

## 13) Explicit Non-Goals

V3 does not require:
- a full internal recipe engine before any composed slides ship;
- deterministic reuse of generated builder code across runs;
- HTML/CSS or browser rendering as a parallel presentation engine;
- LLM-generated coordinates in planner output;
- committing generated builder code into the repository.

## 14) Success Criteria

V3 is successful when all are true:
1. Planner outputs stable, high-quality slide briefs from real user prompts.
2. Builder can compose editable slides from primitives on the branded template canvas.
3. Retry handling makes build failures operationally tolerable.
4. Multimodal review materially improves visual quality on rerender.
5. The generated deck is clearly better than the current placeholder-bound output on benchmark prompts.
