# AGENTS.md — Operating Guide (LLM-Assisted PPTX Generator)

This repo builds a deterministic PPTX generator using:
- **python-pptx** for rendering
- **PowerPoint template-first** approach (masters + curated layouts)
- **LLM-assisted planning** constrained to a layout catalog
- **Hard preflight validation** to prevent overflow (no “auto-layout” assumptions)
- **Manual review image export** in MVP, with an optional vision critique → patch → rerender loop

Agent: follow this guide strictly. Do not invent new architecture or deviate from contracts without updating SPEC.md.

---

## 0) Primary Artifacts (Source of Truth)
You must keep these consistent:
- `SPEC.md` — full specification and contracts
- `PLAN.md` — phase-wise MVP plan
- `assets/template/template.pptx` — corporate template (masters + layouts)
- `assets/layout/layout_catalog.json` — allowed layouts + fields + fit budgets
- `assets/icons/icons.json` — icon metadata
- `inputs/content.md` — content input (Markdown preferred)
- `inputs/cues.json` — visualization cues
- `runs/<run_id>/` — run outputs and logs

---

## 1) Non-Negotiable Constraints
### 1.1 The "Auto-Layout Myth"
`python-pptx` does not behave like the PowerPoint UI. It will not auto-fit text.  
**Therefore: Preflight validation must prevent overflow before rendering.**

### 1.2 Template-first Rendering
Theme fidelity is achieved by using the PowerPoint template’s:
- masters
- layouts
- placeholder formatting

**Do not manually style fonts/colors** in MVP unless explicitly required and documented.

### 1.3 Placeholder Binding via Alt-Text (`field_key`)
The template placeholders must have Alt-Text Description set to a canonical `field_key` (e.g., `ph_title`, `ph_body_left`).  
**Renderer populates placeholders by matching `shape.alt_text` to `field_key`.**

Do not rely on placeholder indexes. That is brittle.

### 1.4 Icons: PNG Only (MVP)
Use high-resolution PNG icons for Phase 1.  
Do not implement SVG handling in MVP.

### 1.5 macOS Export Automation is Deferred
In MVP, slide image export is manual (PowerPoint UI).  
Do not implement AppleScript automation unless explicitly asked in a later phase.

---

## 2) What Agent Should Build (MVP Scope)
### MVP Deliverables
1. A CLI pipeline that:
   - reads `content.md`, `cues.json`, optional `constraints.json`
   - normalizes content into `ContentModel`
   - calls planner LLM to create `DeckIR v1`
   - runs preflight validation + remediation to `DeckIR v1.1`
   - renders PPTX via python-pptx using template layouts and alt-text placeholder binding
   - writes artifacts into `runs/<run_id>/`

2. A review loop (Phase 1):
   - a command that ingests manually exported slide images from `review_images/<run_id>/`
   - runs a vision critic LLM producing `CritiqueReport`
   - produces `PatchSet`
   - applies patches to generate `DeckIR v2`
   - re-renders `deck_v2.pptx`

---

## 3) Repository Conventions
### 3.1 Paths
- Templates: `assets/template/template.pptx`
- Layout catalog: `assets/layout/layout_catalog.json`
- Icons: `assets/icons/png/` and `assets/icons/icons.json`
- Inputs: `inputs/`
- Outputs: `runs/<run_id>/`
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

If review loop is executed:
- `critique_report.json`
- `patch_set.json`
- `deckir_v2.json`
- `deck_v2.pptx`

---

## 4) Architecture Implementation Checklist
Agent must implement these layers (as modules/packages):

### Layer 0 — Config
- Load config including template paths, model config, defaults.

### Layer 1 — Normalize (`content.md` → ContentModel)
- Parse Markdown into stable section/bullet structure with stable IDs.
- Produce a `source_hash`.

### Layer 2 — Plan (LLM → DeckIR v1)
- Planner must produce schema-valid DeckIR.
- DeckIR must only include:
  - allowed `layout_id`s from `layout_catalog.json`
  - allowed field keys
  - allowed `icon_id`s from `icons.json`

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
- Insert PNG icons.
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
Agent  must implement Pydantic schemas (or equivalent) for:
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
- list allowed layout_ids
- list allowed field_keys per layout
- list allowed icon_ids (or require semantic tags that map to icon_ids deterministically)
- enforce constraints (bullets/words/char limits)
- require JSON-only output matching DeckIR schema

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
- `CRITIQUE_DONE`
- `PATCH_APPLIED`
- errors with stack traces and clear human-readable messages

Persist every intermediate artifact; do not keep state only in memory.

---

## 10) Testing Requirements (MVP)
Agent must implement:
- unit tests for schema validation
- unit tests for preflight fit heuristics + remediation ordering
- a smoke test that:
  - runs pipeline on a small sample content
  - produces a PPTX and artifacts

Do not attempt pixel-perfect visual tests in MVP.

---

## 11) “Do Not Do” List
- Do not implement arbitrary x/y layout engines.
- Do not depend on PowerPoint autofit for correctness.
- Do not insert SVGs in MVP.
- Do not automate PowerPoint export in MVP.
- Do not add advanced animations/SmartArt/charts in MVP.

---

## 12) Suggested Work Order for Agent (MVP)
1. Implement schemas + config loader
2. Implement ContentModel normalization from Markdown
3. Implement planner LLM adapter producing DeckIR
4. Implement preflight validation + remediation
5. Implement renderer (alt-text placeholder binding)
6. Implement run artifact persistence
7. Implement review ingestion (manual images)
8. Implement vision critic → CritiqueReport
9. Implement patch planner + applier
10. Wire CLI commands:
   - `generate`
   - `critique`
   - `patch-and-render`
   - `full-run` (generate + optional review if images exist)

---

## 13) Definition of Done (MVP)
MVP is done when:
- A 10-slide deck can be generated and opened in PowerPoint on macOS.
- Theme/master elements are preserved.
- All text is editable.
- Preflight prevents obvious overflow most of the time.
- One critique + patch iteration resolves S0/S1 issues for typical inputs.
- All artifacts are stored in `runs/<run_id>/` with logs.

---