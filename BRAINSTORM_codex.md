# BRAINSTORM_codex.md — Independent First-Principles Design

This document is intentionally independent of `SPEC-v3.md`, `SPEC-v2.md`, and the earlier repo attempts. I started from the problem statement, the hard constraints, and the tools that are actually available:

- fixed org-specific template/theme/master
- user content plus optional visualization cues
- `python-pptx`
- three LLM passes: plan, emit code, review visuals
- required output: editable native PPTX

If any conclusion here overlaps with the current V3 spec, that is because the constraints push in the same direction, not because this document is derived from that spec.

## 1. The Problem, Stated Precisely

The job is not "generate slides."

The job is:

> given a branded PowerPoint environment and clear source content, produce a deck that is both:
> 1. narratively correct for the audience, and
> 2. visually credible enough that a human is editing, not rebuilding.

That breaks into four sub-problems:

1. Decide what the deck should say.
2. Decide what kind of slide each idea deserves.
3. Realize those slides as native PowerPoint objects without breaking the brand system.
4. Catch both mechanical defects and aesthetic defects before delivery.

The core architectural mistake to avoid is letting the same model invent content, geometry, typography, and visual quality from scratch every run. Those are not equally variable.

## 2. What Is Stable vs. Variable

### Stable per organization / template

- canvas size, safe areas, header/footer behavior
- theme fonts and color roles
- spacing rhythm and type hierarchy
- what a "good" title slide, section slide, comparison slide, KPI slide, process slide, etc. look like for that brand
- preferred icon/photo usage rules

### Variable per run

- argument spine
- audience emphasis
- slide count within a bounded range
- per-slide claims and evidence
- which visual family fits each message
- which brand-approved assets are pulled in

This leads to the first design decision:

> the system should compile template knowledge once, and spend run-time intelligence only on narrative and composition choices.

## 3. First-Principles Conclusions

### Conclusion 1: Geometry should not be an LLM responsibility

An LLM can choose "three support cards under a thesis statement." It should not decide that the left card starts at `Inches(0.47)` and ends at `Inches(4.63)`.

That means:

- no raw coordinate JSON from the planner
- no freehand inch arithmetic as the main authoring mode
- no expectation that the builder can mentally estimate text fit

### Conclusion 2: The planner should output communication intent, not layout math

The planner is best used for:

- audience-sensitive storyline
- one claim per slide
- evidence selection
- slide family choice
- density control
- visual intent and asset preference

The planner should not output:

- coordinates
- font sizes
- shape lists
- arbitrary component trees

### Conclusion 3: Code generation is the right builder interface, but only against a narrow DSL

I would not let the builder generate unconstrained raw `python-pptx` for the whole surface area. That is too fragile.

I would let it generate Python against a purpose-built runtime that gives it:

- semantic slide families
- local layout primitives
- deterministic text fit helpers
- brand tokens
- asset lookup helpers
- a tightly-scoped escape hatch

So the builder writes code, but the vocabulary looks like:

```python
slide = deck.add_slide("thesis_with_supports", canvas="header_light")
slide.title(claim)
slide.support_grid(items=supports, cols=3)
slide.callout(kind="risk", text=risk_note)
```

not:

```python
slide.shapes.add_shape(... Inches(4.33) ...)
```

### Conclusion 4: There should be a deterministic feasibility gate before rendering

The planner can still overstuff a slide even if it never emits geometry.

Before code generation proceeds, each slide brief should be checked against the capacity of its chosen slide family:

- max words
- max bullets
- max cards
- max columns
- max chart categories
- max label lengths

If a slide family cannot carry the requested content, the system should re-plan or split the slide before the builder ever runs. This is cheaper and more reliable than fixing overflow after the fact.

### Conclusion 5: Mechanical review and aesthetic review are different systems

These should be separate by design:

- deterministic scan catches: overflow, off-canvas, missing assets, markdown leakage, style drift, broken slide count, illegal colors/fonts
- visual review catches: weak hierarchy, clutter, awkward balance, poor emphasis, boring repetition, wrong visual choice

Running multimodal review before deterministic checks is wasteful.

### Conclusion 6: "Business content slides" and "diagram slides" are different problems

Narrative slides, comparison slides, KPI slides, timelines, and proof slides can share one runtime.

Architecture/system diagrams are different:

- graph layout is a different problem than editorial layout
- icon semantics matter more
- connector routing matters
- review criteria differ

I would explicitly keep diagrams out of the initial general pipeline and treat them as a later specialized composer.

## 4. The Architecture I Would Build

## 4.1 One-time Template Compilation

I would introduce a one-time per-template artifact, but I would treat it as a compiled contract, not just a design note.

Suggested output:

`assets/template/template_contract.json`

It would contain:

- canvas dimensions
- safe zones
- theme font roles
- semantic color tokens
- allowed canvases / master types
- spacing scale
- type scale
- accent usage rules
- header/footer behaviors
- allowable image treatments
- slide-family defaults for this template

I would derive as much of this as possible from the template/theme automatically, then hand-correct the parts that need judgment. Pure manual authoring is too error-prone; pure automatic derivation is not trustworthy enough.

## 4.2 Slide Family Registry

I would define a small fixed registry of slide families. Not dozens at first. Enough to cover the high-frequency business deck cases.

Example starter registry:

- `title_hero`
- `section_break`
- `thesis_with_supports`
- `two_column_compare`
- `card_grid`
- `process_flow`
- `timeline`
- `metric_spotlight`
- `evidence_table`
- `image_with_takeaways`
- `quote_or_case_study`
- `closing_decision`

Each family should define:

- allowed content slots
- capacity limits
- deterministic layout strategy
- optional variants
- which components it may use
- review heuristics specific to that family

This is not the same as a giant V2-style recipe catalog. The registry should be small, opinionated, and high leverage.

## 4.3 Runtime / DSL Layer

This is the most important part of the system.

The builder should target a runtime that sits between generated code and `python-pptx`.

The runtime should own:

- `Deck` and `Slide` construction
- canvas selection
- token lookup
- text measurement
- fit / shrink / truncate policies
- reusable components
- family-specific layout functions
- shape-level helpers
- PPTX-specific quirks

I would split the runtime into four layers:

### Layer A: Brand and canvas

- template loading
- master selection
- theme/token access
- safe-area and region definitions

### Layer B: Layout

- split / stack / grid / repeat primitives
- local regions instead of global coordinates
- padding and spacing helpers
- alignment helpers

### Layer C: Components

- title blocks
- kicker bars
- cards
- metric chips
- evidence rows
- timeline steps
- image frames
- callouts

### Layer D: Families

- compose a whole slide from the above pieces

This layering matters because it lets the builder work mostly at the family/component layer while still giving humans a place to extend the system cleanly.

## 4.4 Planner Pass

The planner should produce a `deck_blueprint.json`, not a rendering plan.

For each slide, I would require:

- `slide_id`
- `purpose`
- `core_claim`
- `supporting_evidence`
- `audience_takeaway`
- `slide_family`
- `visual_intent`
- `density_budget`
- `must_preserve`
- `acceptance_checks`

Example shape:

```json
{
  "slide_id": "legacy_constraint",
  "purpose": "establish_thesis",
  "core_claim": "Legacy fragmentation is slowing delivery and increasing operating risk.",
  "supporting_evidence": [
    "Three systems of record create duplicate workflow ownership.",
    "Change lead time increased from 5 to 14 days in the last two quarters.",
    "Teams are compensating with manual controls."
  ],
  "audience_takeaway": "The problem is structural, not just operational.",
  "slide_family": "thesis_with_supports",
  "visual_intent": {
    "prefer": ["risk_callout"],
    "avoid": ["stock_photo"]
  },
  "density_budget": {
    "max_words": 70,
    "max_support_items": 3
  },
  "must_preserve": ["core_claim"],
  "acceptance_checks": [
    "single focal point",
    "three balanced supports"
  ]
}
```

The important thing is that the planner is describing intent, evidence, and constraints. It is not designing.

## 4.5 Feasibility Gate

This is the phase I would add very early because it reduces downstream chaos.

For each planned slide:

- validate that its chosen family exists
- validate that the slot counts fit the family
- validate density against family limits
- validate asset availability where hints are specific
- validate that required evidence exists for claim-heavy slides

If it fails:

- first preference: deterministic correction if trivial
- second preference: planner repair on just the bad slides
- never let the builder "figure it out somehow"

## 4.6 Builder Pass

The builder should emit one Python file for the whole deck.

But I would constrain the builder more than a normal codegen task:

- one function per slide
- shared deck-level style object
- required use of runtime families/components first
- raw `python-pptx` only inside approved escape-hatch helpers
- no raw hex colors
- no arbitrary font sizes
- no direct global coordinate arithmetic except inside runtime internals

In practice, the builder prompt should include:

- the template contract summary
- the deck blueprint
- the runtime API docs
- 2-3 canonical examples for each referenced slide family
- hard negative instructions on what not to do

I would also bias the builder toward:

- shape-based charts for simple bar / metric visuals when styling control matters
- native tables for tabular evidence
- native text boxes for all text content
- raster images only for photos and icons, never for slide bodies

## 4.7 Example Grounding

I would absolutely use example grounding, but I would structure it narrowly.

What I want is not a generic example library. I want:

- 2-3 excellent examples per slide family
- each example implemented in the same runtime/DSL
- each example annotated with:
  - what is invariant
  - what can vary
  - what density limit it tolerates
  - which audience/style it suits

The builder should only receive examples relevant to the slide families in the current plan. Dumping the full library into context is noise.

## 4.8 Sandbox Execution

This can be pragmatic for local development, but it still needs real boundaries:

- AST import linting
- allowlisted modules
- wall-clock timeout
- memory and CPU limits
- read-only assets
- write-only attempt directory
- full artifact capture

Generated code should be disposable and fully persisted per run:

- prompt inputs
- emitted code
- execution report
- produced PPTX
- scan report
- review feedback

## 4.9 Deterministic Post-Render Scan

I would treat this as a first-class product feature, not a utility.

Checks should include:

- text overflow by measured fit
- off-canvas shapes
- overlap in blocked regions
- missing or broken images
- markdown markers rendered literally
- illegal colors or fonts
- inconsistent title style usage
- unexpected slide count / ordering drift
- excessive accent usage on a slide
- obviously empty or under-filled slides

This scan should emit both blocking failures and non-blocking warnings.

## 4.10 Visual Review Pass

The reviewer should see:

- slide images
- the deck blueprint
- the deterministic scan summary
- the final emitted structure summary per slide

The reviewer should score slides on a fixed rubric, for example:

- hierarchy
- density
- alignment / balance
- focal clarity
- brand consistency
- visual appropriateness
- evidence legibility
- message clarity

The reviewer should not propose coordinates. It should propose slide-level change requests:

- split this slide
- reduce support count from 4 to 3
- use metric spotlight instead of card grid
- strengthen focal point on slide 5
- swap decorative image for evidence visual

## 4.11 Repair Loop

I would use two repair loops:

### Loop A: mechanical repair

Triggered by deterministic scan failures.

Input to builder:

- previous code
- exact failing slides
- exact failure reasons
- instruction to preserve all passing slides

### Loop B: aesthetic repair

Triggered by reviewer scores below threshold.

Input to builder:

- previous code
- reviewer findings
- preserve list of accepted slides
- revised slide-family guidance where necessary

If the same slide fails twice for the same reason, I would escalate by changing the family or splitting the slide, not by asking the builder to "tweak layout again."

## 5. Design Choices I Would Explicitly Reject

### Reject 1: planner emits coordinates

This is the wrong abstraction boundary.

### Reject 2: fully unconstrained raw `python-pptx` generation

Too much surface area, too much drift, too hard to review.

### Reject 3: giant recipe library before proving a narrow family set

Premature library-building can consume months. I would start with a very small family registry and expand only after seeing real misses.

### Reject 4: HTML/CSS or image-first rendering

It breaks the editable-native-PPT promise.

### Reject 5: architecture diagrams in the first general solution

They deserve a separate composer once the narrative-slide path is stable.

## 6. Where I Expect the Real Difficulty

The hard parts are not "getting a valid PPTX."

The hard parts are:

1. keeping density honest before the builder runs
2. making family selection strong enough that the first build is usually plausible
3. building text fit and overflow handling that behaves predictably
4. giving the builder enough expressive power without reopening geometry chaos
5. defining review prompts that produce actionable repairs instead of vague opinions

That means the highest-leverage investments are:

- the template contract
- the family registry
- text measurement and fit logic
- deterministic scan quality
- high-quality family-specific examples

not broad planner cleverness.

## 7. Recommended Initial Scope

If I were running this from scratch, I would deliberately narrow V1 of the new architecture to:

- 6-8 common non-diagram slide families
- one template/org
- text, shapes, tables, icons, and photos
- no freeform architecture diagrams
- one repair loop for mechanical issues and one for visual issues

Success would mean:

- the system can generate a 6-12 slide executive deck where most slides need light editing only
- failures are legible from artifacts
- adding a new slide family is incremental, not architectural

## 8. Practical Build Order

I would implement in this order:

1. `template_contract.json` compiler plus manual review step
2. runtime foundation: tokens, canvases, regions, text measurement
3. 6-8 slide families with deterministic capacity rules
4. deterministic scan
5. builder pass against the runtime
6. reviewer pass and repair loop
7. example-library expansion
8. specialized diagram composer later

I would not start with planner sophistication. I would start with the rendering substrate and the family registry, because they define the ceiling of output quality.

## 9. Bottom Line

If I had to summarize the design in one sentence:

> build a template-compiled, slide-family-driven PowerPoint runtime; make the planner choose message and family; make the builder write constrained Python against that runtime; let deterministic checks catch mechanics and let multimodal review catch taste.

That is the design I would trust to improve output quality without giving the model too much freedom in the one area where it is consistently weak: slide geometry.
