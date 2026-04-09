# SPEC-v2.md — Recipe-Driven Presentation Generator

Status (`2026-04-09`):
- Superseded for active development by `SPEC-v3.md`.
- Retained as historical context for the recipe-driven composed-slide direction.
- The implemented repo still reflects parts of the V1/V2-era placeholder pipeline, but new architecture work should target `SPEC-v3.md`.

## 0) Purpose

This spec defines the V2 architecture for a general-purpose presentation generation agent.

V1 is a working placeholder-filler: it binds LLM-planned text and icons into pre-designed template layouts. It produces valid, branded PPTX files, but every slide is constrained to the spatial structure the template designer authored. It cannot compose a slide from primitives.

V2 adds a **recipe-driven composition engine** that assembles native PowerPoint objects (shapes, text boxes, connectors, icons, tables, charts) on a fixed canvas using deterministic, parameterized layout recipes. The LLM selects a recipe and fills its semantic slots. The recipe engine computes all coordinates. The LLM never outputs spatial values.

The quality bar is: a human editor is polishing phrasing and emphasis, not rebuilding layout or fixing overlap.

---

## 0.1) What Already Exists (V1 Baseline)

These components are implemented and tested in the current codebase. V2 builds on top of them; it does not discard them.

### Rendering Pipeline
- `python-pptx` renderer that opens a branded template, selects a layout by `layout_id`, binds text to placeholders by `shape.alt_text == field_key`, places icons/images into image placeholders, and writes speaker notes.
- Markdown inline formatting (`**bold**`, `*italic*`) parsed into text-run formatting.
- Validation and remediation: text overflow detection, bullet count enforcement, character budget truncation, line estimation, speaker-notes spillover.
- Composition spec projection: deterministic metadata tracking what was remediated and why.

### LLM Planner
- Supports Gemini and Azure OpenAI providers via a `LLMClient` abstraction.
- Emits a `DeckIR` (list of `DeckSlide` objects, each with `layout_id`, `fields` dict, `asset_refs`, `speaker_notes`).
- Consumes content model, visualization cues, layout catalog constraints, icon catalog, visual vocabulary, branded image catalog, component catalog, and planner policy.
- Planning guardrails: intent briefs, structure plans, visual realization plans, pre-planning validation.

### Review Loop
- Single-cycle automated pipeline: plan V1 → validate → render V1 → export review images → diagnose → multimodal review → plan V2 → validate → render V2 → diagnose → quality gates.
- Review image export via Aspose.Slides (PPTX → PDF/PNG, evaluation watermark acceptable for review artifacts).
- Multimodal reviewer consumes slide images, planner output, composition spec, and diagnose report; emits structured `ReviewFeedback` with slide findings and change requests.
- Diagnose script compares rendered PPTX against DeckIR to detect overflow, missing images, layout drift.

### Quality Gates
- `no_blocking_overflow`, `image_layout_visual_coverage`, `no_hero_icon_misuse`, `no_markdown_marker_leak`, `min_visual_density`, `min_image_asset_presence`, plus planning-aware gates.

### Asset Catalogs
| Catalog | Location | Contents |
|---|---|---|
| Layout catalog | `assets/layout/layout_catalog.json` | 12 template layouts with placeholder maps and constraint budgets |
| Icon index | `assets/icons/icons.json` | ~29,000 icons (Tabler 5,928; Fluent 19,401; Lucide 1,542; AWS 1,842) |
| Icon PNGs | `assets/icons/png/external/{pack}/` | Pre-rasterized PNGs ready for PowerPoint embedding |
| Visual vocabulary | `assets/catalog/visual_vocabulary.json` | ~100+ concept-to-icon mappings with domain tags |
| Branded images | `assets/catalog/branded_images.json` | Theme images for section breaks and title slides |
| Component catalog | `assets/catalog/component_catalog_v1.json` | Semantic component definitions with size constraints |
| Planner policy | `assets/catalog/planner_policy_v1.json` | Asset diversity rules, routing guidance, prompt directives |
| Template style baselines | `assets/catalog/template_style_baselines_v1.json` | Typography and color defaults extracted from the template |
| Template | `assets/template/template.pptx` | Branded Ascendion template with masters/layouts |

### CLI
- `validate`: template-catalog drift check.
- `render`: DeckIR JSON to PPTX.
- `smoke`: deterministic validate → preflight → render cycle.
- `generate`: combined markdown → LLM or deterministic plan → validate → render.
- `generate-auto`: full automated loop with multimodal review.

### Tests
- 18 test files covering: CLI, config, normalization, pipeline, renderer, preflight, drift, quality gates, composition, planning guardrails, planner metadata, visual fill, assets, Aspose export, review loop, LLM client, Pydantic models.

---

## 0.1.1) Pre-Build Readiness Checklist

Everything needed before V2 development starts. Check items off as they land in the repo.

**Fonts** (needed for: text measurement, recipe layout, review image fidelity)

- [x] Space Grotesk Regular/Bold/Light — `assets/fonts/SpaceGrotesk-*.ttf` (sub for PP Neue Machina)
- [x] Inter Regular/Bold/Italic/BoldItalic — `assets/fonts/Inter-*.ttf` (sub for Aptos)
- [x] Carlito Regular/Bold/Italic/BoldItalic — `assets/fonts/Carlito-*.ttf` (sub for Calibri)
- [x] Lato Light/LightItalic/Regular/Bold — `assets/fonts/Lato-*.ttf` (sub for Calibri Light)
- [x] Font mapping manifest — `assets/fonts/font_map.json`

**Icon Packs** (needed for: architecture diagrams, visual vocabulary, asset resolver)

- [x] AWS service icons (PNG, 1,842) — `assets/icons/png/external/aws/`
- [x] Fluent icons (PNG, 19,401) — `assets/icons/png/external/fluent/`
- [x] Lucide icons (PNG, 1,542) — `assets/icons/png/external/lucide/`
- [x] Tabler icons (PNG, 5,928) — `assets/icons/png/external/tabler/`
- [x] Azure service icons (SVG source, 628) — `assets/external_assets/azure/svg/`
- [x] Azure service icons (PNG, converted, 628) — `assets/icons/png/external/azure/`
- [x] GCP service icons (SVG + PNG source, 19) — `assets/external_assets/gcp/`
- [x] GCP service icons (PNG, converted, 19) — `assets/icons/png/external/gcp/`
- [x] Icon index updated with Azure + GCP entries (29,573 total) — `assets/icons/icons.json`
- [x] Visual vocabulary extended with Azure/GCP + cross-cloud concepts (302 total) — `assets/catalog/visual_vocabulary.json`

**Template** (needed for: recipe canvas, design token extraction, branding)

- [x] Branded Ascendion template — `assets/template/template.pptx`
- [x] Layout catalog — `assets/layout/layout_catalog.json`
- [x] Canvas config (canonical master + 3 recipe canvas layouts) — `assets/template/canvas_config.json`
- [x] Brand color token overrides (15 semantic roles) — `assets/template/token_overrides.json`

**Reference Slides** (needed for: recipe geometry calibration, review quality baseline)

Source decks (13.33" x 7.50" widescreen, matching our template):
- [x] Capability Deck (28 slides) — `assets/template/Ascendion-Data Practice-Capability Deck_final.pptx`
- [x] AI Services Deck (12 slides) — `assets/template/AI Services  Applied AI Offerings.pptx`

Supplementary decks (10" x 5.62", scale 1.333x for geometry):
- [x] Case Study A4 (content schema) — `assets/template/Case Study Template_A4.pptx`
- [x] Case Study L1/L2 (layout patterns) — `assets/template/Case Study_L1.pptx`, `Case Study_L2.pptx`
- [x] RFP Template (39 layouts) — `assets/template/RFP PPT Template_V1.2_2025.pptx`

Archetype coverage from tagged reference slides (40 total):
- [x] `title_hero` — 3 reference slides (Capability s1, AI s1, Capability s25)
- [x] `section_break` — 5 reference slides (Capability s9,12,15,19,21)
- [x] `executive_summary` — 6 reference slides
- [x] `process_flow` — 5 reference slides (AI s3,5,8,11; Capability s10)
- [x] `architecture_diagram` — 5 reference slides (AI s6,11; Capability s5,14,17)
- [ ] `comparison` — 0 reference slides — **still needed**
- [x] `kpi_snapshot` — 7 reference slides
- [ ] `roadmap` — 0 reference slides — **still needed**
- [x] `case_study` — 6 reference slides + A4 content schema
- [x] `capability_showcase` — 18 reference slides
- [x] `rfp_template` — 39 layouts cataloged from RFP template
- [x] `strategy` — 3 reference slides

Metadata artifacts:
- [x] Full slide catalog (40 slides, per-shape geometry) — `assets/ground_truth/reference_slide_catalog.json`
- [x] Supplementary catalog (case study fields + RFP layouts) — `assets/ground_truth/supplementary_reference_catalog.json`
- [x] Archetype geometry profiles (zone-based) — `assets/ground_truth/archetype_geometry_profiles.json`
- [x] Preview image index (45 PNGs) — `assets/ground_truth/preview_index.json`

**Sample Inputs** (needed for: recipe testing, integration tests, benchmarks)

- [x] Legacy system navigator (test fixture) — `inputs/legacy-system-navigator.combined.md`
- [ ] Executive summary content brief
- [ ] Architecture diagram content brief (cloud data platform or similar)
- [ ] Process flow content brief (CI/CD pipeline, data onboarding, or similar)
- [ ] KPI / metrics content brief
- [ ] Comparison content brief
- [ ] Roadmap content brief
- [ ] Case study content brief
- [ ] Capability showcase content brief
- [ ] RFP response content brief
- [ ] Strategy content brief
- [ ] All sample inputs in — `inputs/`

**Runtime Dependencies** (needed for: pipeline execution)

- [x] `python-pptx` — installed in `.venv`
- [x] `pydantic` v2 — installed in `.venv`
- [x] `Pillow` — installed in `.venv` (verified: ImageFont loads all bundled fonts)
- [x] `aspose-slides` — installed in `.venv`
- [x] `libgdiplus` — installed via Homebrew (`mono-libgdiplus`)
- [x] `pytest` — installed in `.venv`

---

## 0.2) What V2 Adds

V2 introduces four capabilities that V1 lacks:

1. **Recipe engine**: deterministic, parameterized layout recipes that compute coordinates from semantic slot content. Each recipe is a Python class that owns its spatial math.
2. **Composed slide rendering**: a renderer path that places native PowerPoint primitives (shapes, text boxes, connectors, grouped constructs) at recipe-computed positions, alongside the existing placeholder-binding path.
3. **Text measurement heuristic**: font-aware estimation of text extents so the recipe engine can calculate accurate element heights before render.
4. **Bounded per-slide visual review**: review that judges broad aesthetics and content quality, with repair limited to recipe/slot adjustment — never direct coordinate manipulation.

V2 does NOT add:
- A general-purpose constraint solver or CSS-like layout engine.
- LLM-generated coordinates, bounds, or EMU values.
- SVG in the render path (source SVGs remain in catalogs; PNGs are rendered).
- Animation choreography.
- PowerPoint desktop GUI automation.

---

## 1) Core Design Decisions

### 1.1 The Recipe Is the Architecture

The central architectural decision in V2 is: **the LLM selects a recipe and fills its slots; the recipe computes all coordinates deterministically.**

A recipe is a Python class that:
- Declares a **slot schema**: the named content positions it supports (title, subtitle, N cards, connectors, footer bars, etc.) with type and cardinality constraints.
- Accepts **slot content**: text, icon concept references, accent color tokens, relationship declarations — never coordinates.
- Uses the **text measurement heuristic** to estimate rendered heights for text slots.
- Applies **design tokens** from the template for colors, fonts, spacing, and radii.
- Computes **absolute coordinates** for every element on the slide canvas.
- Handles its **own overflow**: font-size reduction within token bounds, text truncation, speaker-notes spillover, item-count clamping.
- Returns a **positioned element list** that the composed renderer consumes directly.

The LLM's output for a composed slide looks like:

```json
{
  "archetype": "executive_summary",
  "recipe_id": "exec_summary_3_cards",
  "title": "Strategic Priorities",
  "subtitle": "FY26 Focus Areas",
  "slots": [
    {
      "role": "card",
      "heading": "Revenue Growth",
      "body": "Expand enterprise accounts by 30%",
      "icon_concept": "growth",
      "accent_token": "accent_1"
    },
    {
      "role": "card",
      "heading": "Operational Excellence",
      "body": "Reduce delivery cycle time by 40%",
      "icon_concept": "efficiency",
      "accent_token": "accent_2"
    },
    {
      "role": "card",
      "heading": "Market Expansion",
      "body": "Enter 3 new verticals in APAC",
      "icon_concept": "target",
      "accent_token": "accent_3"
    }
  ],
  "footer_text": "Source: FY26 Board Strategy Document",
  "background_treatment": "surface_muted"
}
```

The recipe engine converts this to absolute positions. The LLM sees slots, not geometry.

### 1.2 Why Not a General Solver

Two independent reviewers and Anthropic's own Claude-for-PowerPoint implementation converge on the same finding: LLMs cannot reliably produce absolute coordinates for multi-element slide layouts. Claude-for-PPT defaults to uniform grids because "that's what's easiest to compute correctly without visual feedback." A general constraint solver (Cassowary/Kiwi-style) would take months to build and still lack text-extent awareness.

Recipe-driven layout trades generality for reliability. The system can only produce slides for which a recipe exists, but those slides will be spatially correct every time. The mitigation for limited recipe coverage is making recipe authoring fast (a new recipe is a single Python class following a base protocol).

### 1.3 All Slides Are Composed

Every slide in V2 goes through the recipe engine. The V1 placeholder-binding path (`template_native`) is retired for production rendering. V1 code remains in the codebase for reference and testing but is not part of the V2 pipeline.

Even simple slides (title, section break, agenda) use recipes. A `title_centered` recipe is trivial to implement — it computes positions for a title and subtitle on the template's canvas using design tokens. The benefit is uniformity: every slide flows through the same pipeline (slot fill → asset resolution → recipe execution → composed render → review), with no routing logic, no special cases, and no divergent code paths.

### 1.4 The LLM's Bounded Role

The LLM is responsible for:
- Narrative arc: deciding the deck's story structure and slide sequence.
- Archetype and recipe selection: choosing the right visual pattern for each slide's message.
- Slot content: writing the text, choosing icon concepts, selecting accent tokens.
- Deck-level variety: ensuring adjacent slides don't repeat the same recipe.

The LLM is NOT responsible for:
- Coordinate computation. The recipe engine owns all spatial math.
- Font size selection. Recipes use design tokens and adjust based on text measurement.
- Overflow handling. Recipes handle their own overflow deterministically.
- Connector routing. Each recipe that includes connectors routes them as part of its geometry.

### 1.5 Asset Routing Is a Central Contract

V1 treats icon/image resolution as a peripheral concern buried in `_resolve_asset_path`. V2 makes it a first-class pipeline stage:

1. The LLM outputs `icon_concept` references (e.g., `"security"`, `"database"`, `"aws:lambda"`).
2. The **asset resolver** maps concepts to concrete `asset_id` values using the visual vocabulary, icon index, and branded image catalog.
3. The resolver enforces diversity (no duplicate icons on the same slide) and availability (rejects concepts with no matching asset).
4. The recipe engine receives resolved `asset_id` values and embeds them at computed positions.

This contract ensures:
- The LLM never hallucinates asset paths.
- Icon diversity is enforced deterministically, not hoped for.
- The 29K icon library and visual vocabulary are fully utilized.

### 1.6 Review Judges Aesthetics, Not Pixel Alignment

The review loop is better than Claude-for-PPT's text-only feedback, but only if it is bounded and not asked to repair geometry that the deterministic layer should have prevented.

Review responsibilities:
- Content quality and message clarity.
- Visual balance and overall aesthetic judgment.
- Brand consistency and narrative coherence across slides.
- Identifying slides where the recipe choice is wrong for the content.

Review does NOT:
- Suggest coordinate adjustments.
- Micro-adjust spacing or alignment (the recipe owns that).
- Override deterministic validation results.

Repair actions the review can trigger:
- Switch to a different recipe for the same archetype.
- Adjust slot content (shorter text, different emphasis, different icon concept).
- Change accent or background token.
- Reroute to a different archetype's recipe if the current one is a poor fit.
- Flag a slide for deck-level narrative restructuring.

Repair actions the review CANNOT trigger:
- Direct coordinate changes.
- Font size overrides outside token bounds.
- Arbitrary primitive insertion outside the recipe's slot schema.

---

## 2) Non-Negotiable Constraints

### 2.1 Native PPTX Output
- Output must be `.pptx`, must open in Microsoft PowerPoint without repair prompts.
- Text, shapes, lines, connectors, tables, and charts must remain editable.
- No rasterized layout. No slides exported as embedded images.

### 2.2 Template-First Branding
- The system must accept a customer-provided branded `.pptx` template.
- Masters, layouts, theme colors, and theme fonts must be preserved.
- Composed slides inherit theme tokens and render on a blank or minimal-content template layout that preserves the template's masters and theme.

### 2.2.1 Template Canvas Configuration

The current Ascendion template has 5 masters and 118 layouts — significant bloat (Master 4 alone has 50 layouts, 39 named `1_Title slide`). V2 uses a single canonical master and a small set of canvas layouts.

**Canonical master**: Master 0 (44 layouts, contains all branded Light/Dark variants).

**Recipe canvas layouts** (from Master 0) — the blank or minimal-content layouts that composed recipes render onto:

| Canvas Layout | Master 0 Index | Use Case |
|---|---|---|
| `Header Only - Light` | 8 | Composed slides needing only a branded header bar |
| `Header Only - Dark` | 9 | Dark-themed composed slides |
| `Blank` | 36 | Full-canvas composition with no template furniture |

Other Master 0 layouts remain available for reference and token extraction but are not used as recipe canvases.

Template cleanup task: document the canonical master and canvas layouts in `assets/template/canvas_config.json`. Recipes reference canvas layouts by config key, not by hardcoded index.

### 2.3 Asset Format Policy
- Render path supports raster assets (`PNG`, `JPG`, `WebP`) only.
- Source SVGs exist in catalogs but are converted to PNG before render.
- No SVG embedding in the PowerPoint file.

### 2.4 Deterministic Safety
- All LLM outputs must be schema-validated (Pydantic).
- All coordinates are computed by recipe code, never by LLM output.
- Every run must persist artifacts under `runs/<run_id>/`.
- Rendering never executes raw LLM text as code.

### 2.5 Review Image Generation
- **Required**: Aspose.Slides (`aspose-slides` Python package) for PPTX → PDF and PPTX → PNG conversion. High fidelity; evaluation-mode watermark is acceptable because review images are intermediate artifacts.
- Requires `libgdiplus` system library (`brew install mono-libgdiplus` on macOS).
- LibreOffice is **not used**. Its rendering fidelity is too low for reliable multimodal review — font substitution, theme-color misinterpretation, and shape rendering differences cause the reviewer to flag phantom issues and miss real ones.
- The reviewer must still be instructed that review images may have minor rendering differences from PowerPoint and should not flag micro-alignment issues.

---

## 3) Recipe Engine

The recipe engine is the highest-leverage new component in V2.

### 3.1 Recipe Protocol

Every recipe must implement:

```python
class RecipeProtocol:
    recipe_id: str
    archetype: str
    slot_schema: SlotSchema       # declares expected slots and constraints
    
    def validate_input(self, slots: RecipeInput) -> list[SlotError]
    def compute_layout(self, slots: RecipeInput, tokens: DesignTokens, 
                       canvas: CanvasSpec, measure: TextMeasurer) -> PositionedElementList
```

- `validate_input`: checks that slot content meets the recipe's constraints (item count within range, text within budget, required slots present).
- `compute_layout`: deterministic function from (slot content, tokens, canvas size, text measurer) to positioned elements. No randomness, no LLM.

### 3.2 Slot Schema

Each recipe declares its slots:

```python
SlotSchema = {
    "title": {"type": "text", "required": True, "max_chars": 80},
    "cards": {"type": "card_list", "min_items": 2, "max_items": 5,
              "card_fields": {
                  "heading": {"max_chars": 40},
                  "body": {"max_chars": 120},
                  "icon_concept": {"required": False},
                  "accent_token": {"required": False}
              }},
    "footer_text": {"type": "text", "required": False, "max_chars": 100},
    "background_treatment": {"type": "token_ref", "required": False}
}
```

The LLM sees the slot schema as part of the recipe catalog and fills it accordingly.

### 3.3 Positioned Element List

The recipe's output is a flat list of positioned elements:

```python
PositionedElement:
    element_id: str
    primitive: PrimitiveType       # text_box, shape_rect, shape_round_rect, connector, image, group, ...
    bounds: Bounds                 # {left, top, width, height} in inches
    z_index: int
    content: ElementContent        # text, image path, shape fill, etc.
    style: ElementStyle            # resolved token values: font, size, color, fill, stroke, radius
```

This list is the contract between the recipe engine and the composed renderer.

### 3.4 Initial Recipe Library

MVP targets 12 archetypes. Each archetype ships with 2-3 recipe variants for visual variety.

| Archetype | Recipe Variants | Notes |
|---|---|---|
| `title_hero` | `title_centered`, `title_with_subtitle_bar` | Simple recipe; few elements but still composed for pipeline uniformity |
| `section_break` | `section_dark_bg`, `section_with_image` | Branded image overlay or dark-background treatment |
| `executive_summary` | `exec_3_cards`, `exec_4_cards`, `exec_split_hero`, `exec_icon_grid` | Primary proof-of-concept archetype |
| `process_flow` | `process_horizontal_stepper`, `process_vertical_flow` | Requires connectors within the recipe |
| `architecture_diagram` | `arch_layered_stack`, `arch_data_pipeline`, `arch_hub_spoke` | Differentiator; uses AWS/Azure/GCP cloud icons |
| `comparison` | `comparison_2_col`, `comparison_matrix` | Side-by-side or grid |
| `kpi_snapshot` | `kpi_metric_cards`, `kpi_dashboard_row` | Metric callouts with accent bars |
| `roadmap` | `roadmap_horizontal_phases`, `roadmap_swimlane` | Timeline/phase layouts |
| `case_study` | `case_study_problem_solution`, `case_study_narrative` | Client story: challenge → approach → outcome, with metrics and logo |
| `capability_showcase` | `capability_icon_grid`, `capability_pillar_cards` | Service/capability overview with icon-label cells or pillar cards |
| `rfp_template` | `rfp_response_section`, `rfp_compliance_matrix` | Structured response with requirement mapping, compliance indicators |
| `strategy` | `strategy_pillars`, `strategy_horizon_map` | Strategic framework with pillars/themes or time-horizon phasing |

Additional archetypes (`problem_statement`, `current_vs_target`, `decision_next_steps`) may be added post-MVP by authoring new recipe classes.

### 3.5 Architecture Diagram Recipes (First-Class)

Architecture diagrams are the highest-value composed slide type. They are also the hardest because they involve:
- Multiple labeled nodes arranged in spatial groups.
- Icons from the cloud service icon library (AWS, Azure, etc.).
- Connectors routed between nodes.
- Container zones (dashed borders, background fills).
- Cross-cutting bars (governance, monitoring, security).

Each architecture recipe handles this complexity internally:

**`arch_layered_stack`**: N horizontal tiers, each containing M service nodes. Connectors flow vertically between tiers. Optional cross-cutting side bars.

**`arch_data_pipeline`**: Left-to-right flow from source systems through ingestion, medallion zones (bronze/silver/gold), to consumers. Nodes grouped in vertical columns within each zone. Uses the data/analytics icons from the visual vocabulary.

**`arch_hub_spoke`**: Central hub node with N radiating spoke nodes. Connectors from hub to each spoke. Good for integration patterns, API gateways, event-driven architectures.

The slot input for an architecture recipe looks like:

```json
{
  "recipe_id": "arch_data_pipeline",
  "title": "Enterprise Data Platform",
  "zones": [
    {
      "zone_id": "sources",
      "label": "Source Systems",
      "position": "left",
      "nodes": [
        {"label": "SAP ERP", "icon_concept": "database"},
        {"label": "Salesforce", "icon_concept": "cloud"},
        {"label": "IoT Streams", "icon_concept": "streaming"}
      ]
    },
    {
      "zone_id": "lakehouse",
      "label": "Medallion Lakehouse",
      "position": "center",
      "sub_zones": ["Bronze", "Silver", "Gold"],
      "nodes_per_sub": [
        [{"label": "Raw Store", "icon_concept": "database"}],
        [{"label": "Curated", "icon_concept": "transform"}],
        [{"label": "Business", "icon_concept": "analytics"}]
      ]
    },
    {
      "zone_id": "consumers",
      "label": "Consumption",
      "position": "right",
      "nodes": [
        {"label": "Power BI", "icon_concept": "chart"},
        {"label": "ML Models", "icon_concept": "ai"}
      ]
    }
  ],
  "cross_cutting_bars": [
    {"label": "Governance & Security", "icon_concepts": ["security", "compliance"]},
    {"label": "Monitoring & Ops", "icon_concepts": ["monitoring", "alerting"]}
  ],
  "flows": [
    {"from": "sources", "to": "lakehouse", "style": "solid"},
    {"from": "lakehouse", "to": "consumers", "style": "solid"}
  ]
}
```

The recipe computes zone widths, node positions within zones, connector routing between zones, and cross-cutting bar placement. All spatial math is deterministic and specific to this recipe's geometry.

### 3.6 Connector Routing (Per-Recipe, Not General)

Connector routing is NOT a general graph-layout problem in this architecture. Each recipe that uses connectors defines its own routing logic:

- `process_horizontal_stepper`: straight horizontal connectors between step boxes, with arrowheads. Trivial routing.
- `arch_layered_stack`: vertical connectors between tier rows, anchored at node center-bottom to next-tier node center-top.
- `arch_data_pipeline`: horizontal connectors between zone boundaries, routed at zone midpoints.
- `arch_hub_spoke`: radial connectors from hub center to spoke node edges.

Each recipe knows its geometry and routes connectors accordingly. There is no general connector-routing algorithm to build.

---

## 4) Text Measurement Heuristic

### 4.1 The Problem

`python-pptx` has no font-shaping engine. It cannot compute how tall a block of wrapped text will be at a given font size and box width. Without this, the recipe engine cannot compute accurate Y-offsets for stacked elements, and `no_object_collisions` is unmeasurable.

### 4.2 The Solution

Build a lightweight text measurement module using Pillow's `ImageFont`:

```python
class TextMeasurer:
    def estimate_text_height(self, text: str, font_name: str, 
                             font_size_pt: float, box_width_in: float) -> float:
        """Returns estimated rendered height in inches."""
    
    def estimate_line_count(self, text: str, font_name: str,
                            font_size_pt: float, box_width_in: float) -> int:
        """Returns estimated number of wrapped lines."""
```

Implementation:
- Load the template's font files (TTF/OTF) or fall back to a metrics-compatible substitute.
- Use `ImageFont.getbbox()` or `font.getlength()` to measure character widths.
- Simulate line-wrapping by word-boundary splitting against the box width.
- Multiply line count by (font_size + line_spacing) for height.
- Apply a conservative 15-20% padding factor to account for PowerPoint's internal rendering differences.

This will not be pixel-perfect. It does not need to be. It needs to be close enough that:
- Stacked elements don't overlap.
- Overflow detection catches genuine overflows before render.
- The review loop does not waste cycles on layout bugs that measurement could have prevented.

### 4.3 Font Strategy

The template uses fonts that are not embedded in the PPTX and are not universally installed. The project bundles metrically compatible Google Font alternatives under `assets/fonts/`.

| Template Font | Role | Google Font Substitute | Rationale |
|---|---|---|---|
| PP Neue Machina Plain | Headings in template shapes | **Space Grotesk** | Same geometric ink-trap aesthetic and futuristic feel |
| Aptos | Body text in template shapes | **Inter** | Modern, highly legible grotesque sans-serif matching Aptos's neutrality |
| Calibri | Theme body font | **Carlito** | Metrically compatible replacement with identical proportions |
| Calibri Light | Theme heading font | **Lato Light (300)** | Similar elegant thin profile with rounded details |

Font files are stored at `assets/fonts/` with a machine-readable mapping in `assets/fonts/font_map.json`:
```
assets/fonts/
  font_map.json                # template font → substitute mapping
  SpaceGrotesk-Regular.ttf
  SpaceGrotesk-Bold.ttf
  SpaceGrotesk-Light.ttf
  Inter-Regular.ttf
  Inter-Bold.ttf
  Inter-Italic.ttf
  Inter-BoldItalic.ttf
  Carlito-Regular.ttf
  Carlito-Bold.ttf
  Carlito-Italic.ttf
  Carlito-BoldItalic.ttf
  Lato-Light.ttf
  Lato-LightItalic.ttf
  Lato-Regular.ttf
  Lato-Bold.ttf
```

The text measurer loads fonts in this order:
1. Template's original font if installed on the system (PP Neue Machina, Aptos, Calibri).
2. Bundled substitute from `assets/fonts/` using the mapping above.
3. Conservative fixed estimate (assume widest glyphs) if neither is available. This path logs a warning.

The font mapping is also used by Aspose during review-image export: if the original fonts are missing, Aspose substitutes similarly, so the bundled fonts keep measurement and review rendering consistent with each other even if neither matches PowerPoint's rendering exactly.

---

## 5) Design Tokens

### 5.1 Token Extraction

The system extracts design tokens from the template and persists them per run. Tokens are consumed by recipes and the composed renderer.

Token families:

**Typography roles:**
- `display`, `h1`, `h2`, `h3`, `body`, `caption`, `footnote`
- Each role specifies: font family, font size (pt), bold/italic, line spacing, color token.

**Color roles:**
- `bg_primary`, `bg_secondary`, `surface`, `surface_muted`
- `text_primary`, `text_secondary`
- `accent_1` through `accent_5`
- `success`, `warning`, `risk`

**Spacing scale:** `xs` (0.05"), `sm` (0.1"), `md` (0.2"), `lg` (0.35"), `xl` (0.5")

**Stroke scale:** `hairline` (0.5pt), `thin` (1pt), `standard` (1.5pt), `emphasis` (2.5pt)

**Radius scale:** `none` (0), `sm` (0.05"), `md` (0.1"), `pill` (50%)

### 5.2 Token Extraction Realism

Corporate templates are messy. Theme colors may be hardcoded RGB, font mappings may be inconsistent, layouts may violate their own patterns. The token extractor must:

- Extract what the theme provides cleanly (theme colors, theme fonts).
- For semantic roles not directly expressed in the theme (e.g., `surface_muted`, `accent_3`), apply heuristic mapping from the theme's color palette.
- Persist a `token_confidence` flag per token indicating whether it was directly extracted or heuristically mapped.
- Allow manual token overrides via a `token_overrides.json` file per template.

Required artifact per run: `runs/<run_id>/design_tokens.json`

---

## 6) Composed Renderer

### 6.1 Responsibilities

The composed renderer takes a `PositionedElementList` from the recipe engine and produces native PowerPoint objects using `python-pptx`.

### 6.2 Supported Primitives

| Primitive | python-pptx API | Notes |
|---|---|---|
| `text_box` | `slide.shapes.add_textbox()` | Free-positioned text with token-styled runs |
| `shape_rect` | `slide.shapes.add_shape(MSO_SHAPE.RECTANGLE)` | With fill, stroke, radius from tokens |
| `shape_round_rect` | `slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE)` | Primary card shape |
| `shape_circle` | `slide.shapes.add_shape(MSO_SHAPE.OVAL)` | Hub nodes, status indicators |
| `shape_chevron` | `slide.shapes.add_shape(MSO_SHAPE.CHEVRON)` | Process step indicators |
| `shape_arrow` | `slide.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW)` | Directional flow indicators |
| `connector_straight` | `slide.shapes.add_connector()` | Between-node connections |
| `connector_elbow` | OOXML bridge | Routed connections |
| `image` | `slide.shapes.add_picture()` | Icons and branded images |
| `table` | `slide.shapes.add_table()` | Structured data |
| `chart_bar` / `chart_column` / `chart_line` / `chart_pie` | `slide.shapes.add_chart()` | Native charts with data series |
| `group` | OOXML bridge | Grouped constructs for editability |
| `accent_bar` | Thin `shape_rect` | Visual separator/emphasis lines |

### 6.3 OOXML Bridge

The OOXML bridge handles features that `python-pptx` cannot express through its public API:
- Elbow and curved connectors with routed waypoints.
- Shape grouping (critical for editability of complex constructs).
- Gradient fills on shapes (partial `python-pptx` support).
- Shadow and glow effects where recipes explicitly request them.

Bridge rules:
- Every bridge helper must have a unit test that asserts the output XML structure.
- Bridge helpers are called by the composed renderer, not by recipes or the LLM.
- Bridge scope will grow over time. This is accepted. The containment strategy is: bridge helpers are isolated functions, not a parallel renderer.

### 6.4 Background Rendering

Background treatment is part of the recipe's positioned element list. Allowed treatments:
- Template-native background (use the selected layout's existing background).
- Theme solid fill (`bg_primary`, `bg_secondary`, `surface`, `surface_muted`).
- Branded hero image (resolved from `branded_images.json`).
- Light accent wash (semi-transparent shape covering the slide canvas).

Every background treatment must preserve text contrast. The recipe is responsible for selecting text colors that work against its background.

---

## 7) AI Layer

### 7.1 Model Roles

| Role | Responsibility | Required Capability |
|---|---|---|
| `deck_planner` | Narrative arc, slide roster, archetype assignment, recipe selection | Strong structured output |
| `slide_filler` | Per-slide slot content given archetype, recipe, and brief | Structured output, domain knowledge |
| `visual_reviewer` | Per-slide aesthetic and content judgment from rendered image | Multimodal (image + text) |
| `repair_planner` | Recipe/slot adjustments from review findings | Structured output |

The same model family may serve multiple roles. Prompts, schemas, and context bundles remain role-specific.

### 7.2 Provider Strategy

- Primary target: strongest available model with structured output and multimodal support (currently GPT-4o / Claude / Gemini families).
- The architecture must not be coupled to a single provider. The existing `LLMClient` abstraction is retained.
- Provider-specific features (native Skills, tool use) are optional enhancements, not required for the core pipeline.

### 7.3 Planning Workflow

**Pass 0 — Intake**
- Normalize user content and visualization cues (existing V1 code).
- Load template inspection and design tokens.
- Load recipe catalog.
- Load asset catalogs.

Artifacts: `normalized_content.json`, `design_tokens.json`, `recipe_catalog_snapshot.json`

**Pass 1 — Deck Blueprint**
The deck planner determines:
- Deck objective and audience.
- Narrative arc and slide roster.
- Per-slide: archetype, recommended recipe candidates.
- Deck-level variety constraints: no more than 2 consecutive slides with the same recipe; at least 3 distinct recipes across any 5-slide window.

Artifact: `deck_blueprint_v1.json`

**Pass 2 — Slot Filling**
Each slide receives its recipe's slot schema and a content brief. The slide filler produces:
- Slot content matching the recipe's schema.
- Icon concept references (not asset IDs — the resolver handles that).
- Accent token selections.
- Background treatment selection.

Artifact: `slide_slots_v1/<slide_id>.json`

**Pass 3 — Asset Resolution**
Deterministic, no LLM:
- Map `icon_concept` values to concrete `asset_id` values via visual vocabulary and icon index.
- Enforce per-slide icon diversity (no duplicate asset_id on the same slide).
- Resolve branded images for backgrounds.
- Validate all assets exist on disk.

Artifact: `asset_resolution_v1.json`

**Pass 4 — Recipe Execution**
Deterministic, no LLM:
- For each slide: call the recipe's `compute_layout()` with resolved slots, tokens, canvas spec, and text measurer.
- Run deterministic validation on positioned elements: bounds within canvas, no overlaps, text within budget.

Artifacts: `positioned_elements_v1/<slide_id>.json`, `layout_validation_v1.json`

**Pass 5 — Render**
- All slides rendered by the composed renderer consuming positioned element lists.

Artifact: `deck_v1.pptx`

**Pass 6 — Review and Repair**
- Export slides to images via Aspose.Slides.
- Per-slide multimodal review: content quality, visual balance, brand fit, archetype fit.
- Repair planner produces: recipe switch, slot content adjustment, accent/background change, or accept.
- Re-execute passes 3-5 for repaired slides only.

Artifacts: `review_images/v1/`, `visual_review_v1/<slide_id>.json`, `repair_actions_v1.json`, `deck_v2.pptx`

### 7.4 Review Loop Bounds

Hard constraints on the review-repair loop:
- **Maximum 2 iterations total.** Iteration 1: render V1 → review → repair → render V2. Iteration 2 (only for slides still blocking after iteration 1): review V2 → repair → render V3.
- **No coordinate-level repair.** Repair actions are: switch recipe, adjust slot content, change tokens, reroute. Never "move element X by 0.3 inches."
- **Score-delta threshold.** If the reviewer scores a repaired slide within 0.5 points of its pre-repair score, stop iterating on that slide and accept.
- **Graceful degradation.** If a slide fails review after 2 iterations, accept with warnings and log the unresolved findings. Do not block the run.
- **Cost cap.** Total LLM calls per deck generation must not exceed: 3 + (2 * slide_count) calls. For a 10-slide deck, that's 23 calls max (1 blueprint + 10 slot fills + 10 reviews + 2 repair replans). Actual count will usually be lower because not all slides need repair.

### 7.5 LLM Output Schemas

All LLM outputs are Pydantic-validated. Key schemas:

**DeckBlueprint:**
- `deck_objective`, `audience`, `narrative_arc`
- `slides[]`: `slide_id`, `archetype`, `recipe_candidates[]`, `route`, `content_brief`, `variety_notes`

**SlideSlotFill (per recipe):**
- Must conform to the specific recipe's `SlotSchema`.
- Common fields: `title`, `background_treatment`
- Recipe-specific fields: `cards[]`, `steps[]`, `zones[]`, `metrics[]`, etc.

**ReviewVerdict (per slide):**
- `slide_id`, `decision` (accept | minor_repair | major_replan | reroute)
- `content_score`, `visual_balance_score`, `brand_fit_score` (1-5 each)
- `findings[]`: `category`, `description`, `severity`
- `repair_suggestion`: `action` (switch_recipe | adjust_slots | change_tokens | reroute), `details`

---

## 8) Deterministic Validation

### 8.1 Pre-Render Validation (Positioned Elements)

After recipe execution and before render:
- **Bounds check**: every element fits within slide canvas (13.333" x 7.5" standard).
- **Overlap detection**: no two elements overlap by more than a configurable tolerance (default: 0.02").
- **Text budget**: estimated text height (from text measurer) fits within element's allocated height.
- **Asset availability**: every `asset_id` in the positioned elements has a corresponding file on disk.
- **Token compliance**: every color, font, and spacing value traces back to a design token.

### 8.2 Post-Render Validation (PPTX Diagnostics)

After render, the existing diagnose script checks:
- Rendered shape count matches positioned element count.
- No text overflow flags in PowerPoint's XML.
- Image references resolve correctly.
- Layout drift between planned and rendered positions.

### 8.3 Quality Gates (Final Deck)

Retained from V1 with additions:
- `native_pptx_opens`: file is valid PPTX.
- `no_blocking_overflow`: no text overflow after measurement and remediation.
- `no_object_collisions`: overlap check passes for all composed slides.
- `token_compliance`: all styled elements use token values.
- `brand_template_compliance`: template theme is preserved.
- `reviewed_all_slides`: every slide was reviewed.
- `visual_density_floor`: minimum number of non-text elements per slide (for composed slides).
- `asset_diversity_floor`: no duplicate icon on the same slide.
- `deck_variety_floor`: recipe repetition within bounds.
- `no_markdown_marker_leak`: no literal `**` or `*` in rendered text.

---

## 9) Artifacts and Logging

### 9.1 Run Artifacts

All artifacts persisted under `runs/<run_id>/`:

| Artifact | Stage | Format |
|---|---|---|
| `normalized_content.json` | Pass 0 | Content model |
| `design_tokens.json` | Pass 0 | Extracted tokens |
| `recipe_catalog_snapshot.json` | Pass 0 | Available recipes and slot schemas |
| `deck_blueprint_v1.json` | Pass 1 | Deck plan with archetype/recipe assignments |
| `slide_slots_v1/<slide_id>.json` | Pass 2 | Filled slot content per slide |
| `asset_resolution_v1.json` | Pass 3 | Concept-to-asset mapping |
| `positioned_elements_v1/<slide_id>.json` | Pass 4 | Recipe output |
| `layout_validation_v1.json` | Pass 4 | Pre-render validation |
| `deck_v1.pptx` | Pass 5 | Rendered deck |
| `review_images/v1/slide_*.png` | Pass 6 | Exported slide images |
| `visual_review_v1/<slide_id>.json` | Pass 6 | Review verdicts |
| `repair_actions_v1.json` | Pass 6 | Repair plan |
| `deck_v2.pptx` | Pass 6 | Repaired deck |
| `quality_gates_v2.json` | Final | Gate results |
| `run_summary.json` | Final | Aggregate metrics and deltas |
| `run_log.jsonl` | Throughout | Structured event log |

### 9.2 Log Markers

`NORMALIZE_DONE`, `TOKENS_EXTRACTED`, `BLUEPRINT_DONE`, `SLOT_FILL_DONE`, `ASSET_RESOLUTION_DONE`, `RECIPE_EXECUTION_DONE`, `LAYOUT_VALIDATION_DONE`, `RENDER_V1_DONE`, `REVIEW_IMAGES_EXPORTED`, `VISUAL_REVIEW_DONE`, `REPAIR_PLANNED`, `RENDER_V2_DONE`, `QUALITY_GATES`, `RUN_COMPLETE`, `RUN_FAILED_QUALITY_GATES`

---

## 10) Runtime Tech Stack

### 10.1 Core
- Python 3.11+
- `python-pptx` (rendering)
- `pydantic` v2 (schema validation)
- `Pillow` (text measurement)
- `orjson` (fast JSON)
- `pytest` (testing)

### 10.2 Review Toolchain
- `aspose-slides` Python package (PPTX → PDF/PNG, high fidelity)
- System dependency: `libgdiplus` (`brew install mono-libgdiplus` on macOS)

### 10.3 AI Runtime
- LLM client abstraction supporting multiple providers (existing)
- Structured output via JSON schema enforcement
- Multimodal image input for visual review

### 10.4 CLI (First Delivery Surface)
- Retained commands: `validate`, `render`, `smoke`, `generate`, `generate-auto`
- New commands: `inspect-template` (emit tokens), `list-recipes` (show available recipes), `generate-slide` (single composed slide for testing)

### 10.5 Local Web UI (Second Delivery Surface)
- FastAPI backend exposing the same pipeline
- Simple frontend: paste content, pick template, generate, preview slides, trigger per-slide repair, download deck
- Deferred to post-MVP

---

## 11) Testing Strategy

### 11.1 Recipe Tests (New)
- Each recipe must have unit tests that verify:
  - Slot validation rejects invalid input.
  - `compute_layout()` produces non-overlapping elements for fixture input.
  - Element bounds stay within canvas.
  - Text measurement is called and results influence element heights.
  - Varying slot counts produce different but valid layouts.

### 11.2 Text Measurer Tests (New)
- Known font + known text + known box width → expected line count within tolerance.
- Fallback font path works when primary font is missing.
- Edge cases: empty text, single character, very long word.

### 11.3 Composed Renderer Tests (New)
- Positioned element list → PPTX → re-read shape positions and verify bounds match.
- OOXML bridge helpers produce valid XML.
- Grouped constructs remain grouped in output.

### 11.4 Retained V1 Tests
- All existing 18 test files remain. V2 does not break the V1 path.
- Template validation, preflight, drift, quality gates, normalization, LLM client mocks.

### 11.5 Integration Tests
- One-slide composed render from hardcoded recipe input → PPTX.
- One-slide end-to-end: prompt → LLM blueprint → slot fill → recipe → render → PPTX.
- Multi-slide deck with diverse recipes.
- Review loop: render → export → review → repair → re-render.

### 11.6 No Pixel-Perfect Tests
- Structural and metric assertions only: element counts, overlap detection, bounds compliance, token usage.
- No screenshot comparison. No visual regression baselines.

---

## 12) Build Sequence (Vertical Slices)

### Slice 0: Recipe Engine Proof (First Milestone)

**Goal**: One recipe renders a real composed slide from hardcoded input.

Build:
- `TextMeasurer` module with Pillow.
- `DesignTokens` extraction from template (simplified: theme colors + fonts).
- `RecipeProtocol` base class.
- `exec_summary_3_cards` recipe implementation.
- Composed renderer that consumes `PositionedElementList` and produces shapes via `python-pptx`.
- Hardcoded slot input → recipe → render → PPTX.

Demo: One rendered, editable executive summary slide with 3 styled cards, icons, and a title.

Exit criteria: Slide opens in PowerPoint. Shapes are editable. No overlap. Icons render correctly.

### Slice 1: LLM Planning → Recipe Selection

**Goal**: LLM picks a recipe and fills its slots from a prompt.

Build:
- Recipe catalog manifest (JSON listing all recipes, their slot schemas, and archetype associations).
- Deck blueprint schema and LLM prompt.
- Slot-fill schema and LLM prompt.
- Asset resolution pipeline (concept → asset_id).
- 2-3 additional recipes: `exec_icon_grid`, `kpi_metric_cards`, `process_horizontal_stepper`.

Demo: CLI prompt → LLM selects archetype and recipe → fills slots → recipe computes layout → rendered PPTX.

### Slice 2: Architecture Diagram Recipes

**Goal**: Prove the architecture diagram differentiator.

Build:
- `arch_layered_stack` recipe.
- `arch_data_pipeline` recipe.
- Icon routing for AWS/cloud service icons.
- Per-recipe connector routing.

Demo: "Design a data lakehouse architecture" → branded architecture slide with real service icons and routed connectors.

### Slice 3: Review and Repair Loop

**Goal**: Close the quality loop.

Build:
- Per-slide review packet generation.
- Multimodal review with bounded repair actions.
- Repair planner (recipe switch / slot adjustment).
- Re-execution of passes 3-5 for repaired slides.
- Hard iteration cap enforcement.

Demo: Generate → review → repair → measurably improved slide.

### Slice 4: Multi-Slide Deck with Variety

**Goal**: Coherent deck from a single prompt.

Build:
- Deck-level planner with variety constraints.
- Multiple archetypes and recipes in one deck.
- Neighbor-aware recipe selection.
- 5-6 archetypes functional.

Demo: Single prompt → 5-8 slide deck with visual variety and narrative coherence.

### Slice 5: Polish, Web UI, Benchmarks

Build:
- Recipe library expansion (more variants per archetype).
- Local web UI.
- Benchmark gating and quality thresholds.
- Template compatibility validation.

---

## 13) Out of Scope

- Full WYSIWYG canvas parity with PowerPoint.
- Animation choreography.
- General-purpose constraint solver or CSS-like responsive layout.
- LLM-generated coordinates or spatial values.
- SVG embedding in the render path.
- PowerPoint desktop automation.
- Cloud-hosted endpoint (deferred past MVP).
- Advanced chart types beyond basic bar/column/line/pie.

---

## 14) Success Criteria

The architecture is successful when:
1. One composed slide renders from prompt to reviewed, repaired, editable PPTX.
2. At least 5 archetypes render through the composed path with recipe-driven layouts.
3. A 10-slide deck passes quality gates with zero blocking overlap.
4. Architecture diagram slides render with real cloud service icons and routed connectors.
5. Review-driven repair measurably improves slide quality within 2 iterations.
6. Template swap changes branding without code changes.
7. The same backend works through CLI and local web UI.
8. Adding a new recipe is a single Python class plus slot schema — no changes to the engine.
