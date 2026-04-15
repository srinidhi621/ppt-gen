# SPEC-v3.md — Planner / Builder / Reviewer With Runtime Library And Example Grounding

Status (`2026-04-14`):

- Revision 2. Incorporates archetype capacity metadata, pre-builder feasibility gate, section-level runtime composers, repair escalation, and planner schema enrichment after independent first-principles review (`BRAINSTORM_codex.md`).
- Designer reference slides received and cataloged (`2026-04-14`). Ascendion-branded slides identified for direct decomposition; layout patterns from other sources will be reimplemented on Ascendion template.
- Active architecture for new development.
- `SPEC-v2.md` retained as historical context for the recipe-driven direction.
- The currently shipped CLI is still the V1 placeholder pipeline until V3 slices land.

## 0) Purpose

V3 produces high-polish native PowerPoint decks by composing six elements:

1. A **design system artifact** that pins grid, type scale, spacing, and brand tokens — authored once per template, consumed by every run.
2. A **planner model** that decides narrative, per-slide archetype, and semantic content. The planner never emits coordinates, hex codes, or font sizes.
3. A small **runtime library** (`ppt_runtime`) that owns spatial arithmetic, brand tokens, text measurement, and shape helpers. It lifts layout from "compute inches" to "span 4 of 12 columns."
4. A **builder coding model** that generates one disposable `build_deck.py` per run, composing slides via the runtime with raw `python-pptx` as an escape hatch.
5. A **deterministic post-build scanner** that catches mechanical bugs (overflow, off-canvas, broken images, palette drift, leaked markdown) before any review token is spent.
6. A **multimodal reviewer scored on a fixed rubric** that produces per-slide repair hints, and a **repair builder** that regenerates the file while preserving accepted slides.

The core bet: LLMs can write code against a named-anchor runtime and a library of hand-validated example decompositions, but they cannot reliably emit coordinates, measure text extents, or maintain cross-slide consistency without scaffolding. V3 provides that scaffolding.

## 0.1) Why This Architecture

V1 (placeholder-fill) proved the repo can produce valid branded PPTX with a multimodal review loop. Its ceiling is form-fill composition.

V2 (recipe engine) was directionally right — native composition on a branded canvas — but required months of recipe library work before a single slide improved.

The earlier V3 revision pivoted to "let a coding model write disposable python-pptx code." That was the right instinct but missed two things:

- **Coding models do not inherit spatial reasoning from code-writing ability.** Asking a coding model to compute `Inches(4.33)` from "4-column span on a 13.33-inch canvas with 0.5-inch margins" is the same failure mode as asking a planning model to emit JSON coordinates. Both fail. The fix is to remove the arithmetic entirely: the builder composes `grid.span(cols=4, of=12)`, not inch literals.
- **One hand-written reference is not grounding, it is an anecdote.** `alternate-approach/build.py` is one data point. Real grounding requires multiple expert-designed slides decomposed into executable runtime code, tagged to archetype labels, and available as few-shot for the builder prompt. The library grows over time.

This revision addresses both.

## 0.2) Relationship To `alternate-approach/build.py`

`alternate-approach/build.py` seeds the example library. It proves native primitive composition on the Ascendion template produces editable branded output with cross-slide consistency when a single author controls the whole file.

It is not:

- a runtime library (its helpers are inline, not importable);
- a reusable abstraction (colors and fonts are module-level constants);
- a validation harness (no retry, no sandbox, no review).

This spec treats it as one example among several, after rewriting it on top of `ppt_runtime` as part of the runtime validation step.

## 1) Core Architectural Decisions

### 1.1 Planner picks archetypes, not coordinates

Planner output is semantic: archetype label from a fixed vocabulary, headline, body content, visual intent, density budget, must-preserve constraints. No EMU values, no hex codes, no shape types, no font sizes. The planner does not know how the builder will draw the slide.

### 1.2 Builder composes against a runtime library

The builder imports `ppt_runtime` and composes via named anchors and grid primitives. The runtime owns:

- canvas metadata and slide creation;
- grid math and named rectangles;
- brand token lookup;
- text measurement via Pillow;
- shape helpers (`add_rect`, `add_text`, `add_image`);
- a small set of opinionated patterns (`draw_card`, `draw_stat_block`, `draw_header_bar`).

Raw `python-pptx` imports are allowed for unusual shapes. Helpers are the preferred path, not the only path.

### 1.3 One code file per deck, single builder call

The builder produces `build_deck.py` containing all slides in one LLM call. Cross-slide consistency is a byproduct of the model holding all slides in one context — not a hope across independent calls.

### 1.4 Repair regenerates the deck file with a preserve-list

On review feedback, the repair builder receives the prior `build_deck.py` verbatim plus per-slide repair hints. Instruction: "Regenerate the full file. Keep non-flagged slides byte-close. Rework flagged slides against the hints." Preservation is prompt-level, not runtime-enforced. Drift on untouched slides is acceptable and will be caught by the next review pass if material.

### 1.5 Mechanical bugs caught deterministically, before review

A post-build scanner walks the built PPTX and reports overflow, off-canvas shapes, broken image rels, palette drift, and leaked markdown markers. Multimodal review runs only on mechanically-clean decks. This separates the two failure classes and prevents reviewer tokens being burned on "the text is cut off."

### 1.6 Design system is stable per template

Grid, type scale, spacing scale, accent policy, and canvas metadata live in `design_system.json` authored once per template. Never LLM-generated. Changed when the template changes.

### 1.7 Examples populate archetypes, they do not replace them

The planner chooses from a fixed archetype vocabulary (label only). Each archetype is populated by one or more hand-validated example decompositions in `examples/`. The builder receives relevant examples as few-shot based on the archetypes the planner selected. Examples are grounding; archetype labels are the planner-to-builder handoff.

### 1.8 Decompositions are executable code, not prose or JSON

Each example is stored as a runnable `example_<name>.py` that imports `ppt_runtime` and produces an editable PPTX. Validation: execute, diff against the original designer PPTX, iterate until structural fidelity is acceptable. If the runtime cannot reproduce an example, the runtime is missing a primitive and must be extended — or the example is out of scope.

## 2) Non-Negotiable Constraints

### 2.1 Editable native PPTX

Final output is built from native PowerPoint objects: text boxes, shapes, connectors, pictures, tables, charts. Rasterized slide images are not acceptable as slide bodies.

### 2.2 Template-anchored composition

The branded template is the source of masters, theme fonts, colors, and canvas dimensions. V3 composes on `Header Only - Light`, `Header Only - Dark`, and `Blank` canvases from `assets/template/canvas_config.json`.

### 2.3 No GUI automation in render or review

Render and review are headless. Allowed review export path: `soffice → pdf → pdftoppm → png`. No AppleScript or PowerPoint-desktop automation.

### 2.4 Raster assets only in render path

Images consumed by the render path must be PNG/JPG/WebP. SVGs may live in source catalogs but are not a render dependency.

### 2.5 Sandbox execution for builder code

Generated `build_deck.py` runs only in an isolated subprocess with:

- network blocked;
- read-only asset mounts (`assets/template/`, `assets/icons/png/`, `assets/catalog/`, `assets/fonts/`, `ppt_runtime/`);
- writable root limited to `runs/<run_id>/build_attempts/attempt_NN/`;
- import allowlist enforced via AST pre-scan;
- CPU and memory limits via `resource.setrlimit`;
- wall-clock timeout;
- stdout, stderr, exit code, and traceback captured.

Acceptance bar for S1: subprocess + AST pre-scan + rlimit + RO bind mounts. VM/Firecracker-level isolation is explicitly out of scope for single-developer use.

### 2.6 No Autofit assumptions; use measurement instead

`python-pptx` does not replicate PowerPoint UI autofit. V3 protects readability through:

- planner-side density budgets on word and group counts;
- `measure_text` calls at build time to size rectangles before committing them;
- deterministic post-build overflow scan;
- rubric-based visual review for remaining aesthetic issues.

### 2.7 Brand consistency via tokens, not hex codes

Generated code must use `tokens.color(...)` and `tokens.type(...)` lookups. Hex literals and inline font-size integers are flagged by the post-build scanner as palette drift.

## 3) Pipeline

```
User Input
  → Phase 1: Normalize
  → Phase 2: Planner (LLM #1)
  → Phase 3: Pre-build Enrichment
  → Phase 4: Builder (LLM #2)
  → Phase 5: Sandbox Execute
  → Phase 6: Deterministic Post-build Scan
      └ mechanical fail → Phase 9a: Repair Build (loop)
  → Phase 7: Review Image Export
  → Phase 8: Multimodal Review (LLM #3, rubric)
      └ aesthetic fail → Phase 9b: Repair Build (loop)
  → Phase 10: Quality Gates
  → Stop
```

`Phase 0: Design System Derivation` runs once per template and is cached as a repo artifact. It is not part of the per-run flow.

## 4) Phase Specifications

### 4.0 Phase 0 — Design System Derivation (one-time per template)

**When run**: once, when the template is introduced or changed. Not per run.

**Inputs**: `assets/template/template.pptx`, `assets/template/canvas_config.json`, `assets/template/token_overrides.json`, `assets/ground_truth/reference_slide_catalog.json`.

**Output**: `assets/template/design_system.json`.

Shape:

```jsonc
{
  "template_id": "corp_deck_2025",
  "canvas": {
    "width_emu": 12192000,
    "height_emu": 6858000,
    "safe_area": {
      "left_emu": 457200, "right_emu": 457200,
      "top_emu": 365760,  "bottom_emu": 182880
    }
  },
  "grid": {
    "cols": 12,
    "gutter_sm_emu": 91440,
    "gutter_md_emu": 137160,
    "gutter_lg_emu": 274320
  },
  "type_scale": {
    "display":  { "font": "Space Grotesk", "size_pt": 40, "bold": true,  "line": 1.05 },
    "title":    { "font": "Space Grotesk", "size_pt": 28, "bold": true,  "line": 1.08 },
    "kicker":   { "font": "Inter",         "size_pt": 11, "bold": true,  "line": 1.1,  "upper": true },
    "subtitle": { "font": "Inter",         "size_pt": 16, "bold": false, "line": 1.2 },
    "body":     { "font": "Inter",         "size_pt": 12, "bold": false, "line": 1.25 },
    "caption":  { "font": "Inter",         "size_pt": 10, "bold": false, "line": 1.2 }
  },
  "spacing_scale": {
    "xs_emu": 73152, "sm_emu": 137160, "md_emu": 228600, "lg_emu": 365760, "xl_emu": 548640
  },
  "tokens": { /* reference to token_overrides.json */ },
  "canvases": { /* reference to canvas_config.json */ },
  "accent_policy": {
    "primary_role": "accent_1",
    "secondary_role": "accent_2",
    "max_accent_roles_per_slide": 2,
    "hero_treatment_accents": ["accent_1"]
  },
  "font_substitution": {
    "PP Neue Machina": "Space Grotesk",
    "Aptos":           "Inter",
    "Calibri":         "Carlito"
  }
}
```

**Authorship**: hand-authored with reference to existing catalogs. Not LLM-generated. Checked into the repo.

**Validation**: a one-time script opens the template, confirms fonts resolve via substitutes on the review-render box, and asserts canvas dims match.

### 4.1 Phase 1 — Normalize

Reuses existing `src/generate_pipeline.py` behavior. Combined markdown → content model + cues. No changes.

**Output**: `normalized_content.json`.

### 4.2 Phase 2 — Planner (LLM #1)

**Inputs**:

- `normalized_content.json`
- `assets/template/design_system.json` (summary, not full)
- Fixed archetype vocabulary (see §5)
- Available example archetype labels (so the planner can prefer archetypes that have examples)
- Slide-count hint and density preference

**Output**: `deck_plan.json`

```jsonc
{
  "deck_id": "legacy_system_navigator",
  "run_id": "run_20260410_120000",
  "style_contract": {
    "tone": "executive_formal",
    "density": "medium",
    "accent_strategy": "monochrome_plus_one",
    "illustrative_richness": "minimal"
  },
  "slides": [
    {
      "slide_id": "operating_principle",
      "archetype": "hero_statement_with_support_columns",
      "canvas": "header_light",
      "purpose": "establish_thesis",
      "audience_takeaway": "The problem is structural, not just operational.",
      "kicker": "01 | The thesis",
      "headline": "Legacy complexity is now a growth constraint",
      "hero_text": "Fragmentation slows delivery and compounds operational risk.",
      "supports": [
        { "label": "The problem",       "body": "..." },
        { "label": "What we won't do",  "body": "..." },
        { "label": "What we will do",   "body": "..." }
      ],
      "visual_intent": {
        "must_include": ["risk_callout"],
        "avoid": ["stock_photo"]
      },
      "density_budget": { "max_words": 85, "max_groups": 3 },
      "must_preserve": ["headline", "accent_strategy"],
      "acceptance": [
        "single dominant focal point",
        "three equally-weighted supports",
        "brand accent usage within policy"
      ]
    }
  ]
}
```

Hard rules:

- Every slide carries an `archetype` from the fixed vocabulary.
- Every slide carries a `purpose` (e.g. `establish_thesis`, `present_evidence`, `compare_options`, `show_process`, `call_to_action`) and an `audience_takeaway` (single sentence the audience should remember). The reviewer evaluates whether the built slide achieves its stated purpose.
- No field names containing `left`, `top`, `width`, `height`, `x`, `y`, `emu`, `inch`, `hex`, `rgb`, `size_pt`.
- `style_contract` is deck-level and immutable during repair unless the reviewer flags it explicitly.

Planner retry budget: 2 retries on schema-validation failure.

### 4.3 Phase 3 — Pre-build Enrichment (deterministic)

**Inputs**: `deck_plan.json`, asset catalogs.

**Steps**:

1. Resolve icon concepts → concrete asset paths via `visual_vocabulary.json`.
2. Resolve branded image hints → concrete paths via `branded_images.json`.
3. Pick examples: for each slide's archetype, select 1-3 relevant examples from `examples/` and attach their source paths. If no example exists for an archetype, record the gap and fall back to `alternate-approach` as nearest-neighbor.
4. **Feasibility gate** (hard — blocks builder if failed):
  - For each slide, look up the archetype's `capacity` metadata (see §5).
  - Reject if item count exceeds `max_items` (e.g. 5 supports in a family that allows 4).
  - Reject if total word count exceeds `max_words`.
  - Reject if asset hints reference assets that do not resolve.
  - On any rejection: return the failing slides to the planner with the specific violation. The planner re-plans only the failing slides (split, reduce, or change archetype). Re-planning budget: 1 retry.
  - This gate is deterministic and cheap. It prevents the builder from receiving plans it cannot lay out.
5. Attach design system tokens, canvas dims, asset paths, and examples to build the builder input packet.

**Output**: `builder_input.json`

```jsonc
{
  "deck_plan":      { /* passthrough */ },
  "design_system":  { /* passthrough */ },
  "runtime_api":    { /* concise reference doc for runtime symbols */ },
  "examples":       [
    { "archetype": "hero_statement_with_support_columns",
      "example_path": "examples/hero_support_columns_01.py",
      "source_pptx_path": "examples/source/hero_support_columns_01.pptx" }
  ],
  "resolved_assets": { "by_slide": { "operating_principle": [...] } },
  "execution_limits": { "timeout_s": 120, "max_mem_mb": 1024 }
}
```

### 4.4 Phase 4 — Builder (LLM #2)

**Inputs**:

- `builder_input.json`
- Runtime API reference doc (generated from `ppt_runtime` docstrings)
- Selected example source files as few-shot
- Hard prompt rules

**Prompt rules**:

- Import only from `ppt_runtime` and `pptx`. No `os`, `subprocess`, `sys` beyond `sys.argv`.
- Use `tokens.color(...)` and `tokens.type(...)` for every fill, line, and font property. No hex literals. No inline font-size integers.
- Call `measure_text(...)` before committing any text box whose content is not trivially short. If the measurement exceeds the bounding box, call `shrink_to_fit(...)` or reduce content per the planner density budget (not below the `min_size` for that type style).
- Use `grid.span(...)` and canvas-anchor properties for geometry. Inch literals are allowed only inside obvious spacing constants (`Inches(0.1)` for padding); the scanner permits this within a small allowlist.
- Produce all slides in one file. Define shared helpers at the top. Reuse helpers across slides.
- Output file must be named `build_deck.py` and write to `sys.argv[1]`.

**Output**: one `build_deck.py` in the current attempt directory.

**Retry budget**: 3 attempts per build call, with failure reasons folded into the next prompt.

### 4.5 Phase 5 — Sandbox Execution

**Inputs**: the `build_deck.py` from the current attempt.

**Execution**:

1. AST pre-scan: walk the module AST, reject disallowed imports and calls (`__import__`, `eval`, `exec`, `open()` outside allowlisted paths, anything under `os.` except `os.path`).
2. Launch in subprocess with restricted `env`, restricted `cwd` (the attempt dir), RO bind mounts on asset dirs + runtime dir, and `resource.setrlimit` for CPU and memory.
3. Capture stdout, stderr, exit code, and any traceback to `build_exec_report.json`.
4. On success, confirm the expected PPTX path exists and opens with `python-pptx`.
5. On failure, retry up to the builder retry budget.

**Output**: `build_attempts/attempt_NN/build_deck.py`, `build_attempts/attempt_NN/build_exec_report.json`, and `build_attempts/attempt_NN/deck.pptx` on success.

### 4.6 Phase 6 — Deterministic Post-build Scan

**Input**: the latest successful `deck.pptx`.

**Checks**:


| Check                                                   | Method                                   | Severity         |
| ------------------------------------------------------- | ---------------------------------------- | ---------------- |
| Slide count matches `deck_plan`                         | Length compare                           | BLOCKING         |
| No empty slides                                         | `len(shapes) >= 2`                       | BLOCKING         |
| No off-canvas shapes                                    | Shape bbox vs. slide dims                | BLOCKING         |
| No leaked markdown markers                              | Regex scan on text runs                  | BLOCKING         |
| All picture rels resolve                                | Walk `rels` vs. package parts            | BLOCKING         |
| Text frames fit their bounds                            | `measure_text` per run vs. frame         | WARNING → repair |
| No large overlaps between non-background shapes         | AABB intersection with threshold         | WARNING → repair |
| All colors map to `tokens` palette                      | Compare fills/lines/fonts to token hexes | WARNING → repair |
| All fonts are in the substitute allowlist               | Compare run fonts to `font_substitution` | WARNING → repair |
| No raw hex literal patterns in adjacent `build_deck.py` | Static lint on the generated code file   | WARNING          |


**Output**: `geometry_report.json`. Any BLOCKING result triggers the repair build loop immediately. WARNING results are aggregated and passed to the reviewer as context.

The hygiene catalog in `assets/benchmarks/v3_visual_hygiene_checks.xlsx` defines 26 target checks (§10.6). The base scanner only enables checks that are objectively measurable from the PPTX, generated code, or run artifacts without heuristic role inference. Checks that depend on inferred peer groups or inferred title/kicker/body roles stay deferred until explicit anchors or grouping metadata exist. Internal scanner failures are themselves BLOCKING findings; the scanner must never silently pass because a check crashed.

### 4.7 Phase 7 — Review Image Export

Existing `src/review/automation.py` (`soffice + pdftoppm`) path. Unchanged.

**Output**: `review_images/v1/slide_*.png`.

### 4.8 Phase 8 — Multimodal Review (LLM #3)

**Inputs**:

- Rendered slide images
- `deck_plan.json`
- `geometry_report.json` (WARNING-level findings only, BLOCKING never reach here)
- `design_system.json` summary
- Example images for the archetypes used (optional second pass; budget-dependent)

**Output**: `review_feedback.json`

```jsonc
{
  "deck_summary": {
    "overall": 4,
    "weakest_slides": ["operating_principle"],
    "strongest_slides": ["closing_cta"]
  },
  "per_slide": [
    {
      "slide_id": "operating_principle",
      "axes": {
        "contrast":        { "score": 4, "note": "" },
        "alignment":       { "score": 3, "note": "card gutters uneven, right column looks wider" },
        "hierarchy":       { "score": 5, "note": "" },
        "density":         { "score": 2, "note": "body box half empty, hero text too small" },
        "whitespace":      { "score": 4, "note": "" },
        "brand_adherence": { "score": 5, "note": "" },
        "variety_vs_prev": { "score": 4, "note": "" },
        "message_clarity": { "score": 5, "note": "" }
      },
      "repair_hints": [
        "increase hero_text type size by one step, or expand supports body copy to fill vertical space",
        "normalize card gutters to grid gutter_md"
      ],
      "preserve": ["headline", "kicker", "accent strategy"]
    }
  ]
}
```

Any axis score ≤ 2 is a mandatory repair target. Axis ≤ 3 is optional. Scoring is structured, not free-form.

**Reviewer retry budget**: 1 (schema validation only).

### 4.9 Phase 9 — Repair Build

**Trigger**: BLOCKING geometry finding OR any review axis ≤ 2 on any slide.

**Inputs**:

- Prior `build_deck.py` (verbatim)
- `geometry_report.json` (BLOCKING findings if present)
- `review_feedback.json` (if the trigger was aesthetic)
- `builder_input.json` (unchanged)

**Prompt rules**:

- Return a complete replacement `build_deck.py`. Not a patch.
- Keep non-flagged slides byte-close to the prior version. You may touch shared helpers only if the change is strictly additive or the shared helper is what is broken.
- For flagged slides, apply the listed repair hints. Do not invent unrelated changes.
- Preserve all `must_preserve` fields from the original planner output.

**Output**: next attempt directory with new `build_deck.py`, execution report, geometry scan, and (for aesthetic repair) a re-render and re-review.

**Repair budget**: 1 repair loop by default, 2 max. Beyond that, ship the best attempt with a failure report.

**Escalation on repeated failure**: If the same slide fails on the same axis (mechanical or aesthetic) across two consecutive repair attempts, the repair prompt is allowed to change the slide's archetype or split the slide into two. The planner's `must_preserve` fields still hold, but the layout strategy may change. This prevents the repair loop from repeatedly tweaking a layout that fundamentally does not work for the content.

### 4.10 Phase 10 — Quality Gates And Stop

**Gates**:

- Geometry scan has zero BLOCKING findings.
- Review deck overall score ≥ 3.5.
- No per-slide axis scored ≤ 2.
- Slide count matches plan.
- All `must_preserve` fields from planner are still present (fuzzy match on headline strings).
- At least one non-text visual element per content slide (scanner-derived).

**Output**: `quality_gates.json`, `run_summary.json`, `deck.pptx` at the run root.

## 4.11) LLM Integration Mechanics

This section describes the cross-cutting concerns shared by all three LLM call sites (planner, builder, reviewer). Individual phase specs (§4.2, §4.4, §4.8, §4.9) define *what* each call produces; this section defines *how* calls are made, validated, retried, and wired together.

### 4.11.1 Call Sites And Contracts

Three distinct LLM call sites, each with a different input/output contract and model requirement:

| Call Site | Purpose | Input Shape | Output Shape | Model Requirement |
|---|---|---|---|---|
| **Planner** | Content → deck structure | normalized_content + archetype vocab + writing rules | `deck_plan.json` (JSON) | Strong reasoning, JSON mode |
| **Builder** | Plan → executable code | builder_input + runtime API ref + few-shot examples | `build_deck.py` (Python) | Strong code generation |
| **Reviewer** | Images → scored feedback | slide images + plan + geometry report + design system | `review_feedback.json` (JSON) | Multimodal vision, rubric scoring |

All three may use different Azure OpenAI deployments. A planner deployment optimized for reasoning and a builder deployment optimized for code generation are expected.

### 4.11.2 Client Configuration

**V3 uses the Azure OpenAI Responses API exclusively.** The Chat Completions API (`/openai/deployments/<name>/chat/completions`) is not used in V3 code. The V1 client (`src/llm/azure_openai_client.py`) stays for V1 baseline runs; V3 must not import or reuse it.

**Minimum model floor: `gpt-5.2`.** No model older than gpt-5.2 is permitted.

V3 client: `src/v3/llm_client.py` — new module, Responses API via raw HTTP (no SDK dependency).

- Request format: `POST {base_url}/openai/responses?api-version={api_version}` with `model` in the JSON body.
- All three call sites (planner, builder, reviewer) use the same client; they differ only in the model name and prompt.

**Environment variables** (from `.env`):

```
AZURE_OPENAI_ENDPOINT          # Base URL (no path suffix)
AZURE_OPENAI_API_KEY           # API key
AZURE_OPENAI_API_VERSION       # Responses API version (2025-04-01-preview)
```

V3 model assignments (all configurable via `.env`):

```
V3_PLANNER_MODEL=gpt-5.4       # JSON slide-plan output
V3_BUILDER_MODEL=gpt-5.3-codex # Python code generation (code-specialized)
V3_REVIEWER_MODEL=gpt-5.4      # Multimodal vision + JSON scoring
```

If a per-site model is not set, `gpt-5.4` is the default.

### 4.11.3 Prompt Assembly

Each caller assembles a prompt from three layers:

1. **System prompt** — static per caller, defines role, rules, and output schema. Checked into the repo as a text file or inline constant.
2. **User message** — assembled from the structured inputs of that pipeline stage.
3. **Few-shot examples** (builder only) — selected example source files injected as context in the user message.

**Planner system prompt** includes:
- Role definition: "You are a presentation planner..."
- Archetype vocabulary table with capacity metadata (§5)
- `presentation-writing.skill` rules as hard constraints (kill-on-sight lexicon, per-slide checklist)
- `deck_plan.json` schema definition with field-level descriptions
- Forbidden field names: no field containing `left`, `top`, `width`, `height`, `x`, `y`, `emu`, `inch`, `hex`, `rgb`, `size_pt`
- `purpose` and `audience_takeaway` requirements

**Planner user message** includes:
- Normalized content from Phase 1
- Slide-count hint and density preference (if provided)
- Available example archetype labels

**Builder system prompt** includes:
- Role definition: "You are a Python code generator..."
- `ppt_runtime` API reference (generated from module docstrings at build time)
- Prompt rules from §4.4: token-only colors/fonts, grid-only geometry, measure before commit
- Output format: complete `build_deck.py` that writes to `sys.argv[1]`
- Import rules: only `ppt_runtime.*` and `pptx.*`

**Builder user message** includes:
- `deck_plan.json` (full planner output)
- `design_system.json` (summary: type scale, spacing scale, color tokens, canvas defs)
- Selected example source code (1-3 examples, budget-capped)
- Resolved asset paths per slide
- On retry: prior `build_deck.py` + failure reason (traceback or scanner findings)

**Reviewer system prompt** includes:
- Role definition: "You are a presentation reviewer..."
- 8-axis rubric with score-level descriptions (1-5 per axis)
- `review_feedback.json` schema definition
- `purpose` and `audience_takeaway` from the plan (reviewer checks whether the build achieved the stated intent)
- Instruction to produce `repair_hints` for any axis ≤ 3, mandatory repair for axis ≤ 2

**Reviewer user message** includes:
- Rendered slide images (base64)
- `deck_plan.json` (for context on intent)
- `geometry_report.json` WARNING-level findings (BLOCKING never reaches reviewer)
- `design_system.json` summary

### 4.11.4 Response Parsing And Validation

**Planner and Reviewer** (JSON output):
1. Parse LLM response body as JSON (`json.loads`)
2. Validate against the caller's JSON Schema (using `src/contracts/validator.py`)
3. Apply caller-specific semantic checks (e.g., planner: archetypes ∈ vocabulary, no geometry fields; reviewer: all flagged slides have repair_hints)
4. On parse or schema failure → retry with the specific error messages folded into the next prompt
5. On success → persist as the stage artifact

**Builder** (Python code output):
1. Extract code from the LLM response (strip markdown fences if present)
2. Parse as Python AST (syntax check)
3. Run AST pre-scan (import/call allowlist per §2.5)
4. Execute in sandbox (§4.5)
5. Run post-build scanner on output PPTX (§4.6)
6. On any failure → retry with the failure context

The builder's validation is multi-stage: syntax → safety → execution → output quality. Each stage produces a distinct error type that feeds the retry prompt differently.

### 4.11.5 Retry Strategy

| Caller | Total budget | Retry trigger | What goes into the retry prompt |
|---|---|---|---|
| Planner | 2 retries | JSON parse or schema failure | Specific validation errors |
| Planner (re-plan) | 1 retry | Feasibility gate rejection | Failing slides + capacity violations |
| Builder | 3 total attempts | Syntax error, AST rejection, execution failure, or scanner BLOCKING | Traceback, scanner findings, or AST errors |
| Reviewer | 1 retry | JSON parse or schema failure | Specific validation errors |
| Repair builder | 1-2 iterations | Scanner BLOCKING or reviewer axis ≤ 2 | Prior `build_deck.py` verbatim + findings/hints |

**Critical rule**: every retry includes the prior failure context. The LLM never retries blind.

### 4.11.6 Error Propagation

Errors fall into three classes with different handling:

1. **Infrastructure errors** (auth failure, network timeout, rate limit) → fail fast, no retry, structured error in `run_log.jsonl`, run aborts with `RUN_FAILED_BUILD`
2. **Schema/validation errors** (bad JSON, missing fields, forbidden geometry fields) → retry with error context up to the caller's retry budget
3. **Persistent LLM failures** (retry budget exhausted) → abort run, persist the best attempt if one exists, record failure reason in `run_summary.json`

Every error is logged as a stage marker in `run_log.jsonl`. The pipeline never silently swallows an LLM failure.

### 4.11.7 Token Budget And Cost Tracking

- Every LLM call returns token counts via `LLMUsage` (prompt_tokens, completion_tokens)
- Counts are recorded per call and aggregated per run in the metrics ledger (§10.8)
- Builder prompt is the largest: deck_plan (~1-2K tokens) + design_system (~1K) + runtime API ref (~2-3K) + examples (~2-5K each, capped at 3) = ~8-18K input tokens
- Example injection is budget-capped: at most 3 example source files per run, regardless of archetype count. Prefer one example per unique archetype over multiple examples of the same archetype (§6.6)
- If a prompt exceeds the model's context window, the caller fails with a structured error. No silent truncation.

### 4.11.8 Feedback Loops

Four feedback paths carry information backward through the pipeline:

```
Feasibility gate ──(capacity violations)──→ Planner (re-plan failing slides only)
Scanner ──────────(BLOCKING findings)──────→ Repair builder (mechanical fix)
Content fidelity ─(dropped/hallucinated)──→ Repair builder (content fix)
Reviewer ─────────(axis scores + hints)───→ Repair builder (aesthetic fix)
```

Each feedback path includes:
- The **prior output verbatim** (prior `deck_plan.json` or prior `build_deck.py`)
- The **specific findings** that triggered the feedback (not a summary — the actual structured data)
- The **preserve list** (what must not change)

The repair builder receives all applicable feedback in a single prompt. If both scanner and reviewer findings exist, they are combined. The repair builder does not see intermediate discussion — only the prior code, the findings, and the preserve constraints.

### 4.11.9 V3 LLM Client

V3 has its own LLM client (`src/v3/llm_client.py`), built against the Responses API. It does **not** reuse or extend the V1 client.

Core methods:

- **`generate_json(model, instructions, input, ...)`** — sets `text.format.type = "json_object"`. Returns parsed dict. Used by planner and reviewer.
- **`generate_code(model, instructions, input, ...)`** — plain text output. Returns raw string. Used by builder.
- **`generate_json_with_images(model, instructions, input, images, ...)`** — multimodal input (vision). Returns parsed dict. Used by reviewer.

Supporting infrastructure:

- **Structured retry wrapper** — `src/v3/llm_retry.py` wraps any client call with retry logic: parse → validate → retry-with-context. Callers pass a validator function; the wrapper handles the retry loop.
- **Model routing** — each caller specifies its model via `V3_PLANNER_MODEL`, `V3_BUILDER_MODEL`, `V3_REVIEWER_MODEL` env vars. Default is `gpt-5.4`.

**Hard constraints**: Responses API only. Minimum model gpt-5.2. No fallback to Chat Completions. See `AGENTS.md` Rule 9.

### 4.11.10 LLM Cost Logger

Cost logging is **opt-in**: pass a `CostLogger` instance to `ResponsesClient` to enable. When `cost_logger` is `None` (the default), no CSV is written.

When enabled, every API call is appended to `runs/llm_cost_log.csv`. The logger (`src/v3/cost_logger.py`) is append-only, uses `fcntl` advisory locking for concurrent-writer safety, and never blocks the pipeline — `OSError` during writes is suppressed (programmer bugs propagate normally).

Each public client method accepts a `caller` parameter (e.g., `"planner"`, `"builder"`, `"reviewer"`) so cost rows attribute usage to a pipeline stage. The planner already threads `caller="planner"`.

**CSV columns**: timestamp, date, model, method, caller, input_tokens, output_tokens, total_tokens, input_cost_usd, output_cost_usd, total_cost_usd, response_id, prompt_preview.

**Pricing**: reads per-model env vars (`V3_COST_{MODEL_SLUG}_INPUT`, `V3_COST_{MODEL_SLUG}_OUTPUT`) or falls back to global `AZURE_OPENAI_INPUT_USD_PER_MILLION` / `AZURE_OPENAI_OUTPUT_USD_PER_MILLION`. When unset, costs are $0 but tokens are still recorded.

**Summary CLI**: `python scripts/llm_cost_summary.py` reads the CSV and prints rollups by model, caller, day, week, and month. Read and summary paths tolerate malformed/truncated rows without crashing.

## 5) Archetype Vocabulary

Planner output archetypes are drawn from a fixed vocabulary. Each archetype carries capacity metadata used by the feasibility gate (§4.3 step 4). Initial set (to be expanded as the example library grows):


| Archetype                             | Intent                                                        | max_items           | max_words | canvas_pref    |
| ------------------------------------- | ------------------------------------------------------------- | ------------------- | --------- | -------------- |
| `hero_title`                          | Deck cover with headline, optional subhead, optional backdrop | 2                   | 30        | `header_dark`  |
| `section_break`                       | Divider slide between deck sections                           | 2                   | 20        | `header_dark`  |
| `hero_statement_with_support_columns` | One dominant statement + 2-4 supporting columns               | 4 supports          | 85        | `header_light` |
| `three_cards`                         | Three parallel concepts with title + body                     | 3 cards             | 90        | `blank`        |
| `comparison_split`                    | Two-sided before/after, us/them, problem/solution             | 2 sides, 4 pts/side | 80        | `blank`        |
| `kpi_grid`                            | Grid of 4-6 large metrics with labels                         | 6 metrics           | 60        | `blank`        |
| `stat_list_with_icons`                | Vertical list of stats with an icon per row                   | 5 rows              | 75        | `header_light` |
| `process_flow`                        | Linear or staged process with 3-6 steps                       | 6 steps             | 90        | `blank`        |
| `quote_callout`                       | Single large quotation with attribution                       | 1 quote             | 50        | `header_dark`  |
| `content_with_visual`                 | Text on one side, image or diagram on the other               | 1 text + 1 visual   | 60        | `blank`        |
| `closing_cta`                         | Call-to-action closer with next steps                         | 3 items             | 50        | `header_light` |
| `matrix_grid`                         | Labeled rows x labeled columns of content cells               | 4 rows x 3 cols     | 150       | `blank`        |
| `timeline_roadmap`                    | Phased timeline with milestones and durations                 | 5 phases            | 100       | `blank`        |


Capacity values are initial estimates refined during example seeding (SLICE-007). `canvas_pref` is the default; the planner may override with justification.

The following archetypes are **candidates** — observed in designer reference slides but not yet confirmed. They will be added to the active vocabulary only if example decomposition during SLICE-007 confirms they are distinct from existing archetypes:

- `persona_use_case` — persona image + story + data flow (observed in designer slides)
- `feature_columns` — multi-column feature list with category headers (observed in designer slides)
- `services_overview` — multi-section: stats banner + pillars + value props (observed in designer slides, may be too complex for a single archetype)

Rules:

- Archetype names are planner-visible labels, not implementation names.
- Every archetype carries `capacity` metadata: `max_items`, `max_words`, and `canvas_pref`. The feasibility gate (§4.3) checks these before the builder runs.
- Every archetype must be populated by at least one validated example before the planner is allowed to select it. "Populated" means a working `examples/<label>_NN.py` that runs and produces a structurally-faithful reproduction of a designer source.
- New archetypes are added only when a decomposed example shows an existing label cannot describe it cleanly.
- Renamed: `content_with_diagram` → `content_with_visual` to reflect that the visual side may be an image, icon cluster, or simple diagram, not only a complex diagram.

## 6) Example Library

### 6.1 What an example is

An example is a hand-validated decomposition of one designer-made slide (or one slide from a designer-made deck) into runtime code. It lives at `examples/<archetype>_<slug>.py` and is accompanied by the source PPTX at `examples/source/<archetype>_<slug>.pptx`.

### 6.2 Decomposition procedure

1. Open the designer PPTX and extract per-shape data with `python-pptx` (position, size, fill, line, text, font).
2. Identify the archetype label.
3. Identify the grid the slide lives on (derive column count, gutter, margins).
4. Rewrite the slide as `ppt_runtime`-backed Python code. Every coordinate must come from grid spans or canvas anchors; every color must come from tokens; every font size must come from `type_scale`.
5. Execute the decomposition, export the result as an image, and visually diff against the designer source. Iterate until drift is within an acceptable structural threshold (positions within one grid unit, type sizes within one step, colors exact).
6. If the runtime cannot express a shape or pattern, stop and either add the primitive to the runtime or mark the slide out-of-scope and remove it from the library.

### 6.3 Metadata

Each example ships with `examples/<archetype>_<slug>.json`:

```jsonc
{
  "archetype": "hero_statement_with_support_columns",
  "source_pptx": "examples/source/hero_support_columns_01.pptx",
  "runtime_file": "examples/hero_support_columns_01.py",
  "designer": "<source credit>",
  "intent": "Lead with a thesis; support with three contrasting columns.",
  "invariants": [
    "hero statement is the largest element on the slide",
    "supports share equal width and vertical baseline",
    "exactly one accent color is used for emphasis"
  ],
  "variables": [
    "hero text length (20-180 chars)",
    "number of supports (2-4)",
    "support label casing"
  ]
}
```

`invariants` and `variables` are hand-written. They are what make the example teachable — they tell the builder what to copy and what to adapt. Without them, few-shot is pure mimicry.

### 6.4 Designer slide source material

Designer reference slides received `2026-04-14` at `assets/ground_truth/internal_inbox/designer_reference_slides.pptx` (21 slides). After filtering:

**Ascendion-branded slides (direct decomposition sources)**:

- S01: Hero title with background visual — maps to `hero_title`
- S02: Numbered infographic overlay — may map to `process_flow` variant or new archetype
- S06: Solution flow with connectors (22 shapes) — maps to `content_with_visual`, complex

**Excluded**:

- S03, S04: Full-bleed visuals, no extractable text — limited decomposition value
- S10, S16, S19: Architecture diagrams — deferred to B1
- S11-S13: Duplicates (identical slides)
- S05, S07-S09, S14-S15, S17-S18, S20-S21: Collabera Digital branded — not direct sources

**Layout patterns to reimplement on Ascendion template** (from non-Ascendion slides):

- S14 pattern: 4x3 matrix grid with labeled rows and column headers → `matrix_grid`
- S21 pattern: Phased timeline with duration badges → `timeline_roadmap`
- S09 pattern: Two-phase horizontal approach → `process_flow`
- S18 pattern: Multi-column feature list with priority badges → `feature_columns` candidate
- S07 pattern: Two-column concept cards with icons → `comparison_split`

These patterns are decomposed for layout structure only. Colors, fonts, and spacing are replaced with Ascendion design system tokens during reimplementation.

### 6.5 Library growth policy

- Initial seed: Ascendion designer slides (S01, S02, S06) + layout patterns reimplemented from non-Ascendion sources + `alternate-approach/build.py` rewritten on the runtime.
- Coverage target before SLICE-011: at least one example per archetype the planner is allowed to select.
- Coverage target before SLICE-014: 2-3 examples per archetype, varying on the listed variables, so the builder learns invariants across the variation.
- Examples that stop being useful (e.g., template changes, archetype renamed) are removed, not left to rot.

### 6.6 Example selection during a run

`src/compose/examples.py` (new) receives the planner's archetype list and returns the top examples per archetype (by tag match, then by recency). Budget cap: at most 3 examples in the builder prompt for any one run, regardless of archetype count. If the budget is exceeded, prefer one example per unique archetype over multiple examples of the same archetype.

## 7) Runtime Library

### 7.1 Module layout

```
src/ppt_runtime/
  __init__.py         # public API re-exports
  canvas.py           # load_template, pick_canvas, Canvas
  grid.py             # Grid, Rect, span math
  tokens.py           # Tokens, color, type, spacing
  measure.py          # measure_text, shrink_to_fit
  shapes.py           # add_rect, add_text, add_image, add_line, add_connector
  patterns.py         # shape-level: draw_card, draw_stat_block, draw_kicker, draw_header_bar
  composers.py        # section-level: compose_card_row, compose_stat_grid, compose_split_columns, compose_timeline
  errors.py
```

### 7.2 Public API (shapes and rules)

```python
# canvas
canvas = load_template(path)
slide  = canvas.add_slide(canvas_name="header_light")
canvas.body_left   # EMU, derived from design_system
canvas.body_top
canvas.body_width
canvas.body_height
canvas.save(output_path)

# grid
g = Grid(canvas, cols=12, gutter="md")
rect = g.span(col=1, col_span=4, top=canvas.body_top, height_emu=...)
row  = g.row(top=..., height_emu=..., items=[(col_span, name), ...])  # returns dict name→Rect

# tokens
tokens = Tokens.from_design_system("assets/template/design_system.json")
tokens.color("accent_1")      # returns RGBColor
tokens.type("title")          # returns dict {font, size_pt, bold, line}
tokens.spacing("md")          # returns EMU

# measurement
w_emu, h_emu = measure_text("Legacy complexity", tokens.type("title"), max_width_emu=...)
fit_type = shrink_to_fit("Legacy complexity", rect, base="title", min="body")

# shapes
add_text(slide, rect, "Legacy complexity", type_style=tokens.type("title"),
         color=tokens.color("text_primary"), align="left")
add_rect(slide, rect, fill=tokens.color("accent_1"), line=None)
add_image(slide, rect, path="assets/icons/png/...")

# patterns (shape-level, opinionated)
draw_card(slide, rect, title="...", body="...",
          accent=tokens.color("accent_1"), padding=tokens.spacing("md"))
draw_header_bar(slide, kicker="01 | The thesis", title="Legacy complexity is now a growth constraint")

# composers (section-level — lay out multi-shape sections)
compose_card_row(slide, region, items=[{"title": "...", "body": "..."}],
                 accent=tokens.color("accent_1"), gutter="md")       # N equal-width cards
compose_stat_grid(slide, region, metrics=[{"value": "42%", "label": "..."}],
                  cols=3)                                             # metric grid
compose_split_columns(slide, region, left_content, right_content,
                      split=0.5)                                     # two-panel layout
compose_timeline(slide, region, phases=[{"label": "...", "body": "..."}],
                 accent=tokens.color("accent_1"))                    # horizontal timeline
```

Section composers own the internal layout of a region (card gutters, metric sizing, column splits). The builder calls them with content and a bounding `Rect`; the composer handles subdivision. This sits between shape-level helpers (draw one thing) and hypothetical future full-slide family functions. The builder still owns slide-level composition — choosing which sections go where on the canvas.

### 7.3 Validation gate for runtime changes

Any change to the runtime must pass the full example library — every `examples/*.py` must still execute and still produce structurally-faithful output against its source. Breaking changes require bumping a runtime version and rerunning the validation.

### 7.4 Escape hatch

The builder may `from pptx import ...` and `from pptx.util import ...` directly for shapes the runtime doesn't cover (rotated text, custom connectors, charts, tables). The AST scanner permits `pptx.*` imports. The post-build scanner still enforces palette and font rules on the resulting shapes.

## 8) Contracts And Artifacts

Per run, under `runs/<run_id>/`:

```
normalized_content.json
deck_plan.json                            # planner output
builder_input.json                        # plan + design system + examples + assets
build_attempts/
  attempt_01/
    build_deck.py
    build_exec_report.json
    deck.pptx                             # on success
  attempt_02/
    ...
deck.pptx                                 # latest successful build (copy)
geometry_report_v1.json
review_images/v1/slide_*.png
review_feedback_v1.json
build_attempts/
  repair_attempt_01/
    build_deck.py
    build_exec_report.json
    deck.pptx
geometry_report_v2.json
review_images/v2/slide_*.png
review_feedback_v2.json
quality_gates.json
run_summary.json
run_log.jsonl
```

The accepted `deck.pptx` at the run root is a copy of the attempt that passed all gates.

## 9) Logging Contract

`run_log.jsonl` stage markers:

- `NORMALIZE_DONE`
- `PLANNER_DONE`
- `ENRICHMENT_DONE`
- `BUILD_ATTEMPT_STARTED`
- `BUILD_ATTEMPT_FAILED`
- `BUILD_EXEC_DONE`
- `GEOMETRY_SCAN_DONE`
- `GEOMETRY_BLOCKING_FAILURE`
- `REVIEW_IMAGES_READY`
- `REVIEW_DONE`
- `REPAIR_BUILD_TRIGGERED`
- `REPAIR_BUILD_DONE`
- `QUALITY_GATES_PASS`
- `QUALITY_GATES_FAIL`
- `RUN_COMPLETE`
- `RUN_FAILED_BUILD`
- `RUN_FAILED_QUALITY_GATES`

## 10) Testing Strategy

The implemented pipeline is broader than three LLM passes. The full test surface is:

`Normalize → Planner → Feasibility Gate → Pre-build Enrichment / Asset Resolution → Builder → Sandbox → Scanner → Content Fidelity → Review Image Export → Reviewer → Repair Loop`

**Key rules**:

- **Objective checks belong in the deterministic layer.** If a condition can be computed from the PPTX, generated code, or run artifacts, it is scanner-owned or contract-owned, not human-scored.
- **Human evaluation is for taste, narrative, and fitness-for-purpose.** It does not duplicate scanner-owned checks like overflow, palette drift, or slide count.
- **Every blocking signal must feed an action.** No metric or report exists without a defined remediation path.
- **Release thresholds are calibrated, not guessed.** Workbook averages and warning counts are not release gates until anchored against real outputs and reviewer behavior.
- **Cutover decisions use paired comparison.** V3 must be judged against V1 on the same prompts, not only against an absolute score.

Test categories: unit (§10.1), integration (§10.2), example regression (§10.3), stage contracts (§10.4), content fidelity (§10.5), visual hygiene (§10.6), benchmark (§10.7), run metrics (§10.8). Execution tiers and pass criteria in §10.9–§10.10.

### 10.1 Unit Tests

**Scope**: individual functions and modules in isolation.
**Speed**: milliseconds each.
**When to run**: every code change, CI.


| Module / area                        | What to test                                                                                                                                                            |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/normalize/parser.py`            | Combined markdown parsing, cue extraction, malformed cue JSON, missing sections, stable section IDs                                                                     |
| `src/v3/planner.py`                  | Planner output schema, archetype vocabulary membership, required fields, rejection of geometry-bearing fields                                                           |
| `src/v3/feasibility.py`              | Capacity math, pass/fail boundary cases, per-archetype limits, slide-splitting / re-plan triggers                                                                       |
| `src/v3/enrichment.py` or equivalent | Asset resolution, unresolved asset handling, example selection, active-archetype/example coverage                                                                       |
| `ppt_runtime/grid.py`                | Grid math: `span()`, gutter handling, edge alignment                                                                                                                    |
| `ppt_runtime/tokens.py`              | Token lookup by name, fallback behavior, RGB conversion                                                                                                                 |
| `ppt_runtime/canvas.py`              | Named anchor positions, safe-area math, canvas selection                                                                                                                |
| `ppt_runtime/measure.py`             | `measure_text` against known strings at known sizes; `shrink_to_fit` behavior near boundaries                                                                           |
| `ppt_runtime/shapes.py`              | `add_rect`, `add_text`, `add_image`, `add_line`, `add_connector` produce expected native PPTX objects                                                                   |
| `ppt_runtime/patterns.py`            | `draw_card`, `draw_header_bar`, `draw_kicker`, `draw_stat_block` obey bounding boxes and token rules                                                                    |
| `src/scan/scanner.py`                | Every objective hygiene check against injected-defect fixture decks; severity classification; report schema                                                             |
| `src/scan/content_fidelity.py`       | Fact extraction, visible-vs-notes coverage scoring, dropped-fact detection, hallucinated-specific detection, placeholder detection                                      |
| `src/review/automation.py`           | Review image export success and failure modes (`soffice`, `pdftoppm`, missing binaries, empty exports)                                                                  |
| `src/contracts/*.json`               | Known-good payloads validate; known-bad payloads fail with actionable errors                                                                                            |
| `src/sandbox/`                       | AST pre-scan rejects disallowed imports/calls, accepts valid `ppt_runtime.`* and `pptx.*` imports, timeout enforcement, memory cap enforcement, write-path restrictions |
| Run artifact / logging utilities     | Required artifact presence, stage marker completeness, failure-path artifact persistence                                                                                |


### 10.2 Integration Tests

**Scope**: multi-stage pipeline segments.
**Speed**: seconds to minutes. Mock LLM calls in CI; run live locally for canary validation.
**When to run**: before merging any pipeline-stage change.


| Test                             | Stages exercised                                   | What to verify                                                                                         |
| -------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Normalize + cues happy path      | Normalize → Planner                                | Content sections and optional cues survive normalization without loss                                  |
| Cue / asset resolution failure   | Plan → Enrichment                                  | Bad icon/image hints fail early with structured error; no builder call                                 |
| Single-slide happy path          | Plan → feasibility → build → sandbox → scan → PPTX | Output PPTX exists, opens, passes scanner, artifact set complete                                       |
| Multi-slide happy path           | Same, with a 5-slide prompt                        | All slides present; deck-level style invariants hold; artifact set complete                            |
| Feasibility gate near-limit pass | Plan → feasibility                                 | A slide at the documented capacity limit passes                                                        |
| Feasibility gate rejection       | Plan → feasibility                                 | Overstuffed content is rejected; only failing slides are returned for re-plan                          |
| Sandbox failure handling         | Build → sandbox                                    | Timeout, import rejection, and write-path violations produce structured failure artifacts              |
| Review image export smoke        | Sandbox success → review export                    | Slide images are produced, named correctly, and match slide count                                      |
| Scanner triggers repair          | Plan → build → scan → repair → scan                | Repair attempt produced; targeted mechanical defect removed                                            |
| Content fidelity triggers repair | Plan → build → fidelity → repair                   | Dropped facts flow into repair inputs; repaired deck restores missing visible facts                    |
| Reviewer triggers repair         | Full pipeline                                      | Reviewer flags targeted slides; second pass improves targeted axes without regressing preserved slides |
| Repair preserve-list enforcement | Full repair path                                   | Non-flagged slides remain byte-close or invariant-close; `must_preserve` fields retained               |
| Editability probe                | Build → sandbox → manual or scripted edit pass     | Standard edits (title expansion, metric replacement, bullet addition) preserve usability               |
| Artifact completeness            | Full pipeline, success and failure paths           | Required artifacts and `run_log.jsonl` stage markers exist for every attempt                           |
| Contract violation handling      | Each stage with malformed handoff payload          | Pipeline halts with structured error; downstream stage does not execute                                |


### 10.3 Example Regression Suite

**Scope**: every example file in `examples/`.
**Speed**: seconds per example (no LLM — direct runtime execution).
**When to run**: after any change to `ppt_runtime/`.

**Method**:

1. Execute every `examples/<archetype>/<name>/build.py` against the current runtime.
2. Verify each produces a valid PPTX that passes the full objective scanner.
3. Verify each example satisfies its own metadata-defined invariants and role-level expectations.
4. Verify each example remains within its declared density / variable bounds.

**Pass criteria**: zero failures. Any regression blocks the runtime change.

**Not used as a primary assertion**: raw shape count equality, cosmetic snapshot diffs by default.

**Optional future extension**: store lightweight structural snapshots only where invariant checks prove insufficient.

### 10.4 Stage Contract Validators

**Scope**: structural correctness of data flowing between pipeline stages.
**Speed**: sub-second.
**When to run**: automatically on every pipeline execution, at every handoff point.


| Handoff                       | Contract checks                                                                                                                                                                         |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Normalize → Planner           | `normalized_content.json` passes schema; cue JSON parsed; section IDs stable; no empty content payload                                                                                  |
| Planner → Feasibility gate    | Every slide has `archetype`, `purpose`, `audience_takeaway`, `must_preserve`; no geometry-bearing fields; archetype ∈ active vocabulary                                                 |
| Feasibility gate → Builder    | All failing slides resolved or explicitly re-planned; resolved assets exist; all referenced archetypes have validated examples                                                          |
| Builder → Sandbox             | `build_deck.py` passes AST pre-scan; imports only `ppt_runtime.`* and `pptx.*`; no disallowed stdlib/network imports; no raw hex outside allowlist; writes only to expected output path |
| Sandbox → Scanner             | Output file exists, is valid PPTX, slide count matches plan, execution report complete                                                                                                  |
| Scanner / Fidelity → Reviewer | `geometry_report.json` and `content_fidelity_report.json` pass schema; zero BLOCKING scanner findings before reviewer runs                                                              |
| Reviewer → Repair             | `review_feedback.json` passes schema; all flagged slides have scored axes, `repair_hints`, and `preserve` fields                                                                        |
| Repair → Accept               | `must_preserve` fields retained; unchanged slides pass preserve checks; required attempt artifacts exist                                                                                |


**Implementation**: JSON Schema files plus explicit AST / artifact validators in `src/contracts/`. Failure halts the pipeline with a structured error naming the contract, violation, and failing value.

### 10.5 Automated Content Fidelity Check

**Scope**: does the output PPTX preserve the user's intended content in visible slide content, not just speaker notes?
**Speed**: seconds.
**When to run**: every pipeline execution, after scanner, before reviewer.

**Method**:

1. Extract visible text from slide shapes.
2. Extract notes text separately.
3. Extract key facts from the user input: named entities, numbers, percentages, dates, proper nouns, quoted phrases.
4. Match facts against visible slide text first.
5. Record facts that appear only in notes.
6. Flag hallucinated specifics: numbers, client names, quotes, or case-study claims not present in the user input or approved asset/catalog sources.

**Output**: `content_fidelity_report.json`:

```jsonc
{
  "visible_coverage_score": 0.88,
  "notes_only_fact_count": 1,
  "total_facts": 12,
  "matched_visible_facts": 10,
  "matched_notes_only_facts": ["Q3 revenue grew 14%"],
  "dropped_facts": ["Q3 revenue grew 14%"],
  "hallucinated_specifics": [],
  "placeholder_leaks": [],
  "markdown_leaks": []
}
```

**Rules**:

- Facts present only in speaker notes do **not** count as visible coverage.
- Placeholder leaks and markdown leaks are always BLOCKING.
- Any hallucinated specific number, client, quote, or case-study claim is BLOCKING.
- Visible coverage thresholds must be calibrated on an anchor set before they become hard release gates. Until calibrated, low visible coverage is a repair-required signal, not a silent pass.

**Repair path**: `dropped_facts` and `hallucinated_specifics` are passed into the repair prompt as explicit targets.

### 10.6 Visual Hygiene Checks

**Scope**: objective correctness of the output PPTX.
**Speed**: seconds.
**When to run**: every pipeline execution.

26 binary pass/fail target checks across 6 categories. Full definitions live in `assets/benchmarks/v3_visual_hygiene_checks.xlsx`.

**Ownership rule**: if a check is objectively measurable from the PPTX, code, or exported artifacts, it belongs in the deterministic scanner. The benchmark rubric does **not** re-score objective mechanical checks.

**Active scanner set (current)**: 21 objective checks are enabled in the base scanner. The remaining 5 checks are part of the hygiene catalog but deferred until they can be grounded on explicit metadata instead of inference.


| Category          | Check IDs            | Owner / Status                                          |
| ----------------- | -------------------- | ------------------------------------------------------- |
| Color             | VH-01 – VH-05        | Scanner                                                 |
| Typography        | VH-06 – VH-09        | Scanner                                                 |
| Spatial           | VH-10 – VH-13, VH-15 | Scanner                                                 |
| Spatial           | VH-14                | Deferred pending explicit peer-group metadata           |
| Content Rendering | VH-16 – VH-19        | Scanner                                                 |
| Cross-Slide       | VH-20 – VH-23        | Deferred pending explicit title / kicker / body anchors |
| Structural        | VH-24 – VH-26        | Scanner                                                 |


**Severity**: per-check, as defined in the hygiene catalog.

**Grounding rule**: active checks may use template metadata such as layout-index-to-canvas mappings and `body_region` bounds. They may not infer semantic roles or peer-group relationships from raw PPTX geometry alone and then treat those inferences as deterministic truth.

**Deck-level pass**: zero BLOCKING failures. This includes internal scanner failures, which are surfaced as synthetic BLOCKING findings rather than being swallowed. WARNINGs are triaged by class; there is **no fixed global warning budget**.

**Action rule for WARNINGs**: any warning class that repeats on release-gate prompts must be either fixed, explicitly accepted with rationale, or promoted to BLOCKING in the next scanner revision.

### 10.7 Benchmark Evaluation

**Scope**: end-to-end output quality on realistic prompts.
**Speed**: slow (human scoring). Hours per full run.
**When to run**: canary benchmark after first end-to-end build; full paired benchmark before cutover and after major changes.

26 test prompts in `assets/benchmarks/v3_test_prompts.xlsx` (generated by `scripts/generate_benchmark_xlsx.py`). The full corpus currently contains 26 prompts, but not every prompt is a release gate.

**Prompt classes**:

- **Release-gate prompts**: only prompts aligned to the current active archetype vocabulary in §5.
- **Forward-coverage prompts**: prompts for future / inactive labels or known-vocabulary gaps.
- **Stress prompts**: intentionally under-specified prompts such as TP-25 and TP-26; diagnostic only, never cutover gates.

**Artifact requirements**: the benchmark workbook must carry a prompt classification (`release_gate`, `forward_coverage`, `stress`), support paired V1/V3 scoring with an explicit pairwise winner field, and be regenerated if the active archetype vocabulary changes.

**Prompt sections**:


| Section                 | Tests         | What it exercises                                        |
| ----------------------- | ------------- | -------------------------------------------------------- |
| Core archetypes         | TP-01 – TP-10 | One prompt per active archetype, mid-density             |
| Untested archetypes     | TP-11 – TP-13 | `quote_callout`, `section_break`, `stat_list_with_icons` |
| Edge cases              | TP-14 – TP-16 | Sparse content, capacity overflow, ambiguous archetype   |
| Audience variations     | TP-17 – TP-18 | Board-level vs. technical team                           |
| Content type variations | TP-19 – TP-20 | Narrative case study, sales persuasion                   |
| Deck-level              | TP-21 – TP-24 | Multi-slide decks (5-8 slides)                           |
| Stress tests            | TP-25 – TP-26 | Minimal prompt, content dump                             |


**Benchmark axes** (8 total — 6 base + 2 multi-slide-only):


| Axis                    | Scope            |
| ----------------------- | ---------------- |
| Content Fidelity        | All              |
| Archetype Selection     | All              |
| Visual Hierarchy        | All              |
| Density & Readability   | All              |
| Brand Consistency       | All              |
| Editability             | All              |
| Cross-Slide Consistency | Multi-slide only |
| Narrative Flow          | Multi-slide only |


**Removed from benchmark rubric**: Mechanical Defects — this is scanner-owned and recorded from scanner output, not re-scored by a human.

**Editability protocol**: for benchmark decks, apply three standard edits to representative slides: (1) extend a title by ~20%, (2) replace one metric/value, (3) add one bullet or support item where the archetype allows it. Score editability based on whether the deck remains usable after those edits.

**Calibration step**: before any numeric benchmark threshold becomes a release gate, run a 10-prompt anchor set through both V1 and V3 and lock pass/fail score bands, reviewer instructions, and pairwise winner logic. Until calibration is complete, workbook averages are diagnostic only.

**Cutover rule**: release decisions use the **release-gate subset only**. V3 must beat V1 on a majority of paired release-gate prompts. Every active archetype must be represented by at least one passing release-gate prompt. No catastrophic failures on release-gate prompts.

**Catastrophic failure**: scanner BLOCKING finding, hallucinated specific content, editability failure, or any benchmark axis scored `1`.

**Stress / forward-coverage prompts**: reported separately; do not block cutover; failures become backlog inputs, scanner fixtures, or future benchmark candidates.

Full axis definitions with score-level descriptions are in `assets/benchmarks/v3_test_prompts.xlsx` Sheet 3 ("Axis Definitions").

### 10.8 Run Metrics Ledger

**Scope**: operational telemetry for every pipeline run.
**Speed**: near-zero overhead (single CSV append at pipeline end).
**When to run**: every pipeline execution, automatically.

**Fields** (appended to `runs/metrics_ledger.csv`):

```
run_id, timestamp, prompt_hash, slide_count, active_archetypes,
planner_tokens_in, planner_tokens_out,
builder_tokens_in, builder_tokens_out,
reviewer_tokens_in, reviewer_tokens_out,
build_attempts, repair_rounds,
scanner_blocking_count, scanner_warning_count, warning_classes,
visible_content_fidelity_score, notes_only_fact_count,
reviewer_avg_score, reviewer_min_axis,
review_export_success, artifact_completeness,
total_latency_sec, outcome, primary_failure_reason
```

**Key metrics to track over time**:


| Metric                           | What it tells you                  | Threshold                                  | Required action                                                             |
| -------------------------------- | ---------------------------------- | ------------------------------------------ | --------------------------------------------------------------------------- |
| First-pass build success rate    | Builder prompt / runtime quality   | Falling trend over rolling 10 runs         | Inspect failing attempts; add regression fixture if pattern repeats         |
| Repair frequency                 | First-pass quality                 | Repeated increase over rolling 10 runs     | Identify top failing archetypes and prompts; add canary benchmark if needed |
| Repair effectiveness             | Whether repairs actually help      | Repeated ineffective repairs               | Audit repair prompts and preserve behavior; add targeted regression test    |
| Scanner warning class recurrence | Objective hygiene weakness         | Same warning class on 3+ release-gate runs | Fix, explicitly waive, or promote severity                                  |
| Visible content fidelity         | Content preservation               | Falling trend or repeated low outliers     | Feed dropped facts into repair; add anchor prompt if prompt family repeats  |
| Export failure rate              | Review-image path stability        | Any repeated export failure                | Add / fix export smoke coverage before continuing                           |
| Artifact completeness            | Observability quality              | Any missing required artifact              | Fix immediately; blocks trusting downstream metrics                         |
| Per-archetype benchmark weakness | Archetype-specific quality problem | Same archetype underperforms repeatedly    | Freeze archetype from active vocabulary or add examples before reuse        |


**Rule**: the ledger is not purely observational. Threshold breaches must create an issue, owner, and remediation decision.

### 10.9 Test Execution Tiers

**Tier 1 — Per-Run** (every pipeline execution, fully automated):

1. Stage contract validation at every handoff
2. Deterministic scanner for all objective hygiene checks
3. Content fidelity check (visible text, notes-only facts, hallucinated specifics)
4. Review-image export smoke for runs that reach review
5. Artifact completeness and `run_log.jsonl` stage-marker check
6. Metrics ledger append

**Tier 2 — Per-Change** (every code change, automated, CI or local):

1. Unit test suite
2. Example regression suite
3. Integration suite with mocked LLM calls

**Tier 2b — Canary Live Validation** (builder / reviewer / runtime / prompt-surface changes):

1. 3-5 release-gate prompts with live LLM calls
2. Repair-path smoke
3. Editability probe on at least one resulting deck

**Tier 3 — Periodic / Pre-Cutover** (human-in-the-loop):

1. Full paired V1 vs V3 benchmark on the release-gate subset
2. Separate reporting for forward-coverage and stress prompts
3. Editability audit on sampled decks
4. Metrics ledger trend review with explicit actions

### 10.10 Pass Criteria Summary


| Level                               | Criteria                                                                       | Gating?                                                   |
| ----------------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------------- |
| Per-run: contracts                  | All stage handoff contracts pass                                               | Yes                                                       |
| Per-run: scanner                    | Zero BLOCKING findings                                                         | Yes                                                       |
| Per-run: content fidelity           | Zero placeholder leaks, zero markdown leaks, zero hallucinated specifics       | Yes                                                       |
| Per-run: content fidelity           | Visible coverage below calibrated floor                                        | Repair-required; becomes hard gate only after calibration |
| Per-run: artifacts                  | Required attempt artifacts and stage markers present                           | Yes                                                       |
| Per-change: unit tests              | All pass                                                                       | Yes                                                       |
| Per-change: example regression      | All examples execute, pass scanner, and satisfy invariants                     | Yes                                                       |
| Per-change: canary live validation  | No catastrophic failures on canary prompts                                     | Yes for high-risk changes                                 |
| Periodic: release benchmark         | Calibrated release-gate subset passes agreed score bands                       | Yes — gates cutover                                       |
| Periodic: paired comparison         | V3 beats V1 on a majority of release-gate prompts                              | Yes — gates cutover                                       |
| Periodic: archetype coverage        | Every active archetype represented by at least one passing release-gate prompt | Yes — gates cutover                                       |
| Periodic: stress / forward-coverage | Reported separately; failures drive backlog and scanner fixtures               | No                                                        |
| Periodic: metrics trends            | Threshold breach must trigger owner + action                                   | Yes for remediation, not direct pipeline halt             |


**Not used as release gates**: fixed `≤ N` warning counts, stress prompts (TP-25/TP-26) by themselves, uncalibrated workbook averages.

### 10.11 Test Implementation Schedule

Tests land with the slices they de-risk:


| Slice                                      | Tests delivered                                                                                                                                                                                |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SLICE-004 (runtime skeleton)               | Unit tests for grid, tokens, canvas                                                                                                                                                            |
| SLICE-005 (measure_text)                   | Measurement unit tests, near-boundary fit tests                                                                                                                                                |
| SLICE-006 (shapes, patterns)               | Unit tests for shapes and patterns; no shape-count-only assertions                                                                                                                             |
| SLICE-006b (runtime validation)            | Example regression suite bootstrap with invariant-based assertions                                                                                                                             |
| SLICE-007 (example seeding)                | Example regression expansion; active-archetype/example coverage matrix                                                                                                                         |
| SLICE-008 (scanner + contracts + fidelity) | Scanner unit tests for all objective hygiene checks; content fidelity unit tests; artifact/log completeness tests; stage contract bootstrap for normalize/planner/feasibility/scanner handoffs |
| SLICE-009 (sandbox)                        | Sandbox unit tests for import rules, timeout, memory, write restrictions                                                                                                                       |
| SLICE-010 (planner + feasibility)          | Planner validation tests; normalize/cues tests; feasibility pass/fail boundary tests; asset-resolution failure tests                                                                           |
| SLICE-011 (builder + first e2e)            | Integration happy paths; contract-violation handling; review-image export smoke; canary live benchmark (3-5 release-gate prompts)                                                              |
| SLICE-012 (reviewer + repair)              | Repair-path integration; preserve-list tests; dropped-fact repair tests; editability probe                                                                                                     |
| SLICE-013 (CLI + metrics)                  | Metrics ledger implementation; threshold-to-action wiring; end-to-end CLI tests; artifact completeness on CLI runs                                                                             |
| SLICE-014 (cutover benchmark)              | Full paired V1 vs V3 release benchmark; stress/forward-coverage reporting; editability audit; metrics trend review with actions                                                                |


## 11) Migration Strategy

Phase 1 — Foundations (no LLM on the critical path):

- author `design_system.json`;
- build the `ppt_runtime` skeleton;
- hand-rewrite `alternate-approach/build.py` on the runtime and confirm fidelity;
- stand up the sandbox with a trivial script;
- land the deterministic post-build scanner.

Phase 2 — Example seeding:

- decompose user-provided designer slides into the example library;
- tag each with an archetype;
- confirm every seeded archetype has at least one working example.

Phase 3 — LLM slices:

- planner output schema + prompt (no build yet);
- builder prompt + one-archetype integration;
- multi-archetype integration;
- review rubric + repair loop;
- benchmark comparison vs. V1 placeholder.

Phase 4 — Cutover:

- once V3 beats V1 on majority of benchmark slides, route `generate-auto` through V3 by default;
- keep the V1 path as `generate --mode placeholder` for regression.

## 12) Non-Goals

- LLM-emitted coordinates, hex colors, or font sizes (ever).
- A full recipe library like V2.
- A per-slide builder call. One file per deck, one LLM call per build.
- HTML/CSS or browser rendering as a parallel engine.
- Pixel-diff tests.
- Automatic derivation of the design system from arbitrary templates. Manual authoring for now.
- Committing generated `build_deck.py` files to the repo.
- Locking the sandbox to VM-level isolation. Subprocess + rlimit + AST scan + RO mounts only.

## 13) Success Criteria

V3 ships as default when all are true:

1. Every archetype the planner is allowed to select has at least one executing example in the library, and the runtime can reproduce each example within the structural-fidelity threshold.
2. The deterministic scanner catches ≥ 90% of mechanical bugs before review on a seeded failure fixture set.
3. The end-to-end pipeline produces a composed deck from a real prompt with no manual intervention on the happy path.
4. The repair loop demonstrably improves review scores on at least 60% of aesthetically-flagged slides in benchmark runs.
5. On the release-gate subset of benchmark prompts (§10.7), V3 beats V1 on a majority of paired prompts, every active archetype has at least one passing prompt, and there are no catastrophic failures. Score bands are calibrated on a 10-prompt anchor set before becoming release gates.
6. Run artifacts are sufficient to debug any failure mode (every attempt, every exec report, every scan, every review persisted).
7. No metrics ledger threshold (§10.8) is in sustained breach at cutover time.

## 14) Open Decisions (carry into implementation)

- Runtime versioning scheme (per-commit hash vs. explicit semver).
- Whether `design_system.json` is derived by a one-time script or hand-authored from scratch.
- Whether the example selector uses tag match only or adds embedding similarity over `intent` strings.
- Whether the reviewer sees images for the selected examples as a second multimodal context, or only the candidate deck images.
- Whether repair rebuilds use a temperature lower than the initial build (likely yes).
- Whether `alternate-approach/build.py` stays in its current location or moves into `examples/source/` after rewrite.
- Whether candidate archetypes (`persona_use_case`, `feature_columns`, `services_overview`) graduate to the active vocabulary or collapse into existing archetypes after SLICE-007 decomposition.
- Whether section composers (`composers.py`) should be a separate module or folded into `patterns.py`. Current spec separates them for clarity; implementation may merge if the boundary is artificial.
- Archetype capacity values are initial estimates. Final values should be derived from example decomposition + measurement during SLICE-007.

