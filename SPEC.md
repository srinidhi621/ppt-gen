# SPEC.md — LLM-Assisted PPTX Generator (python-pptx)

## 0. Document Status
- **Owner:** You
- **Primary consumer:** Coding agent (Codex) + human reviewer
- **Renderer:** python-pptx
- **Output format:** Microsoft PowerPoint compatible `.pptx` (editable)

### Implementation Progress

| Component | Status | Notes |
|-----------|--------|-------|
| Template preparation | ✅ DONE | Corp Deck 2025 - Nov.pptx (118 layouts, 5 masters) |
| Icon conversion | ✅ DONE | 213 PNG icons at 512x512px |
| Alt-Text field_keys | ✅ DONE | 387/387 placeholders tagged (100%) |
| Layout catalog | ⏳ PENDING | Next: generate from template analysis |
| Pydantic schemas | ⏳ PENDING | ContentModel, DeckIR, ValidationReport, etc. |
| Content normalization | ⏳ PENDING | Markdown → ContentModel |
| LLM Planner | ⏳ PENDING | ContentModel → DeckIR |
| Preflight validation | ⏳ PENDING | Fit checks + remediation |
| Renderer | ⏳ PENDING | DeckIR → PPTX via python-pptx |
| Vision critique | ⏳ PENDING | Phase 1 review loop |

---

## 1. Problem Statement
Create a programmable system that takes:
1) a **corporate PowerPoint template** (theme + masters + curated layouts),
2) an **icon pack** (Phase 1: PNG only),
3) **written content** (Markdown preferred),
4) **visualization cues** (structured hints),

…then generates a **tasteful, on-brand, editable PPTX** by:
- using an LLM for **planning and writing** (slide outline, layout selection, concise bullets, icon selection),
- using deterministic logic for **fit validation** (no overflow assumptions),
- using `python-pptx` as a deterministic renderer,
- optionally iterating via a **vision-based critique loop** that proposes revision patches.

---

## 2. Goals
### 2.1 Functional Goals
- Generate PPTX decks that:
  - adhere to the corporate theme and master slides (logo, fonts, colors, footers),
  - use only pre-approved layouts (“layout catalog”),
  - keep slide text within layout fit constraints (prevent overflow),
  - remain fully editable in Microsoft PowerPoint (Mac/Windows).

- Provide a structured pipeline:
  - Content normalization (Markdown as source of truth),
  - Deck planning (LLM → constrained intermediate representation),
  - Preflight validation + deterministic remediation,
  - Rendering via python-pptx,
  - Review + rework loop (Phase 1 manual export; later automation optional).

### 2.2 Quality Goals
- Deterministic rendering given the same intermediate representation (IR) and template.
- Clear provenance and traceability:
  - Slide IDs, field keys, and logs map outputs back to inputs.
- A “pressure valve” mechanism:
  - Excess details move to speaker notes rather than shrinking text to unreadable sizes.

---

## 3. Non-Goals (Explicitly Out of Scope for MVP)
- Automatic PowerPoint-like autofit/responsive layout during rendering.
- Arbitrary/freeform design (no x/y “designer” layout generation in MVP).
- SVG icon fidelity guarantees (Phase 1 uses PNG to avoid inconsistent vector behavior).
- Complex animations/transitions, SmartArt, or advanced chart types.
- Fully headless slide image export on macOS in MVP (manual export is the default).

---

## 4. Key Constraints and Decisions
1. **Auto-layout myth**: python-pptx will not auto-fit content. The system MUST validate fit before rendering.
2. **Icons**: Phase 1 uses **high-res PNG** icons only to ensure consistent rendering and vision critique.
3. **macOS automation**: PowerPoint AppleScript automation can be flaky if PowerPoint sleeps or prompts login. MVP uses manual image export.
4. **Theme fidelity**: The renderer must rely on template placeholders/styles as much as possible.
5. **Placeholder binding**: Use **Alt-Text** (shape description) in template placeholders to store `field_key`, enabling deterministic mapping.

---

## 5. Inputs
### 5.1 Template Inputs (One-time)

**Current template:** `assets/template/template.pptx` (Corp Deck 2025 - Nov)

| Property | Value |
|----------|-------|
| Dimensions | 13.33" × 7.5" (standard 16:9) |
| Slide Masters | 5 |
| Slide Layouts | 118 |
| Total Placeholders | 387 (all tagged with field_keys) |

- `template.pptx`:
  - corporate theme, masters, and curated layouts
  - placeholder shapes labeled via **Alt-Text** with canonical `field_key` values
  - Backup maintained at `assets/template/template_backup_*.pptx`

- `layout_catalog.json` (pending):
  - maps `layout_id` → template layout + expected fields + constraint profile (fit heuristics)

### 5.2 Asset Inputs
- `icons/` directory of PNGs
- `icons.json` metadata:
  - `icon_id`
  - `tags` / `synonyms`
  - optional `style_group`

### 5.3 Runtime Inputs (Per deck)
- `content.md` (preferred) or equivalent plaintext input
- `cues.json` (structured visualization cues)
- `constraints.json` (optional overrides)

---

## 6. Outputs
### 6.1 Primary Output
- `runs/<run_id>/deck.pptx` (editable, PowerPoint compatible)

### 6.2 Secondary Outputs
- `runs/<run_id>/render_map.json`:
  - mapping between `slide_id`, slide index, and placeholder/shape identifiers

- `runs/<run_id>/run_log.jsonl`:
  - structured event logs (planning, validation, render, critique, patch)

- (Optional) `runs/<run_id>/critique_report.json` + `runs/<run_id>/patch_set.json`

---

## 7. Glossary
- **Template**: the corporate PPTX used as the visual source of truth (masters/layouts).
- **Layout Catalog**: the set of allowed `layout_id`s and their constraints/fields.
- **Field Key**: canonical placeholder binding token (stored in template placeholder alt-text).
- **ContentModel**: normalized representation of source content.
- **DeckIR**: intermediate representation used to render a deck deterministically.
- **PatchSet**: structured modifications to DeckIR.
- **Pressure Valve**: moving excess text to speaker notes to avoid overflow.

---

## 8. Layout Catalog and Template Contract

### 8.1 Layout Catalog
Each layout entry MUST specify:
- `layout_id` (string, stable identifier)
- `template_layout_ref` (index or name used to pick the layout in python-pptx)
- `fields` (list of required/optional field keys)
- `constraints_profile` (fit budgets: chars/lines/bullets)

### 8.2 Placeholder Contract (Alt-Text) — IMPLEMENTED

> **Status:** All 387 placeholders across 118 layouts have been tagged via `scripts/add_alt_text.py`.

- Every placeholder used for automated population MUST have Alt-Text set to a unique `field_key`.
- Field keys are set on `p:cNvPr/@descr` in the OOXML structure.

**Implemented field_key naming convention:**

| Placeholder Type | Single | Two | Three+ |
|-----------------|--------|-----|--------|
| Title/Center Title | `ph_title` | — | — |
| Subtitle | `ph_subtitle` | — | — |
| Body/Content | `ph_body` | `ph_body_left`, `ph_body_right` | `ph_col1`, `ph_col2`, `ph_col3`, `ph_col4` |
| Picture | `ph_image` | `ph_image_left`, `ph_image_right` | `ph_image_left`, `ph_image_center`, `ph_image_right` or `ph_image_1`, `ph_image_2`, ... |
| Date | `ph_date` | — | — |
| Footer | `ph_footer` | — | — |
| Slide Number | `ph_slide_number` | — | — |

**Disambiguation rules:**
- Placeholders of the same type are sorted by position (`left_inches`, then `top_inches`)
- 2-column layouts use `_left`/`_right` suffixes
- 3+ column layouts use `_col1`, `_col2`, etc.
- Photo grids with many images use numbered suffixes (`_1`, `_2`, ...)

### 8.3 Layout Fit Budgets (Hard Requirements)
For each layout, define preflight budgets:
- `max_title_chars`
- `max_bullets`
- `max_words_per_bullet`
- `max_total_body_chars`
- `body_line_budget`
- `avg_chars_per_line` (layout-specific heuristic constant)

**Rule:** Layer 3 (Preflight) MUST reject or remediate anything that violates budgets.

---

## 9. Data Models (Contracts)

> These are contracts, not implementation details. Exact representation can be JSON + Pydantic.

### 9.1 ContentModel
Required fields:
- `doc_id`, `version`, `source_hash`
- `sections[]` with:
  - `section_id`, `title`, `bullets[]`, `paragraphs[]`
- `entities[]` (optional)
- `metrics[]` (optional)
- `cues[]` (normalized cues referencing section/bullets)

### 9.2 DeckIR
Top-level:
- `deck_id`, `run_id`, `template_id`, `title`, `subtitle`
- `global_constraints`
- `slides[]`

Per slide:
- `slide_id` (stable)
- `layout_id` (must be allowed)
- `fields` (key-value map; keys must match layout `field_key`s)
- `speaker_notes` (string or structured notes object)
- `asset_refs` (icons/images)
- `constraints_override` (optional)

### 9.3 ValidationReport
- `violations[]` each with:
  - `slide_id`, `layout_id`, `field_key`
  - `violation_type` (TITLE_TOO_LONG, BODY_TOO_DENSE, TOO_MANY_BULLETS, etc.)
  - `severity` (BLOCKING / WARN)
  - `recommended_action`

### 9.4 CritiqueReport (Vision Critique)
- `findings[]` each with:
  - `slide_id`
  - `finding_type` (OVERFLOW_RISK, DENSITY_HIGH, HIERARCHY_WEAK, VISUAL_MISMATCH, WHITESPACE_ISSUE)
  - `severity` (S0-S3)
  - `affected_field_keys[]`
  - `recommendations[]` (action hints)

### 9.5 PatchSet (Edit DSL)
Patch types (minimum set):
- `REWRITE_FIELD_TEXT(field_key, instructions)`
- `DROP_BULLETS(field_key, keep_top_n)`
- `MOVE_TO_SPEAKER_NOTES(source_field_key, summary_field_key)`
- `SPLIT_SLIDE(strategy)`
- `CHANGE_LAYOUT(to_layout_id)` (rare; only if necessary)
- `SWAP_ICON(old_icon_id, new_icon_id)`

**Policy:** For S0/S1 overflow/density, prefer `MOVE_TO_SPEAKER_NOTES` then `DROP_BULLETS` then `SPLIT_SLIDE`. Layout changes are last resort.

---

## 10. System Architecture

### 10.1 Layered Pipeline
1. **Layer 0: Config**
2. **Layer 1: Content Normalization**
3. **Layer 2: Planning (LLM → DeckIR v1)**
4. **Layer 3: Preflight Validation + Deterministic Remediation (DeckIR v1.1)**
5. **Layer 4: Rendering (python-pptx)**
6. **Layer 5: Review (manual export images in MVP)**
7. **Layer 6: Vision Critique → CritiqueReport**
8. **Layer 7: Patch Planning → PatchSet**
9. **Layer 8: Apply patches → DeckIR v2 → re-render**

### 10.2 Determinism Boundaries
- Rendering must be deterministic.
- Preflight remediation rules must be deterministic.
- LLM planning/critique are non-deterministic; mitigate with:
  - schema enforcement
  - constrained choices
  - retries only on schema validation failures (bounded)

---

## 11. Rendering Rules (python-pptx)
- Always start from template PPTX.
- Add slides using template layouts.
- Bind placeholder population by reading placeholder **Alt-Text = field_key**.
- Avoid manual styling; rely on template formatting.
- Insert icons as PNG images (Phase 1).
- Write speaker notes always (even if empty string) so pressure valve is available.

### 11.1 Alt-Text Access Pattern (python-pptx)

To read `field_key` from a placeholder shape:

```python
from pptx.oxml.ns import qn

def get_field_key(shape):
    """Read field_key from placeholder's alt-text (descr attribute)."""
    elem = shape.element
    # For shape placeholders: p:nvSpPr/p:cNvPr
    nvSpPr = elem.find(qn('p:nvSpPr'))
    if nvSpPr is not None:
        cNvPr = nvSpPr.find(qn('p:cNvPr'))
        if cNvPr is not None:
            return cNvPr.get('descr', '')
    # For picture placeholders: p:nvPicPr/p:cNvPr
    nvPicPr = elem.find(qn('p:nvPicPr'))
    if nvPicPr is not None:
        cNvPr = nvPicPr.find(qn('p:cNvPr'))
        if cNvPr is not None:
            return cNvPr.get('descr', '')
    return None
```

**Important:** The alt-text is stored in the **presentation namespace** (`p:cNvPr`), not the drawing namespace (`a:cNvPr`).

---

## 12. Preflight Fit Heuristics (MVP)
For each slide field that is text-heavy:
- Estimate line count:
  - `estimated_lines = ceil(total_chars / avg_chars_per_line)`
- Enforce:
  - `estimated_lines <= body_line_budget`
  - `max_bullets`, `max_words_per_bullet`, `max_total_body_chars`

Remediation:
1. Condense bullets (LLM rewrite or deterministic trim)
2. Move overflow to speaker notes
3. Split slide

---

## 13. Review Loop (MVP)
### 13.1 Manual Image Export (Phase 1)
- Human opens `deck.pptx` in PowerPoint (Mac) and exports slide images to `review_images/`.
- Images named deterministically:
  - `slide_001.png`, `slide_002.png`, etc. (or by slide_id if you prefer)

### 13.2 Vision Critique
- Vision model reads each image + the expected slide spec and produces CritiqueReport.

### 13.3 Patch + Re-render
- PatchSet applied to DeckIR.
- Re-render deck.
- Repeat for up to `max_iterations` (MVP default: 2).

Stop conditions:
- No S0/S1 findings remain, or iteration cap reached.

---

## 14. Logging and Observability
- Use structured JSONL logs with event types:
  - `NORMALIZE_DONE`, `PLAN_DONE`, `VALIDATE_DONE`, `RENDER_DONE`, `CRITIQUE_DONE`, `PATCH_APPLIED`
- Persist run artifacts under `runs/<run_id>/`.

---

## 15. Testing Strategy (MVP)
- Unit tests:
  - schema validation for DeckIR/PatchSet
  - preflight heuristics and remediation outputs
- Golden tests:
  - fixed input content + cues + template → generated PPTX should be stable (structure and key text)
- Manual acceptance:
  - open in PowerPoint; visually confirm no clipping on typical decks

---

## 16. Security and Privacy
- Content may be sensitive; allow:
  - local-only runs
  - configurable LLM provider (OpenAI/Gemini)
  - redaction in logs (optional)
- Never upload the corporate template to third-party services unless explicitly configured.

---

## 17. Acceptance Criteria (MVP)
A run is successful if:
- Generated PPTX opens cleanly in PowerPoint (Mac).
- Theme and master elements are intact.
- All slide text is editable.
- No S0/S1 overflow/density issues after at most 1 rework iteration (target), and after at most 2 iterations (hard cap).
- Speaker notes contain overflow content when preflight or critique triggered pressure valve.

---