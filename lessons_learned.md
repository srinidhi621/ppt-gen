# Lessons Learned — PPT-Gen Retrospective

## 1) Executive Summary

We built a robust pipeline, but not a robust slide composer.

What we achieved:
- deterministic pipeline orchestration
- reliable artifact/log generation
- one-loop review/rework automation
- overflow prevention and rendering stability

What we did not achieve:
- consulting-grade slide composition quality
- semantically strong visual selection
- narrative visual hierarchy (what to show where, and why)

Bottom line:
- The project did not fail because `python-pptx` cannot render.
- It failed because composition intelligence and quality objectives were under-specified, under-tested, and under-enforced.

## 2) Evidence from Our Runs

### Early one-loop run (`e2e_quality_gates_20260227`)
- Overflow: `2 -> 0` (improved)
- Images rendered: `3 -> 3` (no visual improvement)
- Quality gates: `PASS`

Interpretation:
- Gates validated technical correctness but did not measure design quality.
- We accepted a deck that still looked weak.

### Forced visual-density runs
- `e2e_material_improvement_20260227`: 10/10 slides visualized, overflow fixed.
- `e2e_material_improvement_v2_20260227`: 10/10 slides visualized, overflow fixed, image diversity improved slightly.

Interpretation:
- We improved coverage, but drifted into branded-image overuse.
- Better metrics, still not the target polish.

### Slide-specific failure pattern (Tier 1 X-Ray)
- Cue intent was rich (`map + entity network + chat UI + citations`).
- System often collapsed this to a generic icon/image fill, not a purposeful technical visual.

Interpretation:
- Cue parsing and composition intent translation are still shallow.

## 3) What Worked

1. Pipeline reliability
- End-to-end automation now works.
- Structured artifacts and logs improved debuggability.

2. Deterministic validation and rendering
- Preflight/remediation reduced overflow consistently.
- Renderer behavior is predictable.

3. Review-loop plumbing
- V1 -> review -> V2 control flow works.
- Diagnose output is machine-readable and reusable.

4. Asset integration foundation
- Large asset catalogs are available and addressable.
- Concept-based vocabulary abstraction is directionally correct.

## 4) What Failed

1. Composition was treated as a side effect
- We optimized for filling placeholders, not for designing slides.
- “Has image” became a proxy for quality.

2. Quality gates were initially too weak
- Gates validated absence of hard errors, not presence of good design.
- This caused false confidence.

3. Planner objectives were ambiguous
- Planner had weak constraints around visual role, narrative structure, and layout intent.
- Rich cues were often flattened into simplistic visuals.

4. Layout system was under-leveraged
- Limited image-capable layouts + weak relayout strategy.
- Forced fixes increased coverage but also increased visual sameness.

5. Asset retrieval focused on availability, not fitness
- Retrieval was too easy to satisfy with repeated branded assets.
- Relevance and diversity constraints came late.

6. We lacked a benchmark-first discipline
- No “gold” reference set + rubric at the start.
- No objective design-quality acceptance gate early in development.

## 5) Root Causes (System-Level)

1. Wrong optimization target
- We optimized pipeline completion and schema validity first.
- We should have optimized composition quality first.

2. Missing explicit composition model
- No strong intermediate “design intent” contract (visual roles, emphasis, hierarchy, scene type).
- Without this, rendering became mechanical.

3. Review loop not anchored to design rubric
- Reviewer could flag issues, but patch strategy lacked strong compositional priors.

4. Insufficient separation of concerns
- Content planning, visual retrieval, and composition decisions were too intertwined.
- Hard to debug which stage degraded quality.

## 6) Anti-Patterns to Avoid Next Time

1. “Coverage equals quality”
- Avoid metrics like “all image placeholders filled” as primary success criteria.

2. “One LLM pass decides everything”
- Separate story planning from composition planning.

3. “Fallback-first architecture”
- Repeated fallback paths (generic icon, generic branded image) degrade design quickly.

4. “No benchmark, no target”
- Never iterate on subjective quality without fixed references and scorecards.

## 7) If We Restart (Option A), How to Build It Right

### A) Product goal first
Define target quality as:
- executive readability
- clear visual hierarchy
- visual relevance per slide
- controlled density
- low repetition

### B) Architecture split (mandatory)
1. Story Planner (LLM)
- decides slide narrative and key messages only.

2. Composition Planner (LLM + strict schema)
- decides archetype, visual intent, layout family, and role map.
- output is design intent, not raw asset IDs.

3. Deterministic Composer
- maps intent -> concrete layout + slots + text budgets + visual roles.

4. Asset Ranker (deterministic + embeddings)
- ranks candidates by semantic fit, role suitability, and repetition penalty.

5. Renderer
- executes composed plan only.

6. Reviewer/Rework
- critiques against explicit rubric and proposes targeted deltas.

### C) New core contracts
Add strong intermediate specs:
- `StorySpec` (message hierarchy)
- `CompositionIntentSpec` (archetype + visual intent + role map)
- `AssetSelectionSpec` (ranked candidates + rationale + diversity penalties)
- `RenderPlanSpec` (deterministic placement and constraints)

### D) Benchmark-first development
Before coding advanced logic:
1. Build 30-50 “gold” slides (including your reference deck style).
2. Define scorecard:
- visual relevance
- hierarchy
- density
- repetition
- overflow
3. Ship only when benchmark pass threshold is met.

### E) Quality gates v2 (real quality, not just validity)
Required final gates:
1. Overflow: zero blocking
2. Visual relevance score threshold
3. Repetition cap per asset
4. Minimum unique visual assets per deck
5. Intent adherence (cue -> visual intent trace)
6. Human-judge sample pass rate on benchmark set

## 8) Practical Rebuild Plan (Phased)

### Phase 0 — Freeze and benchmark
- Freeze current repo as baseline.
- Build benchmark dataset and scoring rubric.

### Phase 1 — Composition intent layer
- Implement `CompositionIntentSpec`.
- Train/prompt planner to output intent, not direct assets.

### Phase 2 — Asset ranker
- Add semantic retrieval + role-aware ranking + diversity penalties.

### Phase 3 — Deterministic composer
- Implement recipe-driven slide assembly by archetype:
  - section opener
  - deep technical “x-ray”
  - comparison
  - process/roadmap
  - outcomes

### Phase 4 — Review-driven patching
- Restrict patches to intent-level and ranker-level adjustments.
- Avoid broad planner rewrites unless necessary.

### Phase 5 — Acceptance and hardening
- Require benchmark pass thresholds before rollout.

## 9) Key Takeaways

1. Pipeline engineering is necessary but not sufficient.
2. Composition must be a first-class system, not an emergent side effect.
3. Strong contracts and deterministic steps should surround composition decisions, not replace them.
4. If we start over, success depends on benchmark-driven composition quality from day one.

