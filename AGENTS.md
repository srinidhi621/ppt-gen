# AGENTS.md — Operating Guide (LLM-Assisted PPTX Generator)

This repo builds a PPTX generator using:
- **python-pptx** for rendering
- **PowerPoint template-first** approach (masters + curated layouts)
- **LLM-assisted planning** constrained to a layout catalog and a curated visual vocabulary
- **Hard preflight validation** to prevent overflow (no "auto-layout" assumptions)
- **A large asset library** (28,926 PNG icons across 5 packs + 71 branded images) connected to the planner via semantic catalogs

Agent: follow this guide strictly. Do not invent new architecture or deviate from contracts without updating SPEC.md.

## Agent Policies (Repo-wide)
- **No new Markdown for reviews/analysis:** Do not create new `.md` files for reviews, analysis, or reports unless the user explicitly asks. Prefer updating existing docs (`SPEC.md`, `PLAN.md`, `README.md`) when requested, or writing structured artifacts under `runs/<run_id>/` (e.g., JSON) as part of the pipeline.
- **No new dependencies without approval:** Do not add or install new third-party libraries (e.g., `pip install`, adding to `requirements.txt`) unless the user explicitly approves. Prefer Python stdlib and existing dependencies first; if a new library would materially help, propose it and wait for approval.

---

## 0) Primary Artifacts (Source of Truth)
You must keep these consistent:
- `SPEC.md` — full specification and contracts
- `PLAN.md` — execution plan and next steps
- `assets/` — canonical asset root (lowercase). If a legacy `Assets/` directory exists, treat it as transitional; new work must standardize on `assets/`.
- `assets/template/template.pptx` — corporate template (masters + layouts)
- `assets/layout/layout_catalog.json` — allowed layouts + fields + fit budgets
- `assets/icons/icons.json` — icon metadata (30,700+ entries across internal + external packs)
- `assets/catalog/asset_catalog.json` — unified asset catalog (icons + images, 30,771 entries)
- `assets/catalog/visual_vocabulary.json` — curated concept-to-icon mapping (~200-300 concepts)
- `assets/catalog/branded_images.json` — Dimensional Keyword illustrations mapped to slide themes
- `inputs/` — content inputs (combined markdown preferred)
- `runs/<run_id>/` — run outputs and logs

---

## 1) Non-Negotiable Constraints
### 1.1 The "Auto-Layout Myth"
`python-pptx` does not behave like the PowerPoint UI. It will not auto-fit text.
**Therefore: Preflight validation must prevent overflow before rendering.**

### 1.2 Template-first Rendering
Theme fidelity is achieved by using the PowerPoint template's:
- masters
- layouts
- placeholder formatting

**Do not manually style fonts/colors** unless explicitly required and documented.

### 1.3 Placeholder Binding via Alt-Text (`field_key`)
The template placeholders must have Alt-Text Description set to a canonical `field_key` (e.g., `ph_title`, `ph_body_left`).
**Renderer populates placeholders by matching `shape.alt_text` to `field_key`.**

Do not rely on placeholder indexes. That is brittle.

### 1.4 Icons: PNG Only
Use high-resolution PNG icons. Do not implement SVG handling in the render path. SVG conversion to PNG happens offline via `scripts/convert_svg_to_png.py`.

### 1.5 macOS Export Automation is Deferred
Slide image export is manual (PowerPoint UI). Do not implement AppleScript automation unless explicitly asked.

### 1.6 Markdown Formatting Must Not Leak into Slides
The renderer must parse Markdown inline formatting (`**bold**`, `*italic*`) and apply proper python-pptx text run formatting (bold/italic font properties). Raw Markdown markers must never appear as literal text in the rendered PPTX.

---

## 2) Current State (What Is Built)

### Working Infrastructure
- Template hardened with alt-text placeholders.
- Layout catalog: 12 MVP layouts with fit constraints.
- Deterministic renderer: DeckIR → PPTX via alt-text binding.
- Template drift validation (startup gate).
- Preflight validation + remediation (pressure valve, bullet trimming).
- Markdown parser: `content.md` → `ContentModel` with stable section IDs.
- Combined markdown splitter: `## Content` + `## Visualization Cues` → content + cues.
- CLI: `validate`, `render`, `smoke`, `generate`.
- LLM integration: provider-agnostic client (Gemini live, Azure OpenAI adapter), `--planner llm`, bounded retries, per-run telemetry (tokens + cost in USD/INR).
- Pydantic schemas for all contracts.
- 65 tests passing.

### Asset Library (large, partially connected)
- **28,926 PNG icons** across 5 packs:
  - 213 Ascendion branded icons (`assets/icons/png/icon_*.png`) — converted from SVG, currently **no semantic tags** (`quality: low`).
  - 19,401 Fluent UI icons (`assets/icons/png/external/fluent/`).
  - 5,928 Tabler icons (`assets/icons/png/external/tabler/`).
  - 1,542 Lucide icons (`assets/icons/png/external/lucide/`).
  - 1,842 AWS architecture icons (`assets/icons/png/external/aws/`).
- **71 branded images**: Ascendion logos + 12 "Dimensional Keyword" illustration sets (`assets/Icons and Dimensional Keywords/`), each in 5 color variants (Purple, Teal, Pink, Yellow, White):
  - Break Barriers, Build Next Dimension, Challenge Assumptions, Liberate Innovation, Outmaneuver Risk, Progress Isn't Straight, See Differently, Software To Power Growth, The Future Is What You Engineer, Transform Reality, Unlock New Possibilities, A New Perspective.
- Asset catalog exists (`assets/catalog/asset_catalog.json`, 30,771 entries).
- Token-overlap matcher exists (`match_asset()` in `src/assets.py`).

### Known Quality Gaps (see PLAN.md for details)
- The LLM planner receives raw icon IDs it cannot reason about → most slides get no visuals.
- Cues (`icon_hints`, `image_hint`) from combined markdown may not reach the planner.
- Branded Dimensional Keyword images are unused.
- 213 internal branded icons have no semantic metadata.
- Markdown bold/italic markers render as literal asterisks in PPTX.

---

## 3) Repository Conventions
### 3.1 Paths
- Templates: `assets/template/template.pptx`
- Layout catalog: `assets/layout/layout_catalog.json`
- Icons: `assets/icons/png/` and `assets/icons/icons.json`
- External icon packs: `assets/icons/png/external/{aws,fluent,lucide,tabler}/`
- External pack manifests: `assets/external_assets/{pack}/manifest.json`
- Branded images: `assets/Icons and Dimensional Keywords/`
- Unified asset catalog: `assets/catalog/asset_catalog.json`
- Visual vocabulary: `assets/catalog/visual_vocabulary.json`
- Branded image catalog: `assets/catalog/branded_images.json`
- Inputs: `inputs/`
- Outputs: `runs/<run_id>/` (do not introduce `output/` directories or conventions)
- Manual slide images: `review_images/<run_id>/`

### 3.2 Run ID
A run ID is required for every execution (timestamp-based is fine).
All run artifacts must be stored under `runs/<run_id>/`.

### 3.3 Output artifacts per run
At minimum:
- `deckir_v1.json`
- `deckir_v1_1.json` (after preflight)
- `deck_v1.pptx`
- `render_map.json`
- `run_log.jsonl`

When LLM planner is used:
- `llm_usage.json`
- `content.md` (split from combined input)
- `cues.json` (split from combined input)

If review loop is executed:
- `critique_report.json`
- `patch_set.json`
- `deckir_v2.json`
- `deck_v2.pptx`

### 3.4 Python Environment
- Virtual environment: `.venv/` (project-local)
- Activate before running scripts:
  ```bash
  source .venv/bin/activate
  ```
- For SVG conversion (requires librsvg):
  ```bash
  DYLD_LIBRARY_PATH=/opt/homebrew/lib python scripts/convert_svg_to_png.py
  ```

---

## 4) Architecture Layers

### Layer 0 — Config
- Load config including template paths, model config, defaults.

### Layer 1 — Normalize (`content.md` → ContentModel)
- Parse Markdown into stable section/bullet structure with stable IDs.
- Produce a `source_hash`.

### Layer 2 — Plan (LLM or deterministic → DeckIR v1)
- Planner must produce schema-valid DeckIR.
- DeckIR must only include:
  - allowed `layout_id`s from `layout_catalog.json`
  - allowed field keys per layout
  - visual references resolvable via the visual vocabulary or branded image catalog

#### Layer 2.1 — Visual Vocabulary (concept-to-icon resolution)
The LLM planner must NOT receive raw icon IDs. Instead:
1. The **visual vocabulary** (`assets/catalog/visual_vocabulary.json`) maps ~200-300 human concepts (e.g., `security`, `analytics`, `timeline`, `cloud`) to specific icon picks per pack, with a `preferred` icon and `alt` options.
2. The LLM selects **concepts** (not icon IDs) in its DeckIR output.
3. A **deterministic resolver** maps concepts → actual `icon_id`s using the vocabulary, then validates paths exist and are renderable PNGs.

Icon pack style guidance for vocabulary curation:
- **Lucide**: minimal line icons, cleanest aesthetic → default `preferred` for most concepts.
- **Tabler**: versatile general-purpose line icons → good alternatives.
- **Fluent UI**: Microsoft-style filled/outlined icons → good for enterprise/productivity contexts.
- **AWS**: cloud architecture diagrams → use only for explicitly cloud/infra concepts.
- **Ascendion branded (icon_*.png)**: use when tags indicate a match and brand presence is desired.

#### Layer 2.2 — Branded Image Resolution
The **branded image catalog** (`assets/catalog/branded_images.json`) maps Dimensional Keyword illustration sets to slide themes:
- Each set has a `theme` (e.g., "modernization, digital transformation"), `use_on` (layout types), and `color_preference` per theme variant.
- The planner selects a branded image by theme for hero/section/title slides.
- The resolver maps to a specific file path based on theme + color preference.

#### Layer 2.3 — Post-Planning Visual Fill (safety net)
After the planner emits a DeckIR, a deterministic sweep ensures:
- Every slide whose layout has `ph_image` but no `asset_refs` gets a visual:
  1. Resolve from cues (`icon_hints`, `image_hint`) via vocabulary/branded catalog.
  2. Fall back to content keyword extraction → vocabulary lookup.
  3. For `section_break_light` / `title_image_light` with no match → pick a branded image by content-theme similarity.
- Log every unresolved visual as `VISUAL_CUE_UNRESOLVED`.

### Layer 3 — Validate + Remediate (DeckIR v1 → v1.1)
Hard fit heuristics per layout:
- `max_title_chars`
- `max_bullets`
- `max_words_per_bullet`
- `max_total_body_chars`
- `avg_chars_per_line`
- `body_line_budget`

Remediation order (deterministic):
1. DROP_BULLETS
2. Condense bullets (either deterministic truncation or LLM rewrite)
3. MOVE_TO_SPEAKER_NOTES (pressure valve)
4. SPLIT_SLIDE

Produce `ValidationReport` (persist it).

### Layer 4 — Render (python-pptx)
- Load template.
- Add slides by `layout_id` using the referenced template layout.
- Populate placeholders by matching `shape.alt_text == field_key`.
- **Parse Markdown inline formatting** in text values: convert `**bold**` to bold runs, `*italic*` to italic runs. Never emit raw Markdown markers as literal text.
- Insert PNG icons/images from resolved `asset_refs`.
- Write speaker notes.
- Emit `render_map.json` mapping slide_id → slide index + field_key mapping.

### Layer 5 — Review images ingestion (manual)
- Load slide images from `review_images/<run_id>/`.
- Map them to slide_id (by slide order) deterministically.

### Layer 6 — Vision Critique (LLM)
- Produce structured findings: (S0-S3) + affected fields.

### Layer 7 — Patch Planner + Applier
- Convert CritiqueReport → PatchSet.
- Apply patches to DeckIR to produce v2.
- Re-run preflight on v2 before rendering.

---

## 5) Data Contracts (Strict Enforcement)
Agent must implement Pydantic schemas (or equivalent) for:
- ContentModel
- DeckIR
- ValidationReport
- CritiqueReport
- PatchSet
- RenderMap

All LLM outputs must be validated against schemas.
- If invalid: retry with stronger schema instructions.
- Bounded retries only (e.g., 2). Fail fast with clear error logs.

---

## 6) LLM Prompting Rules
### 6.1 Planner prompt must:
- **Provide the visual vocabulary** (concepts with descriptions, not raw icon IDs). The LLM picks concepts; the pipeline resolves to icons deterministically.
- **Provide the branded image catalog** with theme descriptions and layout guidance.
- **List allowed layouts and field keys** per layout, indicating which layouts have `ph_image`.
- **Enforce that every layout with `ph_image` MUST have an `asset_ref`** — no empty image placeholders.
- **Include full cue data prominently**: `icon_hints`, `image_hint`, `layout_hint`, `notes` from the visualization cues must be front-and-center in the user prompt, not buried.
- **Include 2-3 worked examples** of well-planned slides with appropriate layout + visual choices.
- Enforce constraints (bullets/words/char limits).
- Require JSON-only output matching DeckIR schema.

### 6.2 Critic prompt must:
- accept slide image + slide spec
- produce CritiqueReport schema
- identify S0/S1 issues (overflow/density) aggressively

### 6.3 Patch planner prompt must:
- follow pressure-valve-first policy:
  - MOVE_TO_SPEAKER_NOTES → DROP_BULLETS → SPLIT_SLIDE → REWRITE → CHANGE_LAYOUT
- output PatchSet schema only

---

## 7) Pressure Valve Policy (Must Implement)
When any slide violates fit budgets or critic flags overflow (S0/S1):
- Keep the best/most essential points on-slide.
- Move excess detail into speaker notes.
- If notes are getting huge, split into an appendix slide (later phase); MVP only uses notes or split.

This is the primary mechanism to keep decks readable.

---

## 8) Template Drift Detection (Fail Fast)
On startup, validate:
- every `layout_id` in `layout_catalog.json` maps to a real layout in the template
- every required `field_key` has a matching placeholder in the corresponding layout
- warn/fail if missing placeholders

Do not proceed with rendering if the template/catalog mismatch is detected.

---

## 9) Logging and Debuggability (Required)
Every module must log structured events to `run_log.jsonl`:
- `NORMALIZE_DONE`
- `PLAN_DONE`
- `VALIDATE_DONE`
- `RENDER_DONE`
- `VISUAL_CUE_UNRESOLVED` — logged when a cue hint could not be resolved to an asset
- `CRITIQUE_DONE`
- `PATCH_APPLIED`
- errors with stack traces and clear human-readable messages

Persist every intermediate artifact; do not keep state only in memory.

---

## 10) Testing Requirements
Agent must implement:
- unit tests for schema validation
- unit tests for preflight fit heuristics + remediation ordering
- unit tests for visual vocabulary concept resolution
- unit tests for Markdown inline formatting parsing
- a smoke test that:
  - runs pipeline on a small sample content
  - produces a PPTX and artifacts

Do not attempt pixel-perfect visual tests.

---

## 11) "Do Not Do" List
- Do not implement arbitrary x/y layout engines.
- Do not depend on PowerPoint autofit for correctness.
- Do not insert SVGs in the render path (convert to PNG offline).
- Do not automate PowerPoint export unless explicitly asked.
- Do not add advanced animations/SmartArt/charts.
- Do not send raw icon IDs to the LLM planner. Always use the visual vocabulary as the abstraction layer.

---

## 12) Current Work Order (Visual Polish Phase)
See `PLAN.md` Section 3 for detailed steps. Summary:

1. **Fix Markdown rendering** — parse `**bold**` / `*italic*` into formatted text runs in the renderer.
2. **Fix cue forwarding** — ensure `icon_hints`, `image_hint`, `layout_hint` from combined markdown reach the planner intact.
3. **Build visual vocabulary** — curated `visual_vocabulary.json` mapping ~200-300 concepts to icon picks per pack.
4. **Tag branded icons** — use Gemini Vision on 213 `icon_*.png` files to generate semantic metadata.
5. **Build branded image catalog** — map 12 Dimensional Keyword illustration sets to slide themes with color/layout guidance.
6. **Redesign planner prompt** — give the LLM visual vocabulary + branded catalog + cues + examples instead of raw icon IDs.
7. **Add post-planning visual fill** — deterministic safety net for empty `ph_image` slots.

---

## 13) Definition of Done (Visual Polish)
A 10-slide deck generated from `legacy-system-navigator.combined.md` should:
- Have icons or branded images on every slide whose layout supports `ph_image`.
- Use at least 2 different Dimensional Keyword branded images on title/section slides.
- Have zero literal `**` or `*` Markdown artifacts in rendered text.
- Apply bold formatting where Markdown bold was intended.
- Have layout choices driven by cues and matching content density.
- Have all cue `icon_hints` and `image_hint` values attempted for resolution (unresolved ones logged as `VISUAL_CUE_UNRESOLVED`).
- Open cleanly in PowerPoint on macOS with template theme preserved.
- All artifacts stored in `runs/<run_id>/` with logs.

---
