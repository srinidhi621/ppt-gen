# PLAN.md — Composition Quality Recovery Plan

## 0) Objective

Move from "mechanically valid decks" to "consulting-grade visual storytelling" while keeping the current deterministic one-loop architecture.

## 1) Current Diagnosis

Working:
- full automated one-loop pipeline
- deterministic rendering and validation
- automated review image export
- quality gate enforcement
- consistent artifact/log chain

Still weak:
- composition sophistication
- overuse/repetition of branded images
- insufficient cue decomposition into meaningful visual structures
- limited layout vocabulary for image-heavy storytelling

## 2) Recovery Strategy

### Phase A — Cue-to-Visual Intent Modeling

Goal:
- convert raw cues into explicit visual intent types before asset selection.

Work:
1. Add deterministic cue intent classifier:
- `diagram_map`
- `ui_screenshot_mock`
- `icon_cluster`
- `hero_brand_image`
2. Add intent-aware planner constraints:
- intent must drive layout and asset type.
3. Persist per-slide intent in planner/composition artifacts.

Exit criteria:
- every slide has explicit visual intent;
- cue-rich slides are no longer collapsed to generic icon/image fallback.

### Phase B — Asset Selection Scoring and Diversity

Goal:
- improve relevance and avoid repeated "same image everywhere."

Work:
1. scoring model for asset selection:
- semantic relevance score
- repetition penalty
- slide-role weighting (hero vs support)
2. hard diversity constraints:
- max reuse count per single branded image
- minimum unique visual assets per 10-slide deck
3. separate pools:
- branded images for section/hero
- icons/diagrams for technical detail slides

Exit criteria:
- measurable increase in unique visual assets;
- reduced repeated branded-image saturation.

### Phase C — Composition Recipes per Archetype

Goal:
- make slide structure intentional, not placeholder-only population.

Work:
1. Add deterministic composition recipes for archetypes:
- `section_break`
- `technical_deep_dive`
- `comparison`
- `roadmap`
- `outcomes`
2. Add field-level hierarchy rules:
- title/body balance
- bullet density target
- image role (`hero`, `primary`, `secondary`, `accent`)
3. Extend renderer behavior where feasible within template constraints.

Exit criteria:
- composition specs show non-trivial role/placement patterns per archetype;
- visual + text hierarchy is consistent across runs.

### Phase D — Review Feedback Quality Loop Tuning

Goal:
- make reviewer feedback more composition-aware and less generic.

Work:
1. strengthen reviewer rubric for:
- visual relevance
- narrative coherence
- clutter/repetition penalties
2. improve planner V2 rework prompt with stricter "do-not-repeat" directives.
3. add reviewer-to-planner traceability in run summary.

Exit criteria:
- V2 outputs show meaningful visual/story improvements over V1, not only overflow reduction.

### Phase E — Benchmark and Acceptance Gates

Goal:
- lock objective acceptance thresholds for visual polish.

Work:
1. add benchmark set (including `legacy-system-navigator` and user-provided reference decks).
2. add hard KPIs:
- minimum visual density
- minimum unique visual assets
- max single-asset reuse
- overflow = 0
3. publish benchmark results into run artifacts.

Exit criteria:
- benchmark decks pass KPI gates consistently.

## 3) Immediate Next Implementation Slice

1. Implement Phase A cue-intent model.
2. Implement Phase B diversity constraints and scoring penalties.
3. Add KPI fields to `quality_gates_v2.json` and `run_summary.json`.
4. Re-run benchmark deck and inspect deltas.

## 4) Definition of Done (Quality Recovery)

Done when:
1. Decks are not only overflow-safe but also visually credible.
2. Visual intent is explicit and traceable per slide.
3. Asset selection is diverse and context-appropriate.
4. V2 materially improves story clarity and visual polish over V1 on benchmark runs.

