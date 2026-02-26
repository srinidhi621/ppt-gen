# PLAN.md — Execution Plan

## 0) Objective

Build a PPTX generation pipeline that produces **professional, visually polished decks** from Markdown content + visualization cues, using a corporate PowerPoint template and a curated asset library.

Current prioritization note: **MCP/diagram-compiler integration is deferred** until core visual quality and asset-selection reliability targets are met.

---

## 1) What Is Done

### Infrastructure (all working, tested)
- Template hardened with alt-text placeholders (`assets/template/template.pptx`).
- Layout catalog with 12 MVP layouts and fit constraints (`assets/layout/layout_catalog.json`).
- Deterministic renderer: DeckIR → PPTX via alt-text placeholder binding.
- Template drift validation blocks mismatches at startup.
- Preflight validation + remediation (pressure valve to notes, bullet trimming).
- Markdown parser: `content.md` → `ContentModel` with stable section IDs.
- Combined markdown splitter: `## Content` + `## Visualization Cues` → content + cues.
- CLI: `validate`, `render`, `smoke`, `generate`.

### LLM Integration (wired but underperforming)
- Provider-agnostic LLM client (`src/llm/`): Gemini live, Azure OpenAI adapter ready.
- `generate --planner llm` produces schema-valid DeckIR with bounded retries.
- Per-run telemetry: tokens, cost (USD + INR), usage artifacts.
- 65 tests passing.

### Asset Library (large but disconnected from pipeline)
- **28,926 PNG icons** render-ready across 5 packs:
  - 213 Ascendion branded icons (converted from SVG, **no semantic tags — quality: low**).
  - 19,401 Fluent UI, 5,928 Tabler, 1,542 Lucide, 1,842 AWS.
- **71 branded images**: Ascendion logos + 12 "Dimensional Keyword" illustration sets (Break Barriers, Transform Reality, Unlock New Possibilities, etc.) each in 5 color variants.
- Asset catalog built (`assets/catalog/asset_catalog.json`, 30,771 entries).
- Token-overlap matcher exists (`match_asset()`).

---

## 2) The Quality Gap (Why Output Looks Barebones)

Current output from a real LLM run: **8 of 10 slides have zero visuals.** The 2 slides that do have icons picked irrelevant AWS architecture icons. No branded images appear anywhere. Markdown bold markers (`**text**`) render as literal asterisks.

### Root causes, in order of impact:

**G1 — The LLM has no usable visual vocabulary.**
The planner prompt dumps 400 raw icon IDs like `aws:Architecture-Service-Icons_01302026_Arch_...`. The LLM cannot reason about what these icons depict, so it either picks randomly or gives up and emits `asset_refs: []`.

**G2 — Cues are not reaching the planner.**
In real runs the `cues.json` reaching the LLM is `{"cues": []}`. The rich `icon_hints` and `image_hint` data from the combined markdown is lost during the split or not forwarded when the input is plain `content.md`.

**G3 — No semantic bridge between concepts and 30K icons.**
`match_asset("security", ...)` with `min_score=1` across 30,700 entries returns near-random results. There is no curated concept-to-icon mapping. Single-word hints have low discriminatory power.

**G4 — Branded images are invisible to planning.**
The Dimensional Keyword illustrations (ideal for title/section slides) have only tokenized filename tags. The planner has no guidance on when or how to use them.

**G5 — 213 internal branded icons have zero metadata.**
They are in the catalog as `quality: low` with no tags or synonyms. Completely unusable for matching.

**G6 — Markdown formatting leaks into PowerPoint.**
The renderer places raw text including `**bold**` markers without parsing them into formatted runs.

---

## 3) Next Phase: Visual Polish (the path to acceptable output)

Goal: a 10-slide deck generated from combined markdown input should have **icons or branded images on every slide that supports them**, no Markdown artifacts in text, and sensible layout choices driven by cues.

### Step 1 — Fix Markdown rendering in text `[quick fix]`

Strip `**bold**` / `*italic*` markers from text before placing it in PowerPoint, or convert them to bold/italic text runs via python-pptx. This is a renderer-only change.

**DoD:** No literal `**` or `*` in rendered slide text. Bold markers apply actual bold formatting.

### Step 2 — Fix cue forwarding `[quick fix]`

Ensure that when the combined markdown includes `## Visualization Cues` with `icon_hints`, `image_hint`, and `layout_hint`, those cues arrive intact in the planner (both deterministic and LLM paths). Also ensure that when `generate` is called with `--planner llm`, the cues are included in the user prompt.

**DoD:** Run with `legacy-system-navigator.combined.md` → `cues.json` in run folder contains all 10 cue entries with their icon_hints and image_hints intact. LLM prompt includes full cue data.

### Step 3 — Build the Visual Vocabulary `[core enabler]`

Create `assets/catalog/visual_vocabulary.json` — a curated, compact mapping from ~200-300 human concepts to specific icon picks:

```
{
  "concepts": {
    "security": {
      "preferred": "lucide:shield",
      "alt": ["tabler:lock", "fluent:shield-checkmark-24-regular"],
      "domains": ["governance", "compliance", "protection"]
    },
    "analytics": {
      "preferred": "lucide:bar-chart-3",
      "alt": ["tabler:chart-bar", "fluent:data-trending-24-regular"],
      "domains": ["data", "bi", "reporting"]
    },
    "timeline": {
      "preferred": "lucide:calendar-clock",
      "alt": ["tabler:timeline"],
      "domains": ["planning", "roadmap", "schedule"]
    },
    ...
  }
}
```

**How to build it:**
1. Extract distinct tag sets from each icon pack (Lucide, Tabler, Fluent, AWS).
2. Use an LLM call to cluster tags into ~200-300 concepts and pick the best icon per pack per concept, prioritizing Lucide (cleanest aesthetic) as `preferred`.
3. Human-review the output. Persist as a versioned catalog file.

**DoD:** Vocabulary file exists. Resolver function can take a concept string and return a valid, render-ready icon path. Coverage: common business/tech cue words (security, cloud, data, growth, risk, speed, team, integration, ai, etc.) all resolve.

### Step 4 — Tag the 213 branded icons with Gemini Vision `[asset unlock]`

Send each `icon_*.png` to Gemini Vision, get back structured tags:
- `title`: short human name ("handshake", "network hub", "rising graph")
- `tags`: 5-15 descriptive nouns/verbs
- `synonyms`: query variants
- `domains`: applicable business contexts
- `confidence`: 0-1

Merge results into `icons.json` and regenerate the asset catalog. Flag low-confidence entries for manual review.

**DoD:** >=90% of the 213 icons have meaningful tags. They appear as `quality: high` in the catalog.

### Step 5 — Build branded image catalog with thematic guidance `[asset unlock]`

Create `assets/catalog/branded_images.json` mapping the Dimensional Keyword illustrations to slide contexts:

```
{
  "images": {
    "transform_reality": {
      "theme": "modernization, digital transformation, change",
      "use_on": ["title_image_light", "section_break_light"],
      "color_preference": {"light_theme": "Teal", "dark_theme": "White"},
      "paths": {
        "Teal": "Icons and Dimensional Keywords/Transform Reality/PT_TransformReality_Teal.png",
        "Purple": "...", "Pink": "...", "Yellow": "...", "White": "..."
      }
    },
    "break_barriers": {
      "theme": "overcoming challenges, disruption, problems to solve",
      "use_on": ["title_image_light", "content_image_light", "section_break_light"],
      ...
    },
    "unlock_new_possibilities": {
      "theme": "innovation, solutions, opportunities, capabilities",
      ...
    },
    "software_to_power_growth": {
      "theme": "platform, technology, engineering, building",
      ...
    },
    "outmaneuver_risk": {
      "theme": "risk management, security, governance, compliance",
      ...
    },
    ...
  }
}
```

**DoD:** All 12 Dimensional Keyword sets are cataloged with themes and layout guidance. Resolver function can pick an appropriate image given a slide's content/cue context.

### Step 6 — Redesign the LLM planner prompt `[the big lever]`

Replace the current prompt (which dumps raw icon IDs) with a structured prompt that gives the LLM actual design agency:

**System prompt provides:**
1. The visual vocabulary (concepts, not raw IDs) — "pick concepts, the pipeline resolves to icons."
2. The branded image catalog with themes — "for section breaks and hero slides, pick a branded image by theme."
3. Layout selection guidance: when content has visual cues → pick image-bearing layouts; when content is dense text → pick content-only layouts.
4. Hard rule: every layout with `ph_image` MUST have an `asset_ref`. No empty image placeholders.
5. 2-3 worked examples of good slide specs with well-chosen layouts + asset_refs.

**User prompt provides:**
1. ContentModel sections (as today).
2. Full cue data: `icon_hints`, `image_hint`, `layout_hint`, `notes` — prominently, not buried.
3. deck_id, run_id, template_id.

**Post-LLM resolution step:**
After the LLM returns a DeckIR with concept-level visual references, a deterministic resolver:
- Maps concept names → actual icon_ids using the visual vocabulary.
- Maps branded image theme names → actual file paths using the branded image catalog.
- Validates all resolved paths exist and are renderable PNGs.

**DoD:** LLM-generated DeckIR from `legacy-system-navigator.combined.md` has asset_refs on every image-capable slide. Icons are relevant to slide content. At least 2 slides use branded Dimensional Keyword images.

### Step 7 — Post-planning visual fill (safety net) `[deterministic fallback]`

After the planner (LLM or deterministic) emits a DeckIR, run a deterministic sweep:
- For any slide with `ph_image` in its layout but no `asset_refs` → attempt resolution:
  1. Check cues for `icon_hints` / `image_hint` → resolve via vocabulary or branded catalog.
  2. Fall back to content keyword extraction → resolve via vocabulary.
  3. For `section_break_light` / `title_image_light` with no match → pick a branded image by content-theme similarity.
- Log every unresolved visual as `VISUAL_CUE_UNRESOLVED` with the search terms attempted.

**DoD:** Zero empty `ph_image` placeholders on rendered slides when the asset library has a plausible match. All unresolved cues are logged.

---

## 4) After Visual Polish: Readability & Space (P1)

Only after the visual layer is working:

- Replace ellipsis-heavy truncation with LLM-assisted concise rewriting.
- Density-aware layout fallback (auto-switch from `two_content` to `one_content` when text overflows).
- Implement real slide splitting (not just pressure valve to notes).
- "Headline + supporting bullets" shaping for title/image slides.

**Exit criteria:** First-pass decks have fewer than 2 truncation events per 10-slide deck.

---

## 5) Later Phases

| Phase | Focus | Status |
|-------|-------|--------|
| Review loop | Vision critique (S0-S3) + patch planner + re-render (max 2 iterations) | LATER |
| Cue inference | LLM generates `cues.json` when input has none | LATER |
| Azure OpenAI | Live validation of Azure provider path | LATER |
| MCP diagram integration | `diagram-MCP-spec.md` implementation (`drawio-mcp` + batch renderer) | DEFERRED |
| Productization | Error handling hardening, CI, packaging | LATER |

---

## 6) CLI Commands

```bash
# Validate template against layout catalog
python -m src.cli validate

# Render from hand-authored DeckIR
python -m src.cli render --deckir <path>

# Deterministic smoke test
python -m src.cli smoke --deckir <path>

# Full pipeline (deterministic planner)
python -m src.cli generate --input <combined.md>

# Full pipeline (LLM planner)
python -m src.cli generate --input <combined.md> --planner llm --llm-provider gemini
```

---

## 7) Success Criteria for "Acceptable Polish"

A 10-slide deck generated from `legacy-system-navigator.combined.md` should:
- [ ] Have icons or branded images on every slide whose layout supports `ph_image`.
- [ ] Use at least 2 different Dimensional Keyword branded images (for title/section slides).
- [ ] Have zero literal `**` or `*` Markdown artifacts in rendered text.
- [ ] Apply bold formatting where Markdown bold was intended.
- [ ] Have layout choices that match content density (not cramming 3-column content into a layout with no columns).
- [ ] Have all cue `icon_hints` and `image_hint` values attempted for resolution (with unresolved ones logged).
- [ ] Open cleanly in PowerPoint on macOS with template theme preserved.
