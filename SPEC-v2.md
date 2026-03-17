# SPEC-v2.md — AI Presentation Generator (GPT-5.4, Skills, Deterministic PowerPoint Composer)

## 0) Purpose

This spec fully replaces the prior `SPEC-v2.md`.

The target system is a general-purpose presentation generation agent that:
- accepts a prompt, optional visualization cues, and optional reference slides;
- generates a fully native, editable `.pptx` deck;
- preserves company branding through customer-provided PowerPoint templates;
- plans each slide at the element level instead of only filling placeholders;
- uses `gpt-5.4` and reusable skills for narrative, composition, review, and repair;
- deterministically renders PowerPoint-native objects and persists run artifacts for every stage.

The quality bar is not "valid PPTX". The quality bar is near top-tier consulting and executive communication polish within bounded archetypes, controlled visual grammar, and reference-backed review.

---

## 0.1) Product Thesis

The main failure in the first version was not the Python stack itself. The failure was that the system behaved like a placeholder filler rather than a presentation composer.

This revised architecture therefore changes the planning model more than the file-emission model:
- the AI layer must reason about narrative role, slide archetype, visual hierarchy, shape selection, spacing, typography, color, and background treatment;
- the deterministic layer must translate that plan into native PowerPoint objects with strict validation;
- the review layer must inspect rendered slides visually and drive targeted slide repair.

The renderer remains Python-first because template preservation is still a hard requirement.

---

## 0.2) Outcome Target

A successful run produces a deck that:
- opens in Microsoft PowerPoint without repair prompts;
- remains manually editable at the text, shape, connector, chart, and table level;
- uses the customer theme and template correctly;
- exhibits coherent slide-to-slide rhythm and varied visual structure;
- passes deterministic safety gates and visual review gates;
- is strong enough that a human editor is polishing, not rebuilding.

---

## 0.3) Architecture Summary

The system is organized into five cooperating layers:
1. Presentation layer: template understanding, design tokens, slide archetypes, visual grammar, and element-level composition plans.
2. AI layer: `gpt-5.4` planning, skill loading, per-slide composition, and multimodal review/repair.
3. Deterministic renderer: `python-pptx` plus a bounded OOXML bridge for edge cases.
4. Review layer: slide export, per-slide diagnostics, per-slide visual review, and targeted repair.
5. Delivery layer: CLI first, local web UI second, cloud-hosted API third.

---

## 1) Non-Negotiable Constraints

### 1.1 Native PPTX Output
- Output must be `.pptx`.
- Output must open in Microsoft PowerPoint.
- Text, shapes, lines, connectors, tables, and charts must remain editable.
- Do not export slides as images inside the final deck.

### 1.2 Template-First Branding
- The system must accept a customer-provided branded `.pptx` template.
- The system must preserve masters, layouts, theme colors, and theme fonts.
- Placeholder binding remains `shape.alt_text == field_key` for `template_native` slides.
- `composed` slides may render on blank or low-content layouts, but must still inherit template theme tokens and rhythm rules.

### 1.3 PowerPoint-Native Visuals
- The system must use the same native object families users expect from PowerPoint's `Home` and `Insert` tabs:
  - text boxes and placeholders;
  - shapes;
  - lines and connectors;
  - tables;
  - charts;
  - pictures and icons;
  - grouped visual constructs assembled from the above.
- The system is not automating the PowerPoint UI. It is generating the same underlying native objects programmatically.

### 1.4 Deterministic Safety
- All LLM outputs must be schema-validated.
- All final rendering decisions must pass deterministic validation before render.
- Every run must persist artifacts under `runs/<run_id>/`.
- Visual review may recommend changes, but rendering never executes raw free-form LLM text as code.

### 1.5 Asset Format Policy
- Render path supports raster assets (`PNG`, `JPG`, `WebP`).
- Source SVGs may exist in catalogs, but must be converted before render.
- Do not add SVG directly to the runtime render path.

### 1.6 Review Image Generation
- Automated slide previews remain headless.
- Preferred backend: **Aspose.Slides** (`aspose-slides` Python package).
  - Converts PPTX → PDF and PPTX → PNG directly with high fidelity.
  - Evaluation mode adds a watermark to outputs; this is acceptable because review images are intermediate artifacts — final deliverables are the `.pptx` files.
  - Requires `libgdiplus` system library (`brew install mono-libgdiplus` on macOS).
- Fallback backend: LibreOffice + Poppler.
  - `soffice` for `PPTX -> PDF`
  - `pdftoppm` for `PDF -> PNG`
  - Lower layout/typography fidelity than Aspose.Slides; use when Aspose is unavailable.
- Do not rely on GUI automation in the core pipeline.

### 1.7 Delivery Surfaces
- The first production surface is CLI.
- The second surface is a locally run web UI on the laptop.
- The third surface is a cloud-hosted endpoint.
- All three surfaces must use the same planning, rendering, and review contracts.

---

## 2) Primary Architecture Decisions

## 2.1 Rendering Engine: Python + `python-pptx` (Accepted)

**Decision**
- Primary renderer remains Python with `python-pptx`.

**Why**
- Template preservation is mandatory.
- Existing branded masters/layouts already encode valuable presentation design work.
- The current repo already has deterministic rendering, validation, and artifact scaffolding around Python.
- A renderer rewrite would not solve the core composition-planning problem.

**Implication**
- The major architectural investment shifts to slide planning, visual grammar, and review-driven repair.

**Edge-case strategy**
- Introduce a bounded OOXML bridge for features that `python-pptx` cannot express directly.
- OOXML escape hatches must live behind helper APIs and tests.

**Non-goal**
- Do not rewrite the runtime around `PptxGenJS` as the primary engine.
- A future spike comparing one composed slide family in a Node stack is allowed, but it is not the baseline architecture.

## 2.2 AI Runtime: `gpt-5.4` + Skills via Responses API (Accepted)

**Decision**
- Primary planning and review model family is `gpt-5.4`.
- Runtime should use the OpenAI Responses API when available so the system can leverage Skills and modern tool orchestration.

**Why**
- The planner must do more than summarize content; it must compose slides at the element level.
- The review loop must interpret slide images, compare them to intent, and issue bounded repair instructions.
- Reusable skills materially improve consistency across blueprint types, slide archetypes, and company brand rules.

**Provider strategy**
- Canonical capability target is OpenAI-hosted `gpt-5.4` with Skills support.
- Azure/OpenAI-compatible deployment remains supported, but the architecture must not assume identical provider feature parity.
- Internal skill definitions must therefore be provider-agnostic and projectable into either:
  - native OpenAI Skills, or
  - local prompt/context bundles for providers without the same skill surface.

## 2.3 Slide Strategy: Hybrid `template_native` + `composed` (Accepted)

**Decision**
- Keep two rendering routes:
  - `template_native`: use existing template placeholders and designer-authored layouts when the slide structure already fits them well.
  - `composed`: use a composition plan to place native PowerPoint primitives on a template-aligned canvas.

**Routing principle**
- A slide must not be forced through placeholders if the message requires custom visual structure.
- A slide must not be custom-composed if the template already provides a better branded layout for that slide type.

**Target steady state**
- Most complex slides should use `composed`.
- Many title, divider, simple content, and straightforward two-column slides may remain `template_native`.

## 2.4 Review Policy: Per-Slide Visual Review with Targeted Repair (Accepted)

**Decision**
- Review is performed at the slide level, not only at the full-deck level.
- The reviewer produces slide-specific findings and repair instructions.
- Review findings are fed back into the slide planner/repair planner as structured input, not just logged as commentary.
- Repair rerenders only the affected slides unless a deck-level narrative issue requires wider replan.

**Review loop iteration limit**
- The system allows a maximum of **2 review/repair loops** per run.
- Loop 1: render V1 → review V1 → repair → render V2.
- Loop 2: review V2 → repair → render V3 (only for slides still blocking after loop 1).
- After 2 loops the run must stop regardless of remaining findings. Unresolved findings are recorded in the run summary but do not trigger further iterations.
- The system may batch review calls, but the review contract must remain per-slide.

## 2.5 Skills Policy: OpenAI Skills + Internal Skill Repository (Accepted)

**Decision**
- The system will use two skill layers:
  - base runtime Skills provided by OpenAI where available;
  - a versioned internal skills repository that encodes company-specific deck standards.

**Purpose of internal skills**
- Tell the planner what each slide should look like.
- Encode slide archetype rules, brand rules, reference patterns, and review standards.
- Make the system opinionated and repeatable rather than generic.

---

## 3) Presentation Layer

The presentation layer is the source of truth for how a slide should look and what PowerPoint-native primitives may be used.

## 3.1 Responsibilities

The presentation layer must provide:
- template inspection;
- theme extraction;
- design token generation;
- a PowerPoint primitive catalog;
- slide archetype definitions;
- visual recipe definitions;
- layout rhythm rules;
- composition constraints;
- render-ready slide element plans.

## 3.2 Template Inspection

For every input template, the system must extract and persist:
- slide size;
- masters and layouts;
- placeholder map;
- theme fonts;
- theme colors;
- title bands and margin tendencies;
- background treatments available in the template;
- reusable branded layouts suitable for `template_native` routing.

Required artifact:
- `runs/<run_id>/template_inspection.json`

## 3.3 Design Tokens

The system must convert the template into deterministic design tokens, including:
- typography roles:
  - `display`
  - `h1`
  - `h2`
  - `h3`
  - `body`
  - `caption`
  - `footnote`
- color roles:
  - `bg_primary`
  - `bg_secondary`
  - `surface`
  - `surface_muted`
  - `text_primary`
  - `text_secondary`
  - `accent_1`
  - `accent_2`
  - `success`
  - `warning`
  - `risk`
- spacing scale:
  - `xs`, `sm`, `md`, `lg`, `xl`
- stroke scale:
  - `hairline`, `thin`, `standard`, `emphasis`
- radius scale:
  - `none`, `sm`, `md`, `pill`
- shadow/effect policy:
  - allowed, discouraged, forbidden effect families.

All composed slides must use tokenized values unless an explicit recipe override is defined.

Required artifact:
- `runs/<run_id>/design_tokens.json`

## 3.4 PowerPoint Primitive Catalog

The presentation layer must define the allowed primitive families used to emulate the visual language of PowerPoint `Home` and `Insert`.

Allowed primitive families for MVP:
- `text_box`
- `placeholder_text`
- `shape_rect`
- `shape_round_rect`
- `shape_circle`
- `shape_line`
- `shape_bar`
- `shape_chevron`
- `shape_arrow`
- `connector_straight`
- `connector_elbow`
- `connector_curved`
- `table`
- `chart_bar`
- `chart_column`
- `chart_line`
- `chart_pie`
- `image`
- `icon`
- `group`

Derived visual constructs may be built from those primitives, including:
- metric cards;
- process flows;
- timelines;
- architecture diagrams;
- comparison matrices;
- icon-label grids;
- callout clusters;
- section hero slides.

### 3.4.1 Home/Insert Mapping Requirement

For every derived construct, the system must be able to explain which PowerPoint-native primitives it maps to.

Example:
- `timeline` = round rectangles + lines/connectors + text boxes + optional icons.
- `architecture_diagram` = grouped rectangles + connectors + labels + optional icons.
- `metric_cards` = rounded rectangles + text boxes + accent bars.

This keeps the system grounded in editable native PowerPoint objects instead of opaque custom drawing logic.

## 3.5 Slide Archetypes

The system must ship with a bounded library of slide archetypes. Each archetype defines:
- its narrative role;
- content contract;
- visual recipe options;
- default route (`template_native` or `composed`);
- allowed primitive families;
- text budgets;
- density limits;
- reference examples;
- review checklist.

Initial required archetypes:
- `title_hero`
- `section_break`
- `executive_summary`
- `problem_statement`
- `current_vs_target`
- `capability_overview`
- `process_flow`
- `roadmap`
- `architecture_diagram`
- `comparison`
- `kpi_snapshot`
- `case_study`
- `decision_next_steps`

## 3.6 Visual Recipes

Each archetype must support one or more visual recipes.

A visual recipe specifies:
- composition pattern;
- focal point strategy;
- background treatment;
- primitive mix;
- title treatment;
- evidence placement;
- image/icon rules;
- contrast rules;
- whitespace expectations;
- anti-patterns.

Example visual recipe IDs:
- `exec_summary_cards`
- `exec_summary_split_hero`
- `roadmap_horizontal_phases`
- `roadmap_swimlane`
- `architecture_layered_stack`
- `architecture_hub_spoke`
- `process_stepper`
- `comparison_matrix`

Required artifact:
- `assets/catalog/visual_recipes_v1.json`

## 3.7 Element-Level Composition Contract

Each composed slide must be planned at the element level.

Minimum `SlidePlan` fields:
- `slide_id`
- `narrative_role`
- `archetype_id`
- `visual_recipe_id`
- `route`
- `base_layout_id`
- `background_plan`
- `title_plan`
- `regions[]`
- `elements[]`
- `text_budget`
- `review_targets[]`

Minimum `SlideElementPlan` fields:
- `element_id`
- `semantic_role`
- `primitive_family`
- `bounds`
- `z_index`
- `content_binding`
- `style_tokens`
- `shape_spec`
- `line_spec`
- `text_spec`
- `background_spec`
- `asset_ref`
- `validation_rules[]`

This is the central architectural change from V1.

---

## 4) AI Layer

The AI layer is responsible for narrative planning, slide-level composition planning, review, and repair.

## 4.1 Model Roles

Required model roles:
- `deck_planner`: strong structured planner using `gpt-5.4`
- `slide_composer`: per-slide composition planner using `gpt-5.4`
- `visual_reviewer`: multimodal slide reviewer using the strongest available `gpt-5.4`-compatible image-capable endpoint
- `repair_planner`: structured repair planner using `gpt-5.4`

The same model family may serve multiple roles, but prompts, schemas, and skills must remain role-specific.

## 4.2 Skill Loader

The AI layer must load three skill classes per run:
- deck-level skills;
- slide archetype skills;
- review/remediation skills.

### 4.2.1 Canonical Internal Skill Repository

The internal skill repository is the source of truth.

Recommended structure:
- `skills/brand/`
- `skills/blueprints/`
- `skills/archetypes/`
- `skills/visual_recipes/`
- `skills/review/`
- `skills/remediation/`

Each skill must be versioned and may include:
- instructions;
- examples;
- allowed visual patterns;
- prohibited patterns;
- required evidence patterns;
- review rubric fragments;
- tests or fixtures.

### 4.2.2 OpenAI Skills Projection

When running against OpenAI-hosted infrastructure that supports Skills:
- selected internal skill bundles may be projected into native OpenAI Skills;
- skill selection may occur at deck scope or slide scope;
- runtime must persist the resolved skill set used for reproducibility.

When native Skills are unavailable:
- the same skill content must be injected as structured prompt context.

Required artifact:
- `runs/<run_id>/resolved_skills.json`

## 4.3 Planning Workflow

The planner is hierarchical. It does not emit a deck in one giant step.

### Pass 0 — Intake and Context Assembly
- normalize user content and visualization cues;
- load template inspection and design tokens;
- load applicable skills;
- load relevant reference slides;
- classify deck blueprint.

Artifacts:
- `normalized_content.json`
- `template_inspection.json`
- `resolved_skills.json`
- `reference_packet.json`

### Pass 1 — Deck Blueprint Planning
The deck planner determines:
- deck objective;
- audience;
- narrative arc;
- slide roster;
- slide count;
- slide archetype per section;
- target evidence pattern per slide;
- target visual variety constraints across the deck.

Artifact:
- `deck_blueprint_v1.json`

### Pass 2 — Slide Brief Planning
Each slide receives a brief that captures:
- slide purpose;
- key message;
- audience takeaway;
- must-include evidence;
- avoid/forbid notes;
- recommended visual recipe candidates;
- route recommendation.

Artifact:
- `slide_briefs_v1.json`

### Pass 3 — Per-Slide Composition Planning
Each slide is planned independently, but with neighbor context.

The slide composer must decide:
- title treatment;
- background treatment;
- region layout;
- exact primitive families to use;
- shape, line, and connector choices;
- font roles and token selections;
- color token usage;
- visual emphasis strategy;
- asset placement and crop mode;
- text budgets per element;
- overflow fallback strategy.

This pass must return `SlidePlan` objects, not only layout names.

Artifacts:
- `slide_plan_v1/<slide_id>.json`
- `deck_render_plan_v1.json`

### Pass 4 — Deterministic Validation and Repair Prep
Before render, deterministic logic must validate:
- allowed primitive families;
- token compliance;
- text density budgets;
- asset availability;
- route/layout compatibility;
- non-overlap and bounds sanity;
- archetype-specific payload caps.

Blocking failures may cause:
- deterministic compression;
- component swap;
- recipe reroute;
- targeted replan request.

Artifact:
- `planning_validation_v1.json`

### Pass 5 — Visual Review and Repair Planning
After render and slide export, the review model must evaluate each slide and decide one of:
- `accept`
- `minor_repair`
- `major_replan`

Review must examine:
- content quality and message clarity;
- placement, alignment, spacing, and visual balance;
- visual appeal, emphasis, and slide polish;
- slide image;
- slide plan;
- diagnose output;
- neighboring slides;
- relevant archetype skill and review rubric.

Artifacts:
- `visual_review_v1/<slide_id>.json`
- `deck_review_summary_v1.json`
- `repair_plan_v1/<slide_id>.json`

### Pass 6 — Targeted Repair Render
The repair planner consumes the multimodal review output and produces updated slide plans.
Only flagged slides are rerendered unless the review explicitly marks a deck-level narrative issue.

Artifact:
- `slide_plan_v2/<slide_id>.json`
- `deck_render_plan_v2.json`

## 4.4 Planning Rules

The AI layer must follow these rules:
- do not invent layouts or primitives outside the allowed catalog;
- do not style individual elements with arbitrary fonts/colors outside the token system;
- do not overfill slides beyond archetype budgets;
- do not repeat the same visual pattern on adjacent slides unless explicitly justified;
- do not treat visuals as decoration separate from the message.

---

## 5) Deterministic Renderer

The deterministic renderer translates validated slide plans into a native `.pptx`.

## 5.1 Responsibilities

The renderer must:
- open the template presentation;
- create `template_native` slides from placeholders when appropriate;
- create `composed` slides on template-aligned layouts when needed;
- render native PowerPoint objects;
- apply tokenized typography and styling;
- persist diagnostics and mapping metadata;
- isolate OOXML edge cases.

## 5.2 Route Types

### `template_native`
Use when:
- the template already contains the right structure;
- slide complexity is low to medium;
- custom composition would not materially improve clarity.

Required inputs:
- `layout_id`
- field bindings
- optional image/icon bindings

### `composed`
Use when:
- slide structure requires explicit composition control;
- the message depends on diagramming, card layouts, process flows, or carefully balanced evidence blocks;
- placeholder layouts would materially reduce quality.

Required inputs:
- `base_layout_id`
- `background_plan`
- `regions[]`
- `elements[]`

## 5.3 Renderer Modules

Required renderer modules:
- `template_loader`
- `token_resolver`
- `layout_solver`
- `element_factory`
- `asset_resolver`
- `chart_factory`
- `table_factory`
- `connector_router`
- `diagnostics_emitter`
- `ooxml_bridge`

## 5.4 Layout Solver

The solver is bounded and deterministic.

It may support only:
- `inset`
- `split_h`
- `split_v`
- `grid`
- `stack`
- `center`
- `anchor`

The solver does not emulate CSS or full responsive layout. It solves fixed-canvas PowerPoint composition.

## 5.5 Element Rendering Rules

Every element render must resolve:
- absolute bounds in slide coordinates;
- typography tokens;
- fill/stroke tokens;
- alignment;
- z-order;
- asset crop/contain policy;
- text overflow policy.

### 5.5.1 Text Rendering
The renderer must support:
- bold/italic/underline where required;
- paragraph spacing and indentation;
- bullet and numbered list styles;
- alignment;
- emphasis spans;
- speaker notes spillover as a last resort.

### 5.5.2 Shape and Line Rendering
The renderer must support:
- rectangles and rounded rectangles;
- circles and dots;
- bars and accent rules;
- arrows, chevrons, and banners where recipes allow;
- connectors with line style, weight, and arrowhead policy.

### 5.5.3 Chart and Table Rendering
- Use native PowerPoint charts when structured numeric data exists.
- Use native tables when tabular evidence is the clearest form.
- If data is too sparse or too narrative for a chart, prefer shape-based composition instead of low-value charts.

### 5.5.4 Background Rendering
Background selection is part of the slide plan.

Allowed background treatments:
- theme solid fill;
- tokenized surface blocks;
- branded hero image;
- section divider image;
- light accent wash;
- template-native background already present on chosen layout.

Every background treatment must preserve text contrast and focal clarity.

## 5.6 OOXML Bridge

The OOXML bridge exists only for targeted gaps such as:
- unsupported connector features;
- grouping edge cases;
- niche formatting not reliably available through `python-pptx`;
- preservation fixes where the template object model requires lower-level access.

OOXML bridge rules:
- no business logic in OOXML patch helpers;
- helper APIs only;
- snapshot tests or structural assertions required;
- avoid speculative patches.

---

## 6) Review Layer

The review layer turns rendered slides into actionable repair instructions.

## 6.1 Review Inputs

Each slide review packet must include:
- rendered slide image;
- slide plan;
- slide diagnostics;
- slide brief;
- neighboring slide summaries;
- archetype skill;
- review rubric.

## 6.2 Review Outputs

Each slide review output must include:
- `slide_id`
- `decision`
- `severity`
- `summary`
- `findings[]`
- `repair_instructions[]`
- `must_preserve[]`
- `reroute_required`
- `planner_feedback`

## 6.3 Review Dimensions

Reviewer must score or classify at minimum:
- content quality and message clarity;
- hierarchy and scanability;
- placement, alignment, spacing, and balance;
- visual relevance;
- visual appeal and polish;
- asset quality and fit;
- brand fit;
- archetype fit;
- deck continuity relative to neighboring slides.

## 6.4 Repair Policy

Repairs may change:
- recipe choice;
- element sizing and spacing;
- shape emphasis;
- background treatment;
- asset choice;
- title/body budgets;
- route (`template_native` to `composed`, or vice versa) when justified.

Repairs may not change:
- core deck narrative without an explicit deck-level issue;
- template identity;
- required compliance/brand constraints.

## 6.5 Review-To-Planner Feedback Loop

The multimodal review loop is a required planning stage, not an optional post-process.

Required behavior:
- every rendered slide is reviewed visually;
- the reviewer emits structured feedback for content, placement, and visual appeal;
- that feedback is converted into planner-facing repair input;
- the repair planner updates the slide plan before rerender;
- the repaired slide is re-reviewed when it was previously blocking.

**Hard iteration cap:** the review-repair loop runs at most **2 iterations** (see §2.4). After the cap is reached the pipeline proceeds to quality gates with whatever findings remain. This prevents oscillation where the reviewer and repair planner trade conflicting instructions indefinitely.

This loop must remain explicit in both artifacts and runtime control flow.

---

## 7) Reference Corpus and Skills Inputs

The system must consume three reference classes:
- company template and brand assets;
- company-approved reference slides and decks;
- public benchmark/reference slides for structural inspiration where usage permits.

## 7.1 Reference Usage Rules

Reference material is used to guide:
- slide archetype choices;
- visual recipes;
- spacing and density expectations;
- hierarchy patterns;
- quality review rubrics.

Reference material is not used to copy proprietary content verbatim.

## 7.2 Required Reference Artifacts

Required artifacts:
- `assets/ground_truth/deck_blueprints_v1.json`
- `assets/ground_truth/slide_archetypes_v1.json`
- `assets/ground_truth/quality_rubric_v1.json`
- `assets/ground_truth/reference_manifest_v1.json`
- `assets/catalog/visual_recipes_v1.json`
- `assets/catalog/ppt_primitive_catalog_v1.json`

---

## 8) Runtime Tech Stack

## 8.1 Core Runtime
- Python 3.11+
- `python-pptx`
- `pydantic` v2
- `orjson`
- `fastapi`
- `uvicorn`
- `pytest`

## 8.2 Review Toolchain
- **Preferred:** `aspose-slides` (Python) — high-fidelity PPTX → PDF/PNG; evaluation watermark acceptable for review artifacts
- **Fallback:** LibreOffice `soffice` + `pdftoppm` — used when Aspose.Slides is not installed
- System dependency for Aspose path: `libgdiplus` (`mono-libgdiplus` on macOS via Homebrew)

## 8.3 AI Runtime
- OpenAI Responses API as canonical runtime where available
- `gpt-5.4` as primary planning model
- strongest available multimodal GPT-5.4-compatible endpoint for slide review
- provider abstraction for Azure/OpenAI-compatible deployments

## 8.4 Non-Core Development/Authoring Tools
- Codex models may be used during development or internal authoring workflows
- they are not required runtime dependencies for presentation generation

---

## 9) Artifacts and Logging

Minimum run artifacts:
- `normalized_content.json`
- `template_inspection.json`
- `design_tokens.json`
- `resolved_skills.json`
- `reference_packet.json`
- `deck_blueprint_v1.json`
- `slide_briefs_v1.json`
- `slide_plan_v1/<slide_id>.json`
- `deck_render_plan_v1.json`
- `planning_validation_v1.json`
- `deck_v1.pptx`
- `diagnose_report_v1.json`
- `review_images/v1/slide_*.png`
- `visual_review_v1/<slide_id>.json`
- `deck_review_summary_v1.json`
- `repair_plan_v1/<slide_id>.json`
- `slide_plan_v2/<slide_id>.json`
- `deck_render_plan_v2.json`
- `deck_v2.pptx`
- `diagnose_report_v2.json`
- `quality_gates_v2.json`
- `run_summary.json`
- `run_log.jsonl`

Required log markers:
- `NORMALIZE_DONE`
- `TEMPLATE_INSPECTION_DONE`
- `SKILL_RESOLUTION_DONE`
- `DECK_BLUEPRINT_DONE`
- `SLIDE_BRIEFS_DONE`
- `SLIDE_PLANS_V1_DONE`
- `PLANNING_VALIDATION_V1_DONE`
- `RENDER_V1_DONE`
- `REVIEW_IMAGES_INGESTED`
- `VISUAL_REVIEW_V1_DONE`
- `REPAIR_PLANS_V1_DONE`
- `SLIDE_PLANS_V2_DONE`
- `RENDER_V2_DONE`
- `DIAGNOSE_V2_DONE`
- `QUALITY_GATES_V2`
- `RUN_COMPLETE` or `RUN_FAILED_QUALITY_GATES`

---

## 10) Quality Gates

A final deck passes only if all blocking gates pass.

Required gates:
- `native_pptx_opens`
- `no_blocking_overflow`
- `no_object_collisions`
- `token_compliance`
- `brand_template_compliance`
- `reviewed_all_slides`
- `no_slide_left_unrepaired_after_blocking_review`
- `visual_hierarchy_floor`
- `visual_density_floor`
- `asset_diversity_floor`
- `archetype_alignment`
- `deck_variety_floor`
- `no_markdown_marker_leak`
- `image_asset_presence_floor`

Every gate must produce machine-readable evidence.

---

## 11) Testing Strategy

## 11.1 Unit Tests
- template inspection
- token extraction
- primitive catalog validation
- skill resolution
- planner schema validation
- layout solver invariants
- element rendering helpers
- OOXML bridge helpers
- review output schema validation

## 11.2 Integration Tests
- one-slide end-to-end composed render
- one-slide visual review and repair
- multi-slide CLI generation
- artifact persistence contract

## 11.3 Visual Validation Tests
- no pixel-perfect snapshots
- structural and perceptual assertions only
- slide density and whitespace heuristics
- primitive counts and collision checks
- review-decision determinism for fixture cases

## 11.4 Benchmark Tests
- benchmark deck generation using fixed skill packs and fixed inputs
- archetype score thresholds
- visual variety thresholds
- V1 vs V2 KPI deltas where relevant

---

## 12) Delivery Surfaces

## 12.1 CLI (First Surface)

The CLI is the first production surface.

Required capabilities:
- run generation from prompt/content files;
- select template;
- select skill packs;
- run one-slide or full-deck generation;
- rerun review/repair for a single slide;
- inspect artifacts under `runs/<run_id>/`.

## 12.2 Local Web UI (Second Surface)

The locally run web UI is the second surface.

Required capabilities:
- upload or paste content;
- choose template and skill pack;
- preview generated slides;
- inspect review findings per slide;
- trigger regenerate for a single slide;
- download final deck.

The local web UI is a presentation shell over the same backend pipeline.

## 12.3 Cloud Endpoint (Third Surface)

The cloud endpoint is the third surface.

Required capabilities:
- create generation job;
- poll job status;
- retrieve artifacts and final deck;
- request per-slide repair;
- support local hosting or Azure-hosted deployment.

---

## 13) Out of Scope

Out of scope for the baseline architecture:
- full WYSIWYG browser canvas parity with PowerPoint;
- animation choreography as a primary deliverable;
- arbitrary freeform drawing beyond the approved primitive catalog;
- dependence on PowerPoint desktop automation;
- full replacement of the Python renderer with a JS-first renderer.

---

## 14) Success Criteria

The architecture is successful when all are true:
1. A one-slide composed archetype can go from prompt to reviewed, repaired, editable `.pptx`.
2. A 5-slide deck can maintain visual variety without losing brand coherence.
3. A 10-15 slide benchmark deck can pass hard safety gates with zero blocking overflow.
4. At least 5 distinct archetypes can render through the composed path with acceptable review scores.
5. Slide review results are per-slide, actionable, and result in measurable repair improvements.
6. Template swap changes branding without code changes.
7. The same backend works through CLI, local web UI, and cloud endpoint.
8. Skill packs can deterministically influence slide look-and-feel in reproducible ways.

---

## 15) Required Follow-Up Artifacts

After this spec is accepted, the following must exist or be updated:
- `PLAN.md` rewritten to vertical slices aligned to this spec
- `README.md` updated for new CLI/runtime flow
- deck blueprint catalog
- slide archetype catalog
- visual recipe catalog
- PowerPoint primitive catalog
- internal skill repository scaffold
- new slide plan schemas and fixtures
