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

| Check | Method | Severity |
|---|---|---|
| Slide count matches `deck_plan` | Length compare | BLOCKING |
| No empty slides | `len(shapes) >= 2` | BLOCKING |
| No off-canvas shapes | Shape bbox vs. slide dims | BLOCKING |
| No leaked markdown markers | Regex scan on text runs | BLOCKING |
| All picture rels resolve | Walk `rels` vs. package parts | BLOCKING |
| Text frames fit their bounds | `measure_text` per run vs. frame | WARNING → repair |
| No large overlaps between non-background shapes | AABB intersection with threshold | WARNING → repair |
| All colors map to `tokens` palette | Compare fills/lines/fonts to token hexes | WARNING → repair |
| All fonts are in the substitute allowlist | Compare run fonts to `font_substitution` | WARNING → repair |
| No raw hex literal patterns in adjacent `build_deck.py` | Static lint on the generated code file | WARNING |

**Output**: `geometry_report.json`. Any BLOCKING result triggers the repair build loop immediately. WARNING results are aggregated and passed to the reviewer as context.

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

## 5) Archetype Vocabulary

Planner output archetypes are drawn from a fixed vocabulary. Each archetype carries capacity metadata used by the feasibility gate (§4.3 step 4). Initial set (to be expanded as the example library grows):

| Archetype | Intent | max_items | max_words | canvas_pref |
|---|---|---|---|---|
| `hero_title` | Deck cover with headline, optional subhead, optional backdrop | 2 | 30 | `header_dark` |
| `section_break` | Divider slide between deck sections | 2 | 20 | `header_dark` |
| `hero_statement_with_support_columns` | One dominant statement + 2-4 supporting columns | 4 supports | 85 | `header_light` |
| `three_cards` | Three parallel concepts with title + body | 3 cards | 90 | `blank` |
| `comparison_split` | Two-sided before/after, us/them, problem/solution | 2 sides, 4 pts/side | 80 | `blank` |
| `kpi_grid` | Grid of 4-6 large metrics with labels | 6 metrics | 60 | `blank` |
| `stat_list_with_icons` | Vertical list of stats with an icon per row | 5 rows | 75 | `header_light` |
| `process_flow` | Linear or staged process with 3-6 steps | 6 steps | 90 | `blank` |
| `quote_callout` | Single large quotation with attribution | 1 quote | 50 | `header_dark` |
| `content_with_visual` | Text on one side, image or diagram on the other | 1 text + 1 visual | 60 | `blank` |
| `closing_cta` | Call-to-action closer with next steps | 3 items | 50 | `header_light` |
| `matrix_grid` | Labeled rows x labeled columns of content cells | 4 rows x 3 cols | 150 | `blank` |
| `timeline_roadmap` | Phased timeline with milestones and durations | 5 phases | 100 | `blank` |

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

- **Unit**: planner schema validation; builder input assembly; AST sandbox rejection of disallowed imports; runtime grid math; `measure_text` against known strings; token lookup; geometry scan checks.
- **Integration**: one-archetype single-slide pipeline (plan → build → scan → review → stop); multi-slide pipeline across all seeded archetypes; mechanical repair loop recovery; aesthetic repair loop improvement.
- **Regression**: every example file in `examples/` must continue to execute after any runtime change, producing a deck that passes the full geometry scan.
- **Benchmark**: 10 curated test prompts in `assets/benchmarks/v3_test_prompts.xlsx`, each targeting a specific archetype with deliberately ambiguous user instructions. Side-by-side V1 placeholder vs. V3 composed, scored by the user on the 7-axis rubric below.

### 10.1 Benchmark Evaluation Rubric

Each test prompt is scored on 7 axes (1-5 scale):

| Axis | What it measures |
|---|---|
| Content Fidelity | Does the output capture all user-specified content without fabrication? |
| Archetype Selection | Did the planner pick the right layout family for the content? |
| Visual Hierarchy | Is there a clear focal point and natural reading flow? |
| Density & Readability | Does the content fit without overflow, with appropriate whitespace? |
| Brand Consistency | Are all colors, fonts, and spacing from the design system tokens? |
| Editability | Can a non-designer edit the content and maintain layout quality? |
| Mechanical Defects | Does the geometry scan return zero blocking findings? |

**Per-prompt pass**: average across all 7 axes ≥ 3.5 AND no single axis ≤ 2.

**Benchmark pass** (V3 ships as default): ≥ 7 of 10 test prompts pass AND V3 output is rated higher than V1 placeholder output on a majority of prompts by the user's own scoring.

The rubric is intentionally aligned with the multimodal reviewer's 8-axis scoring (§4.8). The benchmark axes are a superset: `Content Fidelity` and `Archetype Selection` are human-only judgments not available to the automated reviewer. `Mechanical Defects` subsumes what the deterministic scanner checks. The remaining 4 axes map directly to reviewer axes.

Full axis definitions with score-level descriptions are in `assets/benchmarks/v3_test_prompts.xlsx` Sheet 3 ("Axis Definitions").

No pixel-perfect visual diffs. No tests that require the Azure/Gemini API for correctness signals; mock the LLM layer.

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
5. On the 10 benchmark prompts (`assets/benchmarks/v3_test_prompts.xlsx`), ≥ 7 pass the 7-axis rubric (§10.1), and V3 is rated higher than V1 on a majority of prompts.
6. Run artifacts are sufficient to debug any failure mode (every attempt, every exec report, every scan, every review persisted).

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
