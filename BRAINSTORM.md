# BRAINSTORM.md — First-Principles Design For PPT Generation

This document is an independent design exercise. It does not start from V1/V2/V3. It starts from the problem and derives an architecture. Comparisons come at the end.

## 1) What is the actual problem?

Reframed without jargon:

> Given a branded template, user text, and optional visual hints, produce a native editable PowerPoint deck that a discerning reader would call "well designed."

The output constraint is firm: native PPTX, editable, brand-consistent. That rules out HTML-to-image, slide screenshots, and proprietary non-PowerPoint formats.

The inputs split into two categories:
- **Fixed per organization**: template, masters, brand colors, theme fonts, canvas dimensions, visual conventions. These change rarely.
- **Variable per run**: content, narrative intent, optional visual cues. These change every time.

The mistake most pipelines make is treating both categories as equally variable and asking an LLM to decide everything from scratch each run. A lot of the "design" work is actually stable per template — it should be computed once and reused.

## 2) What LLMs can and cannot do here

This is the single most important upstream question. Architecture follows from it.

**LLMs are good at:**
- Writing narrative prose, headlines, and bullets from source content.
- Choosing which visual pattern fits a given message ("this is a before/after, use a 2-column comparison").
- Writing code — including `python-pptx` code — when given clear constraints and good examples.
- Critiquing a rendered image against a structured rubric.
- Preserving consistency across a single response when all slides are generated together.

**LLMs are bad at:**
- Emitting precise numeric coordinates in structured output. Every independent reviewer and Anthropic's own claude-for-PowerPoint team hit this wall. This is the single most robust negative finding in the domain.
- Measuring whether a string of text will fit inside a rectangle at a given font size. They have no visual feedback and no calibrated priors for font metrics.
- Cross-slide consistency across separate calls — colors drift, grid systems drift, type scales drift.
- Catching overlapping shapes, off-canvas elements, or broken image references after the fact. They need the raw file, which they cannot parse visually.

**The design implication**: spatial reasoning cannot live in an LLM's structured output, but it can live in code an LLM writes — if the code is expressed in terms the LLM can manipulate (named anchors, grid cells, helper functions) rather than raw EMUs. Text measurement cannot live in an LLM's head, so it must be a deterministic primitive the LLM calls.

## 3) First principles

These are the decisions that fall out of the analysis above.

### Principle 1: Separate stable-per-template from variable-per-run

The grid system, type scale, spacing rules, and accent usage rules for a given template are stable. They should be authored or derived once, stored as a durable artifact, and loaded by every run. Not generated per run. Not LLM-decided per run.

### Principle 2: The planner picks patterns, not geometry

The planner is good at "this slide is a 3-card comparison with a hero metric above." It is bad at "card 1 is at x=0.5in y=2.1in w=3.9in h=2.4in." Capture the first, forbid the second. The planner outputs a fixed-vocabulary archetype label plus semantic content; the builder figures out how to realize it.

### Principle 3: The builder writes code, but in the builder's preferred vocabulary

Raw `add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))` with hand-computed arithmetic is a test of the model's mental math. Instead, the builder should write code like:

```python
with grid(cols=12, gutter="md") as g:
    for i, card in enumerate(cards):
        draw_card(slide, g.span(cols=4, row=1, col=1 + i*4),
                  title=card.title, body=card.body, accent=tokens.accent_1)
```

The grid, tokens, and `draw_card` helper are part of a thin runtime library. The builder composes them. Spatial reasoning becomes compositional, not arithmetical. This is genuinely hard for LLMs to get wrong because it looks like CSS flexbox — a domain models have seen a million times.

### Principle 4: Text measurement is a deterministic primitive, not a hope

The most common bug in every approach I've seen is text not fitting. Fix it at the source:

```python
w, h = measure_text("Operational Excellence", font="Inter", size=16, bold=True)
if h > target_rect.height:
    size = shrink_to_fit("Operational Excellence", target_rect, max_size=16, min_size=10)
```

`measure_text` is Pillow-backed, runs in the sandbox, and returns accurate rendered dimensions for the substitute fonts the repo ships. The builder can check its work *before* committing to a bounding box. This single primitive kills the majority of layout bugs cheaply.

### Principle 5: Cross-slide consistency is a contract, not a hope

If slide 3's headline is 28pt and slide 5's is 30pt, the deck feels sloppy. You don't fix this with a reviewer — you fix it by **never letting it happen**. Two complementary mechanisms:

- **Deck style contract**: a single artifact per run that pins accent strategy, type scale, grid system, spacing scale. The builder loads it at the top of the generated code.
- **Single-pass builder call for all slides**: one LLM call produces one code file containing all slides. Consistency is preserved because the model holds all slides in one context. Not a cluster of independent per-slide calls.

### Principle 6: Determinism catches mechanical errors; review catches aesthetic ones. Use both.

There are two classes of bug:

| Class | Example | Best catcher |
|---|---|---|
| Mechanical | Text clipped, shape off-canvas, broken image, leaked `**` markers, duplicate icon | Deterministic post-render scan |
| Aesthetic | Boring hierarchy, awkward composition, weak focal point, crowded density | Multimodal reviewer |

Running multimodal review on a deck with mechanical bugs is a waste of tokens — the reviewer fixates on "the text is cut off" and never gets to judgment calls. **Deterministic checks run first; review only sees mechanically-correct output.** Repair loops are two-phase: geometry-fix before aesthetic-fix.

### Principle 7: The reviewer needs a rubric, not an open question

"What's wrong with this slide?" produces vague prose. "Score this slide 1-5 on contrast, alignment, hierarchy, density, whitespace balance, brand adherence, variety, and message clarity" produces a prioritizable work list. Structure the review like a code review checklist, not a vibes check.

### Principle 8: The escape hatch matters

No helper library will cover every legitimate slide. The builder must always be able to drop to raw `python-pptx` for unusual cases. Helpers are the preferred path, not the only path. Lock down the sandbox, not the API surface.

## 4) Architecture derivation

From the principles above, the shape of the pipeline falls out.

You need:
- A stable per-template **design system artifact** (derived once).
- A planner that outputs a **style contract + semantic slide briefs** with archetype labels.
- A thin **builder runtime library** — grid, tokens, measurement, shape helpers, escape hatch.
- A builder LLM pass that generates **one deck-level Python file** using the runtime.
- A **sandbox** that executes the file and captures the PPTX.
- A **deterministic post-build scanner** that walks the PPTX for mechanical bugs.
- A **structured multimodal reviewer** that scores the rendered images on a rubric.
- A **repair builder pass** that rewrites the file preserving accepted slides.
- **Quality gates** that stop or escalate based on deterministic + visual signals.

No single step is novel. The value is in how they compose and what each is responsible for.

## 5) The pipeline

### Phase 0 — Design system derivation (once per template)

**Input**: template .pptx + brand assets.

**Output**: `design_system.json`, containing:

```jsonc
{
  "canvas": { "width_emu": 12192000, "height_emu": 6858000,
              "safe_area": { "left": "0.5in", "right": "0.5in",
                             "top": "0.4in", "bottom": "0.4in" } },
  "grid":   { "cols": 12, "gutter_md": "0.15in", "gutter_lg": "0.3in" },
  "type_scale": {
      "display":  { "font": "Space Grotesk", "size": 40, "bold": true },
      "title":    { "font": "Space Grotesk", "size": 28, "bold": true },
      "subtitle": { "font": "Inter",        "size": 16, "bold": false },
      "body":     { "font": "Inter",        "size": 12, "bold": false },
      "caption":  { "font": "Inter",        "size": 10, "bold": false }
  },
  "spacing_scale": { "xs": "0.08in", "sm": "0.15in", "md": "0.25in",
                     "lg": "0.4in",  "xl": "0.6in" },
  "tokens": { /* from token_overrides.json, semantic colors */ },
  "canvases": { /* from canvas_config.json: blank, header_light, header_dark */ },
  "accent_policy": {
      "primary": "accent_1",
      "secondary_sparse": "accent_2",
      "max_accents_per_slide": 2
  }
}
```

This is **authored, not LLM-generated**. It is checked into the repo next to the template. You change it when the template changes. Every downstream phase treats it as ground truth.

### Phase 1 — Normalize (deterministic)

Existing V1 behavior: combined markdown → content model + cues. No changes.

### Phase 2 — Planner (LLM pass #1)

**Input**:
- Content model + cues
- Design system summary (archetypes, tokens, constraints)
- Fixed archetype vocabulary (~15 labels like `hero_title`, `section_break`, `three_cards`, `comparison_split`, `hero_metric_with_support`, `process_flow`, `kpi_grid`, `quote_callout`, `stat_list_with_icons`, `content_with_diagram`, `closing_cta`)

**Output**: `deck_plan.json`

```jsonc
{
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
      "headline": "Legacy complexity is now a growth constraint",
      "hero_text": "Fragmentation slows delivery and compounds operational risk.",
      "supports": [
        { "label": "The problem", "body": "..." },
        { "label": "What we won't do", "body": "..." },
        { "label": "What we will do", "body": "..." }
      ],
      "visual_intent": { "must_include": ["risk_callout"], "avoid": ["stock_photo"] },
      "density_budget": { "max_words": 85, "max_groups": 3 },
      "must_preserve": ["headline", "accent_strategy"],
      "acceptance": ["clear focal point", "three equally-weighted supports"]
    }
  ]
}
```

Key properties:
- No coordinates.
- Archetype is from a fixed vocabulary the builder knows about.
- Style contract is deck-level, not slide-level.
- Content is semantic (labels, bodies, heroes) not presentational (cards, rectangles, colors).

### Phase 3 — Pre-build enrichment (deterministic)

- Resolve icon concepts → concrete asset paths via `visual_vocabulary.json`.
- Resolve branded image hints → concrete paths via `branded_images.json`.
- Attach design system tokens to each slide brief for the builder prompt.
- Run text budget pre-check: for each slide, measure the headline and body at the smallest reasonable font; if they blow the budget, request a re-plan before spending builder tokens.

**Output**: `builder_input.json` — the planner output plus resolved assets, tokens, design system, and canvas dims.

### Phase 4 — Builder (LLM pass #2)

**Runtime library** the builder imports (actual Python module, not prose docs):

```python
# ppt_runtime/__init__.py
from .canvas   import Canvas, load_template, pick_canvas
from .grid     import Grid, Rect
from .tokens   import Tokens
from .measure  import measure_text, shrink_to_fit
from .shapes   import add_rect, add_text, add_image, add_line, add_connector
from .patterns import draw_card, draw_stat_block, draw_kicker, draw_header_bar
# plus: escape hatch — `from pptx import ...` is allowlisted
```

- `Canvas` wraps a `pptx.Presentation` and exposes `body_left`, `body_top`, `body_width`, `body_height`, `add_slide(canvas_name)`.
- `Grid(cols=12)` gives `g.span(col_start, col_span, row_start=..., row_height=...)` returning a `Rect`.
- `Tokens` gives `tokens.color("accent_1")`, `tokens.type("title")` with values from the design system.
- `measure_text(text, type_style) -> (w, h)` uses Pillow + bundled fonts.
- `shrink_to_fit(text, rect, type_style, min_size)` returns the largest type size that fits.
- `draw_card(slide, rect, title, body, accent)` is an opinionated pattern — padding, hierarchy, accent stripe, bold title, body below. Roughly 20-30 lines of python-pptx under the hood. Half a dozen such patterns cover most archetypes.

**Builder prompt**:
- System: "You are writing `build_deck.py` using the `ppt_runtime` library. You must use runtime helpers and token names, not raw EMUs or hex colors. You may import from `pptx` for shapes the runtime doesn't cover. Always use `measure_text` before sizing a text box. Always load colors via `tokens.color(...)`. The deck must use exactly N slides matching the provided plan."
- Few-shot: `alternate-approach/build.py` rewritten to use the runtime — the strongest possible signal of what "good" looks like.
- User: `builder_input.json` + the archetype vocabulary docs + runtime API reference.

**Output**: a single `build_deck.py` file. One artifact for the whole deck. Cross-slide consistency comes free because the model holds all slides in one context.

### Phase 5 — Sandbox execution

Subprocess in a restricted environment:
- Read-only bind mounts on `assets/template/`, `assets/icons/`, `assets/catalog/`, `assets/fonts/`, the runtime module
- Writable root = `runs/<run_id>/build_attempts/attempt_NN/`
- Network blocked
- Time limit via `resource.setrlimit`
- AST pre-scan of generated code rejecting: `import os` (except `os.path`), `import subprocess`, `__import__`, `eval`, `exec`, network libs, any write outside the attempt dir
- Capture stdout, stderr, traceback, exit code

Retry budget: 3 attempts on failure. Failure reasons feed back into the next attempt's prompt.

### Phase 6 — Deterministic post-build scan

Open the produced PPTX with `python-pptx` and walk every shape:

| Check | Source of truth |
|---|---|
| Slide count matches plan | plan length |
| No empty slides | shape count per slide ≥ 2 |
| No leaked `**` / `*` in text | string scan |
| No text frame overflow | `measure_text` on each run, compared to frame size |
| All picture rels resolve | scan blip refs against pkg parts |
| No shape bbox outside canvas | slide dims |
| No large shape overlaps | AABB intersection among non-background shapes |
| All colors are from token palette | scan fills and fonts |
| Font names are on the substitute list | scan runs |

**Output**: `geometry_report.json`. Hard failures escalate directly to a repair builder call without burning a review pass.

### Phase 7 — Review image export

Existing soffice + pdftoppm path. No changes.

### Phase 8 — Visual review (LLM pass #3)

**Prompt contract**:

```jsonc
{
  "per_slide_scores": [
    { "slide_id": "...",
      "axes": {
        "contrast":          { "score": 4, "note": "..." },
        "alignment":         { "score": 3, "note": "card gutters uneven" },
        "hierarchy":         { "score": 5, "note": "..." },
        "density":           { "score": 2, "note": "too sparse, body box half empty" },
        "whitespace":        { "score": 4, "note": "..." },
        "brand_adherence":   { "score": 5, "note": "..." },
        "variety_vs_prev":   { "score": 4, "note": "..." },
        "message_clarity":   { "score": 5, "note": "..." }
      },
      "repair_hints": ["increase body content or shrink card column width"]
    }
  ],
  "deck_summary": { "overall": 4, "weakest_slides": ["..."], "strongest_slides": ["..."] }
}
```

Scores drive prioritization: any axis ≤ 2 is a repair target; any axis ≤ 3 is optional. The builder doesn't have to guess what matters.

### Phase 9 — Repair builder (LLM pass #2, second call)

**Input**:
- Prior `build_deck.py`
- `geometry_report.json` (if any mechanical bugs)
- `visual_review.json` (if any axis ≤ 2)
- Unchanged `builder_input.json`
- Instruction: "Return a full replacement `build_deck.py`. Keep slides not in the repair list byte-identical. For flagged slides, apply the listed repair hints."

Regeneration with preservation is prompt-level, not enforced by the runtime. That's fine — the cost of a drifted untouched slide is low and will be caught by the next review pass if it matters. The spec does not need to guarantee it.

### Phase 10 — Quality gates and stop

Gates:
- Deterministic scan passes all mechanical checks.
- No review axis scored ≤ 2 on any slide.
- Average review score ≥ 3.5.
- Slide count matches plan.

Retry budget: 1 repair loop by default, 2 max. Beyond that, ship the best attempt with a failure report.

## 6) What I would NOT do

- **No LLM-emitted coordinates, ever.** Even as an "advanced" mode. The failure mode is well-documented.
- **No full recipe engine** like V2. Writing one card pattern helper is cheap; writing 40 archetype recipes is months of work and still bounds what slides exist.
- **No per-slide builder calls.** Cross-slide consistency is worth the deck-level context size.
- **No pixel-diff tests.** They are brittle and don't measure what you care about.
- **No HTML/CSS intermediary.** It doesn't round-trip to editable PPTX.
- **No attempt to "teach the LLM the grid" via prose.** Ship it the runtime module and a few-shot example. Prose is the slow path.
- **No over-engineered sandbox.** Subprocess + rlimit + AST scan + RO mounts is enough on a single-developer machine. VMs, containers, and seccomp filters are yak-shaves for this use case.
- **No generated design system.** Grid, type scale, and spacing are authored or derived from the template, never LLM-decided per run.
- **No committing generated code.** The `build_deck.py` for each run lives only in `runs/<run_id>/`. The runtime library does live in the repo.

## 7) What's different from V1, V2, and V3

| Decision | V1 | V2 | V3 | This design |
|---|---|---|---|---|
| Who owns geometry | Template designer | Recipe Python classes | LLM writing raw code | LLM writing code against a named-anchor runtime |
| Who owns archetype choice | Template layout catalog | LLM picks from recipe library | Implicit in planner visual_intent | Fixed archetype vocabulary in planner output |
| Style consistency mechanism | Template placeholders | Recipe-shared tokens | Cross-slide hope | Deck style contract + single builder call |
| Text overflow defense | Post-render validation | Recipe-internal measurement | Multimodal review | `measure_text` primitive called at build time |
| Mechanical bug defense | Placeholder bounds | Recipe math | Multimodal review | Deterministic scan before review |
| Aesthetic bug defense | None | Review loop | Review loop | Structured rubric review loop |
| Builder output granularity | N/A | N/A | Ambiguous per-slide vs. per-deck | One deck-level file |
| Repair mechanism | Planner V2 | Slot adjustment | Unclear | Regenerate file with preserve-list |
| Engineering surface | Small | Very large (recipe library) | Medium (sandbox) | Medium (sandbox + small runtime + scanner) |
| Proof of concept | Shipped | Never shipped | `alternate-approach/build.py` | Same proof — runtime is the abstraction that script hand-rolled |

The single most important difference from V3: **this design does not rely on the builder being able to do spatial arithmetic correctly.** V3 hopes the coding model can get EMU math right because it's a coding model. This design removes the arithmetic from the builder's responsibility by giving it a grid primitive and a text measurer. That's a much smaller ask and a much more reliable one.

The single most important difference from V2: **no recipe library.** The runtime is ~500 lines of grid + tokens + measurement + shape helpers + half a dozen patterns. A recipe library is thousands of lines of per-archetype geometry code. The builder composes runtime primitives; the runtime is not a whole-slide compositor.

The single most important difference from V1: **slides are composed from primitives, not form-filled into template placeholders.** This is the same move V2 and V3 both make. What distinguishes this design is *how* the composition is done.

## 8) What I'd build first

If I were starting this today, I'd do it in this order:

1. **Phase 0 artifact**: hand-author `design_system.json` for the current template. Two days. No LLM involved. This unblocks everything.
2. **Runtime library v0**: `Canvas`, `Grid`, `Tokens`, `measure_text`, `add_rect`, `add_text`, `add_image`, `draw_card`. Maybe 400 lines. One week.
3. **Rewrite `alternate-approach/build.py` on top of the runtime** — by hand, no LLM. Prove the runtime is expressive enough to reproduce a slide set you already trust. If it isn't, the runtime is missing a primitive. Fix it and iterate. This is the design's "can this work" gate.
4. **Sandbox harness**: subprocess + rlimit + AST scan + RO mounts. Three days if you don't over-engineer it.
5. **Deterministic scanner**: rewrite diagnose for composed PPTX using the checks in Phase 6. One week.
6. **Builder LLM pass**: prompt construction + few-shot from step 3. Two weeks of iteration.
7. **Structured reviewer**: the existing reviewer scaffold rewritten around the 8-axis rubric. One week.
8. **Repair loop**: regeneration with preservation. One week.
9. **Quality gates + benchmarks**: compare against V1 placeholder baseline on ~10 prompts. Decide whether to migrate.

The critical test is step 3. If the runtime cannot reproduce a hand-authored high-polish slide, no amount of LLM tuning in later steps will fix it. The runtime is the load-bearing abstraction of the whole design, and it is cheap to validate before committing to the rest.

## 9) Open questions I haven't answered

- **How many archetypes in the fixed vocabulary?** My guess is 12-20. Too few is limiting; too many is a de facto recipe library with extra steps. I'd start with 8 and add as benchmarks reveal gaps.
- **Do patterns like `draw_card` belong in the runtime, or should the builder re-derive them each run from raw shapes?** Runtime is safer and faster to iterate on; raw is more flexible. I'd start with runtime patterns and allow the builder to bypass them for unusual cases.
- **Does the repair loop regenerate the whole file or patch specific slides?** I picked regeneration above for simplicity. A patching mode (via `libcst`-style AST rewrite) is possible but adds complexity. Benchmarks would decide.
- **Should the design system artifact be derived from the template automatically or authored by hand?** I picked authored above. Automatic derivation is possible (scan reference slides, extract dominant type sizes and gutters) but the ground-truth catalogs in the repo already give you most of what you need for manual authoring.
- **Per-slide vs. whole-deck review call?** I'd do whole-deck for the cross-slide "variety" axis, but it makes the image payload large. Might need to split in practice.
