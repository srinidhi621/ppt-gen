# PLAN.md — MVP Implementation Plan

## 0. Objective
Implement an MVP pipeline that generates an editable, on-brand PPTX using:
- **Template-first rendering (python-pptx)**
- **LLM-driven planning constrained to a layout catalog**
- **Deterministic preflight validation to prevent overflow**
- **Manual review image export + vision critique + patch iteration**

No Beamer/LaTeX. No LibreOffice in MVP.

---

## Progress Tracker

| Phase | Task | Status |
|-------|------|--------|
| 0.1 | Template selection | DONE |
| 0.2 | SVG → PNG icon conversion | DONE |
| 0.3 | Directory structure setup | DONE |
| 0.4 | Template analysis | DONE |
| 0.5 | Add Alt-Text to placeholders | DONE |
| 0.6 | Contract alignment + catalog gate | PENDING (next) |
| 1.x | MVP pipeline (prove determinism) | PENDING (blocked on 0.6) |
| 2.x | LLM planning + review loop | PENDING (blocked on 1.x) |
| 3.x | Productization (deferred) | DEFERRED (after MVP proven) |

**Last updated:** 2026-02-03

---

## 1. Repo Structure

```
ppt-gen/
├── SPEC.md                    # Contract specification
├── PLAN.md                    # This file
├── AGENTS.md                  # Agent operating guide
├── .venv/                     # Python virtual environment
│
├── assets/                   # Canonical asset root (lowercase)
│   ├── template/
│   │   ├── template.pptx                    # ✅ Corp Deck 2025 (387 placeholders tagged)
│   │   └── template_backup_*.pptx           # ✅ Auto-generated backups
│   ├── icons/
│   │   ├── icons.json                       # ✅ Icon metadata (213 icons)
│   │   └── png/                             # ✅ 512x512 PNG icons
│   ├── layout/
│   │   └── layout_catalog.json              # ⏳ NEXT: generate from template
│   ├── Icons and Dimensional Keywords/      # Original SVG source
│   └── Ascendion Logos/                     # Logo assets
│
├── scripts/
│   ├── inspect_template.py                  # ✅ Template analysis + alt-text report
│   ├── convert_svg_to_png.py                # ✅ SVG → PNG batch converter
│   ├── add_alt_text.py                      # ✅ Automated field_key assignment
│   ├── alt_text_report.json                 # ✅ Field_key assignment log
│   └── template_report_*.json               # ✅ Template analysis snapshots
│
├── inputs/                    # To be created
│   ├── content.md
│   ├── cues.json
│   └── constraints.json (optional)
│
├── src/                       # To be implemented (Phase 1)
│   ├── models/                # Pydantic schemas
│   ├── normalize/             # Markdown → ContentModel
│   ├── plan/                  # LLM planner
│   ├── validate/              # Preflight + remediation
│   ├── render/                # python-pptx renderer
│   └── critique/              # Vision critic + patches
│
└── runs/<run_id>/             # Created at runtime
    ├── deckir_v1.json
    ├── deckir_v1_1.json
    ├── deck_v1.pptx
    ├── render_map.json
    ├── validation_report.json
    └── run_log.jsonl
```

---

## 2. Phase 0 — Template + Catalog Hardening

### 2.1 Select/Prepare the template PPTX — DONE

**Selected template:** `Corp Deck 2025 - Nov.pptx`
- **Dimensions:** 13.33" x 7.5" (standard 16:9)
- **Slide masters:** 5
- **Total layouts:** 118
- **Location (canonical):** `assets/template/template.pptx`

Available layout categories:
- Title slides (with/without images, light/dark variants)
- Section breaks (light/dark)
- Content layouts: One/Two/Three/Four content (light/dark)
- Content with image layouts
- Case study templates
- Agenda layouts
- Statement/Boilerplate layouts
- Blank layouts

### 2.2 Convert icons to PNG — DONE

**Source:** `assets/Icons and Dimensional Keywords/2025 New Icons/` (213 SVG files)
**Output:** `assets/icons/png/` (213 PNG files, 512x512px)
**Metadata:** `assets/icons/icons.json`

Icon naming: `icon_001.png` through `icon_213.png` (zero-padded)

To re-run conversion:
```bash
DYLD_LIBRARY_PATH=/opt/homebrew/lib python scripts/convert_svg_to_png.py
```

### 2.3 Add Alt-Text field_key tags to placeholders — DONE (Automated)

**Coverage:** 100% (387 of 387 placeholders have Alt-Text)

Automated via `scripts/add_alt_text.py`:

```bash
source .venv/bin/activate
python scripts/add_alt_text.py              # Add alt-text to all layouts
python scripts/add_alt_text.py --dry-run    # Preview without changes
python scripts/add_alt_text.py --mvp-only   # Only MVP layouts
```

**Field key naming convention:**

| Placeholder Type | field_key |
|-----------------|-----------|
| Title | `ph_title` |
| Subtitle | `ph_subtitle` |
| Body (single) | `ph_body` |
| Body (2 columns) | `ph_body_left`, `ph_body_right` |
| Body (3+ columns) | `ph_col1`, `ph_col2`, `ph_col3`, `ph_col4` |
| Image (single) | `ph_image` |
| Image (2) | `ph_image_left`, `ph_image_right` |
| Image (3) | `ph_image_left`, `ph_image_center`, `ph_image_right` |
| Image (many) | `ph_image_1`, `ph_image_2`, ... |

**Outputs:**
- Modified template: `assets/template/template.pptx`
- Backup: `assets/template/template_backup_YYYYMMDD_HHMMSS.pptx`
- Report: `scripts/alt_text_report.json`

**Definition of Done:** ✓
- All 118 layouts processed
- 387 placeholders tagged
- Template saved with backup

## 2.4 Phase 0.6 — Contract Alignment + Catalog Gate (PENDING — Next Milestone)

This is a hard gate before implementing the MVP pipeline. It eliminates path/contract drift and produces the layout catalog + drift validation needed to safely render.

### 2.4.1 Canonical paths + contract alignment (must-do)
**Policy:** Use `assets/` (lowercase) as the canonical asset root going forward.

Tasks:
1. Migrate the repo asset directory naming to `assets/` (lowercase) and update references everywhere:
   - `PLAN.md`, `SPEC.md`, `README.md`, scripts
2. Standardize outputs exclusively under `runs/<run_id>/` (avoid `output/` conventions).

**Definition of Done**
- All docs/scripts reference `assets/...` paths only
- Run artifacts are specified under `runs/<run_id>/` only

### 2.4.2 Build `layout_catalog.json` (hard requirement for planning + validation)
Generate `assets/layout/layout_catalog.json` from template analysis.

**Approach:** Create `scripts/generate_layout_catalog.py` that:
1. Loads `assets/template/template.pptx` and reads all layouts and their placeholder `field_key`s from alt-text
2. Filters to MVP-priority layouts (or all)
3. Generates a structured catalog with initial fit constraints per layout
4. Produces a validation report if any layout/field is ambiguous or missing

**Required fields per layout entry:**

```json
{
  "layout_id": "one_content_light",
  "template_layout_name": "One Content - Light",
  "master_index": 0,
  "layout_index": 10,
  "fields": [
    {"field_key": "ph_title", "type": "title", "required": true},
    {"field_key": "ph_body", "type": "content", "required": true}
  ],
  "constraints": {
    "max_title_chars": 60,
    "max_bullets": 6,
    "max_words_per_bullet": 15,
    "max_total_body_chars": 600,
    "body_line_budget": 12,
    "avg_chars_per_line": 50
  }
}
```

**MVP Layout Selection (12 layouts to start):**

| Layout Name | layout_id | Use Case |
|-------------|-----------|----------|
| Title with Image 2 | `title_image_light` | Opening slide |
| Section Break - Light 1 | `section_break_light` | Section dividers |
| Header Only - Light | `header_only_light` | Title-only slides |
| One Content - Light | `one_content_light` | Standard bullet slide |
| Two Content - Light | `two_content_light` | Two-column comparison |
| Three content - Light | `three_content_light` | Three-column layout |
| Four content - Light | `four_content_light` | Four-column layout |
| One Content With Image - Light | `content_image_light` | Content + visual |
| Two Content with Image - Light | `two_content_image_light` | Two columns + image |
| Statement - Light | `statement_light` | Big quote/statement |
| Agenda - Light | `agenda_light` | Agenda/TOC slide |
| BoilerPlate - Light | `boilerplate_light` | Closing slide |

**Constraint calibration strategy:**
- Start with conservative estimates based on placeholder dimensions
- Refine after testing with real content
- Use `avg_chars_per_line` ≈ placeholder_width_inches × 7 (heuristic for body text)

**Definition of Done:**
- `assets/layout/layout_catalog.json` exists with at least 12 MVP layouts
- Each layout has field_keys matching template alt-text
- Each layout has initial constraint estimates
- A validation script confirms catalog matches template (template drift detection)

### 2.4.3 Template drift detection (fail fast)
Add a startup validator (and/or standalone script) that checks:
- every `layout_id` in the catalog maps to a real layout in the template
- every required `field_key` exists in that layout

**Definition of Done**
- Rendering (and optionally the CLI startup) refuses to proceed on mismatch

### 2.4.4 Add sample inputs for repeatable testing
Create:
- `inputs/content.md` (small but representative deck content)
- `inputs/cues.json` (minimal cues)

**Definition of Done**
- Sample inputs are stable and used by the smoke test in Phase 1
- A short deck can be generated end-to-end once Phase 1 is implemented

---

## 3. Phase 1 — MVP Pipeline (Prove Determinism First)

**Principle:** Build the deterministic engine and prove it works with hand-authored inputs before integrating LLM planning. This keeps debugging fast and establishes stable contracts.

### 3.1 Implement Models (Pydantic)
Schemas needed:
- Config
- ContentModel
- DeckIR
- ValidationReport
- CritiqueReport
- PatchSet
- RenderMap

**Definition of Done:** All artifacts validate and serialize reliably.

### 3.2 Renderer from a hand-authored DeckIR (determinism proof)
Add a CLI command that takes an explicit `DeckIR` JSON and produces:
- `runs/<run_id>/deck_v1.pptx`
- `runs/<run_id>/render_map.json`
- `runs/<run_id>/run_log.jsonl`

**Definition of Done:** Rendering is deterministic given the same DeckIR + template + assets.

### 3.3 Preflight Validation + Remediation (DeckIR v1 → v1.1)
Hard fit checks:
- title chars, bullets count, words per bullet
- total body chars, estimated line count

Remediation order:
1. Trim bullet count
2. Shorten bullets
3. Pressure valve: move overflow to notes
4. Split slide

Artifacts:
- `runs/<run_id>/deckir_v1_1.json`
- `runs/<run_id>/validation_report.json`

**Definition of Done:** Overflow is transformed before rendering; ValidationReport records changes.

### 3.4 Content Normalization (Markdown → ContentModel)
- Parse `inputs/content.md`
- Produce normalized model with sections, bullets, paragraphs
- Tie cues to sections/bullets by IDs
- Store `source_hash` for diffing

**Definition of Done:** Same input → stable ContentModel with stable IDs.

### 3.5 Smoke test (local)
One command runs the deterministic path using sample inputs and produces all run artifacts under `runs/<run_id>/`.

**Definition of Done:** A PPTX is generated and opens in PowerPoint; logs and artifacts are present.

---

## 4. Phase 2 — LLM Planning + Review Loop (After MVP Determinism)

### 4.1 Planner (LLM → DeckIR v1)
Responsibilities:
- Propose slide list with `layout_id`
- Produce concise fields for each slide
- Select icons by `icon_id`
- Produce speaker notes skeleton

Constraints:
- Only allowed layouts and field keys
- Obey global constraints (max bullets etc.)
- Bounded retries only on schema invalidity (do not “retry” for quality)

**Definition of Done:** Planner outputs schema-valid DeckIR v1 consistently.

### 4.2 Renderer (python-pptx)
Responsibilities:
- Load `assets/template/template.pptx`
- Add slides from template layout
- Populate placeholders by matching Alt-Text `field_key`
- Insert PNG icons
- Write speaker notes
- Emit `deck_v1.pptx` + `render_map.json`

**Definition of Done:** Output opens in PowerPoint, theme intact, placeholders mapped robustly.

---

## 5. Phase 2 Review Cycle — Vision Critique + Patch

### 5.1 Manual export protocol
1. Open `runs/<run_id>/deck_v1.pptx` in PowerPoint
2. Export slides as PNGs to `review_images/<run_id>/`
3. Name files by slide order: `slide_001.png`, etc.

### 5.2 Vision Critic (Images → CritiqueReport)
Check each slide for:
- Clipping/overflow (S0)
- Density/too-small text (S1)
- Hierarchy issues (S2)
- Icon mismatch (S2)
- Whitespace balance (S3)

### 5.3 Patch Planner (CritiqueReport → PatchSet)
Policy (pressure valve first):
1. MOVE_TO_SPEAKER_NOTES
2. DROP_BULLETS keep_top_n
3. SPLIT_SLIDE
4. REWRITE_FIELD_TEXT
5. CHANGE_LAYOUT (last resort)

### 5.4 Apply patches and re-render (DeckIR v2)
- Apply patches → DeckIR v2
- Run preflight again
- Render `deck_v2.pptx`
- Max iterations: 2

---

## 6. Operational Workflow (MVP)
1. Prepare inputs: `content.md`, `cues.json`
2. Run pipeline → `deck_v1.pptx` + artifacts
3. Export PNGs manually to `review_images/<run_id>/`
4. Run critic + patch planner → PatchSet
5. Apply patch + render `deck_v2.pptx`
6. Final human polish in PowerPoint

---

## 7. MVP Acceptance Criteria
- PPTX opens and is editable in PowerPoint (Mac)
- Corporate theme preserved
- No S0/S1 issues after iteration
- Speaker notes contain overflow when pressure valve triggered
- Artifacts are reproducible and auditable

---

## 8. Known Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Overflow risk | Hard preflight budgets + pressure valve |
| Icon rendering (SVG) | Phase 1 uses PNG only (DONE) |
| macOS automation flaky | Manual export for MVP |
| Template drift | Validate template vs catalog at startup |
| Path drift | Canonicalize `assets/` + update all references (Phase 0.6) |

---

## 9. Post-MVP Backlog (Defer until MVP proven)
- Automate slide image export
- Calibrate fit heuristics from real decks
- Diff-aware regeneration
- Editable charts via template replacement
- Partial re-render (changed slides only)
- Icon selection via embeddings

---

## Next Action Required

**NEXT:** Complete Phase 0.6 (contract alignment + layout catalog + drift detection)

### Immediate Steps

1. **Canonicalize `assets/` paths**
   - Migrate directory naming and update all references (docs + scripts)
   - Standardize run artifacts under `runs/<run_id>/` only

2. **Create `scripts/generate_layout_catalog.py`**
   - Read template layouts and their field_keys from alt-text
   - Generate `layout_id` from layout name (snake_case, normalized)
   - Compute initial fit constraints from placeholder dimensions
   - Output `assets/layout/layout_catalog.json`

3. **Select MVP layouts** (start with 12 core layouts)
   - Title slides, section breaks, content layouts, agenda, statement

4. **Validate catalog against template**
   - Ensure all field_keys in catalog exist in template
   - Fail fast on mismatch (template drift detection per AGENTS.md)

5. **Add sample inputs**
   - Create `inputs/content.md` and `inputs/cues.json`

### After Phase 0.6

6. **Phase 1.1: Implement Pydantic schemas**
   - `src/models/`: ContentModel, DeckIR, ValidationReport, CritiqueReport, PatchSet

7. **Phase 1.2: Renderer from hand-authored DeckIR**
   - Prove deterministic rendering + render_map

8. **Phase 1.3: Preflight validation**
   - Fit checks + remediation + ValidationReport + DeckIR v1.1 artifact

9. **Phase 1.4: Content normalization**
   - `src/normalize/`: Markdown parser → ContentModel with stable IDs

10. **Phase 1.5: Smoke test**
   - A small end-to-end run produces a PPTX and all artifacts under `runs/<run_id>/`

11. **Phase 2: LLM Planner**
   - `src/plan/`: Prompt templates + DeckIR generation (only after Phase 1 is stable)

12. **Phase 2: Critique + patch iteration**
   - `src/critique/`: Vision critic + PatchSet generation + applier

---

## Completed Work Summary

### Phase 0 Deliverables (All Done)

| Task | Deliverable | Details |
|------|-------------|---------|
| 0.1 | Template selected | Corp Deck 2025 - Nov.pptx (13.33" × 7.5", 118 layouts, 5 masters) |
| 0.2 | Icons converted | 213 SVG → PNG at 512×512px with metadata in icons.json |
| 0.3 | Directory structure | assets/, scripts/, organized per AGENTS.md |
| 0.4 | Template analyzed | `inspect_template.py` generates JSON reports |
| 0.5 | Alt-text automated | `add_alt_text.py` tagged 387/387 placeholders (100%) |

### Scripts Created

| Script | Purpose | Usage |
|--------|---------|-------|
| `inspect_template.py` | Analyze template structure, report alt-text coverage | `python scripts/inspect_template.py` |
| `convert_svg_to_png.py` | Batch convert SVG icons to PNG | `DYLD_LIBRARY_PATH=/opt/homebrew/lib python scripts/convert_svg_to_png.py` |
| `add_alt_text.py` | Programmatically set field_key alt-text | `python scripts/add_alt_text.py [--dry-run] [--mvp-only]` |

### Key Technical Decisions

1. **Alt-text location:** `p:cNvPr/@descr` (presentation namespace, not drawing namespace)
2. **Field_key naming:** Position-based disambiguation for multi-placeholder layouts
3. **Backup strategy:** Timestamped backups before template modification
4. **Verification:** `inspect_template.py` updated to read `p:cNvPr` correctly
