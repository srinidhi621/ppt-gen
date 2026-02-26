# PLAN.md — End-to-End Execution Plan

## 0) Objective
Build a reliable PPTX pipeline that:
- preserves corporate template fidelity,
- converts content into readable slides without overflow,
- uses visualization cues to place icons/images,
- supports future LLM planning/critique without breaking deterministic guarantees.

This plan reflects current feedback and execution order:
1. **P0 first (deterministic rebuild, no LLM)**
2. **LLM layer next**
3. **P1 quality improvements after LLM layer**
4. Review loop and productization after core quality is stable

---

## 1) Current State Snapshot

### 1.1 Completed and Working
- Template hardening complete (`assets/template/template.pptx`, alt-text placeholders).
- Layout catalog complete (`assets/layout/layout_catalog.json`).
- Deterministic renderer complete (`DeckIR -> PPTX`).
- Drift validation complete (`validate` command).
- Preflight validation/remediation complete (fit checks + pressure valve).
- Normalization complete (`content.md -> ContentModel`).
- CLI commands available: `validate`, `render`, `smoke`, `generate`.
- Combined markdown split flow exists in `generate`.
- Test suite is green (**50 passing**).

### 1.2 Confirmed Gaps from Latest Real Run
- Visual cues are not executed into visuals yet (icons/images not placed by cue hints).
- Icon metadata lacks semantic tags/synonyms for reliable cue-to-icon mapping.
- Truncation still relies heavily on ellipsis under pressure.
- First-slide parsing/layout assignment can under-utilize space for some inputs.

---

## 2) Principles for Next Steps

- **Determinism first:** Fix correctness and mapping in deterministic logic before LLM quality work.
- **Template-first always:** Keep using template layouts/placeholders, avoid custom manual styling.
- **Pressure valve over overflow:** Move excess detail to notes before forcing unreadable slides.
- **Artifact traceability:** Every transformation persists to `runs/<run_id>/`.
- **LLM as quality layer:** Introduce LLM only after deterministic foundation is robust.

---

## 3) Phase Roadmap (Updated)

| Phase | Focus | Status |
|------|-------|--------|
| 0 | Template/catalog hardening | DONE |
| 1 | Deterministic pipeline baseline | DONE |
| 2 (P0) | Deterministic rebuild for visual cues + parsing quality | NEXT |
| 3 | LLM layer (asset semantics + cues/planning) | AFTER P0 |
| 4 (P1) | Readability/space quality improvements | AFTER LLM LAYER |
| 5 | Vision critique + patch loop | LATER |
| 6 | Productization | LATER |

---

## 4) Phase 2 (P0) — Deterministic Rebuild (No LLM)

### 4.1 Goal
Make the pipeline reliably use provided cues and improve deterministic planning quality before adding LLM.

### 4.2 Workstream A: Input Robustness and Parsing
- Accept both strict and practical combined input formats:
  - `## Content` + `## Visualization Cues` (preferred)
  - tolerant handling for `Content`/`Visualization Cues`, unicode separators, and bullet variants.
- Fix first-slide title/subtitle heuristics so slide title is not lost/misassigned.
- Preserve section structure and IDs exactly from input where provided.

**DoD**
- No accidental title-to-subtitle swallowing on first content section.
- Real-world content files parse without manual cleanup.

### 4.3 Workstream B: Deterministic Cue Execution -> Visual Placement
- Extend deterministic planner to convert cues into `asset_refs`:
  - map `icon_hints` -> `icon_id` candidates,
  - map `image_hint` -> selected image/icon target,
  - populate `target_field_key` for image placeholders when layout supports it.
- Add fallback policy:
  - if no match: continue render without failing, log `VISUAL_CUE_UNRESOLVED`.
- Ensure renderer uses populated `asset_refs` as-is (already supported).

**DoD**
- At least one visual placed on slides with image-capable layouts and resolvable hints.
- Unresolvable cues are logged, not silent.

### 4.4 Workstream C: Icon Catalog Enrichment (Deterministic)
- Enrich `assets/icons/icons.json` with meaningful `tags` and `synonyms`.
- Add deterministic scoring for hint-to-icon matching (exact > synonym > token overlap).
- Add validation tests for mapping quality on a small benchmark set.

**DoD**
- Cue words like `shield`, `timeline`, `graph` resolve consistently to stable icon IDs.

### 4.5 Workstream D: Diagnostics and Tests
- Expand tests for:
  - combined input parsing variants,
  - first-slide title handling,
  - cue -> `asset_refs` generation,
  - unresolved cue logging.
- Add a smoke fixture with visuals expected in output DeckIR/render map.

**P0 Exit Criteria**
- `generate` from real client-style input produces PPTX with:
  - correct titles,
  - visible visuals where cues/layout allow,
  - zero hard failures when cues are partially unmatched.

---

## 5) Phase 3 — LLM Layer (After P0)

**Model assumption for this phase:** Gemini 3 Flash (initial default for speed/cost).

### 5.1 Stage A — Asset Semantic Enrichment (Primary Goal for Gap Closure)
- Goal: close metadata + asset-semantic coverage gap before relying on runtime cue mapping.
- Input set:
  - `assets/icons/png/*` (213 icon PNGs),
  - `assets/Icons and Dimensional Keywords/**/*.{png,jpg,jpeg,webp}`,
  - `assets/Ascendion Logos/**/*.{png,jpg,jpeg,webp}`.
- For each asset, Gemini 3 Flash should generate structured metadata:
  - `title` (short human name),
  - `tags` (5-15 concrete nouns/verbs),
  - `synonyms` (5-15 query variants),
  - `domains` (e.g., security, architecture, analytics, operations, finance),
  - `visual_type` (`icon`, `logo`, `photo`, `diagram`, `brand-illustration`),
  - `confidence` (0-1),
  - `usage_notes` (short placement guidance).
- Persist outputs:
  - `assets/catalog/asset_catalog_enriched.json`,
  - `runs/<run_id>/asset_tagging_report.json`.
- Human-in-the-loop:
  - low-confidence entries are flagged for manual review,
  - reviewed tags are fed back into canonical catalog.

**DoD (Stage A)**
- >=90% assets have non-empty semantic metadata.
- >=80% cue tokens in benchmark decks overlap catalog tags/synonyms.
- Catalog quality report is generated and versioned.

### 5.2 Stage B — LLM Entry Contract (Mandatory First Step for Deck Generation)
- Input may be:
  - combined markdown, or
  - plain content without cues.
- LLM stage must produce:
  - `content.md`
  - `cues.json`
- If cues are missing/weak, LLM infers visualization cues and writes `cues.json`.
- Persist both artifacts under `runs/<run_id>/`.

### 5.3 Stage C — LLM Planner Stage
- Convert normalized content + cues into schema-valid `DeckIR`.
- Respect allowed layouts/fields/icons only.
- During planning, resolve `icon_hints`/`image_hint` against enriched asset catalog.
- Bounded retries on schema invalid output only.

### 5.4 Guardrails
- Validate all LLM outputs against Pydantic schemas.
- Keep deterministic preflight + renderer unchanged as enforcement layers.
- Log `PLAN_DONE` with retries and validation status.
- For asset selection:
  - require confidence thresholds,
  - if below threshold, leave unresolved and log `VISUAL_CUE_UNRESOLVED`,
  - do not block render.

**Phase 3 Exit Criteria**
- Repeatable generation from plain content input to valid DeckIR without manual prep.
- Visual assets are selected for image-capable layouts in benchmark decks.
- Unresolved visual cues are explicit and measurable (not silent).

---

## 6) Phase 4 (P1) — Readability and Space Utilization

> Sequencing decision: execute this after LLM layer is available.

### 6.1 Goals
- Reduce ellipsis-heavy truncation.
- Improve space usage and layout suitability.
- Preserve meaning while fitting constraints.

### 6.2 Planned Improvements
- Add smarter remediation order:
  1. concise rewrite/compression,
  2. redistribute content across columns/fields,
  3. move overflow to notes,
  4. split slide when necessary (implement for real, not placeholder).
- Add density-aware layout fallback when hinted layout is too tight.
- Add explicit "headline + supporting bullets" shaping rules for title/image slides.

**Phase 4 Exit Criteria**
- Fewer hard truncations and better visual balance on first-pass deck.

---

## 7) Phase 5 — Review Loop (Vision Critique + Patch)

- Manual image export remains MVP default.
- Critique model produces structured findings (S0-S3).
- Patch planner applies pressure-valve-first edits.
- Re-render up to max 2 iterations.

**Exit Criteria**
- Typical decks clear S0/S1 in <= 2 iterations.

---

## 8) Operational Commands (Current and Target)

### Current
- `python -m src.cli validate`
- `python -m src.cli render --deckir <path>`
- `python -m src.cli smoke --deckir <path>`
- `python -m src.cli generate --input <combined.md>`

### After Phase 3+
- `generate` supports plain content input by auto-producing `content.md` + `cues.json`.
- Add dedicated commands as needed: `critique`, `patch-and-render`, `full-run`.

---

## 9) Risks and Mitigations (Updated)

| Risk | Mitigation |
|------|------------|
| Cue hints do not map to visuals | Gemini-assisted catalog enrichment + deterministic matcher + unresolved logging |
| Over-truncation hurts readability | Move P1 shaping after LLM layer + implement true split-slide |
| Layout hint mismatch to text density | Add density-aware fallback policy |
| Parsing ambiguity in real client files | Tolerant parser + strict normalized artifacts in runs |
| Template drift | Keep startup drift validation as hard gate |

---

## 10) Immediate Next Action (Approved Sequence)

**NEXT: Execute Phase 2 (P0) now, no LLM.**

### P0 Sprint Checklist
1. Fix first-slide title/subtitle parsing behavior.
2. Add tolerant combined-input parsing normalization.
3. Implement deterministic cue -> `asset_refs` mapping.
4. Enrich icon metadata tags/synonyms and add matching tests.
5. Run end-to-end on `legacy-system-navigator` and confirm visuals appear.

After this is done: start **Phase 3 LLM layer** in this order:
1. Stage A: asset semantic enrichment (Gemini 3 Flash),
2. Stage B: content/cues separation and cues inference,
3. Stage C: DeckIR planning with enriched catalog,
then move to **Phase 4 (P1)**.

---

## 11) Success Metrics

- Visual placement success rate on cue-provided slides.
- Number of unresolved cues per run.
- Number of truncation events per deck.
- S0/S1 issues in post-render review.
- Time-to-first-usable deck from raw input.
