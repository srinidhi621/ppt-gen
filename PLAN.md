# PLAN.md — MVP Implementation Plan

## 0. Objective
Implement an MVP pipeline that generates an editable, on-brand PPTX using:
- **Template-first rendering (python-pptx)**
- **LLM-driven planning constrained to a layout catalog**
- **Deterministic preflight validation to prevent overflow**
- **Manual review image export + vision critique + patch iteration**



---

## Progress Tracker

| Phase | Task | Status |
|-------|------|--------|
| 0.x | Phase 0 complete | DONE |
| 1.x | MVP pipeline (prove determinism) | DONE |
| 2.x | LLM planning + review loop | PENDING (next) |
| 3.x | Productization | DEFERRED (after MVP proven) |

### Phase 1 Detailed Status

| Task | Status |
|------|--------|
| 1.1 Models + Config (Pydantic) | ✅ DONE |
| 1.2 Template Drift Detection | ✅ DONE |
| 1.3 Renderer (DeckIR → PPTX) | ✅ DONE |
| 1.4 Preflight Validation + Remediation | ✅ DONE |
| 1.5 Content Normalization (Markdown → ContentModel) | ✅ DONE |
| 1.6 CLI Commands (validate, render, smoke) | ✅ DONE |
| 1.7 Sample DeckIR (determinism proof) | ✅ DONE |
| 1.8 Unit Tests (45 tests passing) | ✅ DONE |

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
│   │   └── template.pptx                    # ✅ Corp Deck 2025 (387 placeholders tagged)
│   ├── icons/
│   │   ├── icons.json                       # ✅ Icon metadata (213 icons)
│   │   └── png/                             # ✅ 512x512 PNG icons
│   ├── layout/
│   │   └── layout_catalog.json              # ✅ 12 MVP layouts + constraints
│   ├── Icons and Dimensional Keywords/      # Original SVG source
│   └── Ascendion Logos/                     # Logo assets
│
├── scripts/
│   ├── inspect_template.py                  # ✅ Template analysis + alt-text report
│   ├── convert_svg_to_png.py                # ✅ SVG → PNG batch converter
│   ├── add_alt_text.py                      # ✅ Automated field_key assignment
│   ├── generate_layout_catalog.py           # ✅ Build layout catalog + drift validation
│   └── alt_text_report.json                 # ✅ Field_key assignment log
│
├── inputs/                    # Sample inputs
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

## 2. Phase 0 — Template + Catalog Hardening (Complete)

Key outputs now in place:
- Canonical assets under `assets/` (lowercase)
- `assets/template/template.pptx` tagged with 387 `field_key`s
- `assets/layout/layout_catalog.json` with 12 MVP layouts + constraints
- Template drift validation implemented in `scripts/generate_layout_catalog.py`
- Sample inputs in `inputs/`

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
| Icon rendering (SVG) | Phase 1 uses PNG only |
| macOS automation flaky | Manual export for MVP |
| Template drift | Validate template vs catalog at startup |
| Path drift | Canonicalize `assets/` + update all references |

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

**NEXT:** Begin Phase 2 (LLM Planning + Review Loop)

### Phase 1 — Detailed Build Plan (COMPLETED)

#### 1.1 Models + Config (Pydantic)
**Status:** ✅ DONE
- Created `src/models/` with strict Pydantic models for: Config, ContentModel, DeckIR, ValidationReport, CritiqueReport, PatchSet, RenderMap.
- Schema validation on all JSON inputs/outputs at module boundaries.
- JSON serialization helpers with deterministic ordering.

#### 1.2 Template Drift Detection + Catalog Validation
**Status:** ✅ DONE
- Validator in `src/validate/drift.py` loads layout_catalog.json and template.pptx.
- Verifies every catalog entry resolves to a template layout.
- Verifies required field_keys exist in each layout.
- CLI command: `python -m src.cli validate`

#### 1.3 Renderer (DeckIR → PPTX) from Hand-Authored DeckIR
**Status:** ✅ DONE
- `src/render/renderer.py` loads template and renders from DeckIR.
- Adds slides by layout_id, populates placeholders by alt_text == field_key.
- Supports PNG icons and speaker notes.
- Emits render_map.json mapping slide_id → slide_index + field_keys.
- CLI command: `python -m src.cli render --deckir path/to/deckir.json`

#### 1.4 Preflight Validation + Remediation (DeckIR v1 → v1.1)
**Status:** ✅ DONE
- `src/validate/preflight.py` implements fit checks using catalog constraints.
- Checks: title length, bullet count, words per bullet, total chars, line budget.
- Remediation order: DROP_BULLETS → CONDENSE → MOVE_TO_SPEAKER_NOTES.
- Emits validation_report.json and deckir_v1_1.json.

#### 1.5 Content Normalization (Markdown → ContentModel)
**Status:** ✅ DONE
- `src/normalize/parser.py` parses Markdown into ContentModel.
- Supports section separators (---), metadata comments, headings, bullets, paragraphs.
- Generates stable section IDs from titles or metadata.
- Computes source_hash for change detection.

#### 1.6 Determinism Proof + End-to-End Smoke Test
**Status:** ✅ DONE
- CLI command: `python -m src.cli smoke --deckir path/to/deckir.json`
- Sample DeckIR at `inputs/sample_deckir.json` (10 slides).
- Produces all required artifacts under `runs/<run_id>/`:
  - deckir_v1.json, deckir_v1_1.json, validation_report.json
  - render_map.json, deck_v1.pptx, run_log.jsonl
- 45 tests passing (pytest tests/)

### After Phase 1

6. **Phase 2: LLM Planner**
   - `src/plan/`: Prompt templates + DeckIR generation (only after Phase 1 is stable)

7. **Phase 2: Critique + patch iteration**
   - `src/critique/`: Vision critic + PatchSet generation + applier
