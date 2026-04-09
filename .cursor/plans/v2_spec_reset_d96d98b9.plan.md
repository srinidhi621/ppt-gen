---
name: V2 Spec Reset
overview: "Revise the V2 architecture and execution plan so the system is recipe-first, asset-aware, and physically credible in PowerPoint, while preserving the strongest parts of the current direction: template-first rendering, deterministic validation, and a bounded multimodal review loop."
todos:
  - id: reset-contract
    content: Redefine the composition contract in SPEC so the model outputs recipe/slot intent, not absolute coordinates.
    status: pending
  - id: layout-physics
    content: Add text measurement, overflow, solver precedence, connector scope, and OOXML boundary rules to the spec.
    status: pending
  - id: asset-first
    content: Promote existing component, asset, and visual vocabulary catalogs into first-class architecture inputs.
    status: pending
  - id: review-bounds
    content: Rewrite review/repair semantics so review is bounded, convergence-aware, and not the source of geometric truth.
    status: pending
  - id: plan-resequence
    content: Resequence PLAN to prove rendering physics before richer AI orchestration and broader archetype coverage.
    status: pending
isProject: false
---

# V2 Spec Reset Plan

## Goal

Refactor the target architecture in [SPEC-v2.md](/Users/Srinidhi/my_projects/ppt-gen/SPEC-v2.md) and the delivery sequence in [PLAN.md](/Users/Srinidhi/my_projects/ppt-gen/PLAN.md) so the project stops trying to make the model act like a blind coordinate planner and instead uses:

- LLMs for narrative intent, archetype selection, recipe selection, and slot assignment
- deterministic code for layout solving, sizing, routing, and rendering
- existing catalogs in [assets/catalog/component_catalog_v1.json](/Users/Srinidhi/my_projects/ppt-gen/assets/catalog/component_catalog_v1.json), [assets/catalog/visual_vocabulary.json](/Users/Srinidhi/my_projects/ppt-gen/assets/catalog/visual_vocabulary.json), [assets/catalog/planner_policy_v1.json](/Users/Srinidhi/my_projects/ppt-gen/assets/catalog/planner_policy_v1.json), and [assets/layout/layout_catalog.json](/Users/Srinidhi/my_projects/ppt-gen/assets/layout/layout_catalog.json) as the backbone for visual recipes and asset routing.

## Recommended Architecture Shift

The biggest spec change should be a contract reset:

- Replace LLM-owned `bounds` in `SlideElementPlan` with recipe/slot intent, relative ordering, importance, and content binding.
- Make the deterministic engine the sole owner of final coordinates, text fitting decisions, and connector routing.
- Narrow the initial composed path to recipe instantiation, not open-ended free composition.
- Treat the review loop as advisory for polish and narrative fit, not authoritative for geometric truth.

```mermaid
flowchart LR
    intake[IntakeAndCues] --> blueprint[DeckBlueprint]
    blueprint --> brief[SlideBrief]
    brief --> route[RouteDecision]
    route --> recipe[RecipeAndSlotPlan]
    recipe --> measure[TextMeasurementAndSizing]
    measure --> solve[DeterministicLayoutSolve]
    solve --> render[NativePptxRender]
    render --> diagnose[DeterministicDiagnostics]
    diagnose --> review[VisualReview]
    review --> repair[BoundedRepairPlan]
    repair --> solve
```



## What To Change In The Spec

### 1. Redefine the planning/rendering contract

Update [SPEC-v2.md](/Users/Srinidhi/my_projects/ppt-gen/SPEC-v2.md) sections around element composition, renderer responsibilities, and repair so that:

- the planner outputs `SlideIntentPlan` / `RecipePlan` / slot assignments instead of absolute `bounds`
- layout primitives are declared per recipe with deterministic sizing rules
- reroute and fallback behavior is explicit when a recipe cannot satisfy text or density budgets
- `template_native` vs `composed` routing uses deterministic criteria instead of planner preference alone

This directly addresses the current conflict between `SlideElementPlan.bounds` and the claimed `layout_solver`.

### 2. Add a real layout-physics section

Add an explicit subsystem to [SPEC-v2.md](/Users/Srinidhi/my_projects/ppt-gen/SPEC-v2.md) for:

- text measurement heuristics or measurement backends
- overflow policies by element type
- solver precedence rules when constraints conflict
- connector scope limits for MVP
- grouping policy and OOXML escalation boundaries

The current solver section is too small for the kinds of diagrams the spec promises.

### 3. Collapse “general-purpose composed slides” into bounded recipe families

Revise the composed path to start with a small set of recipe families:

- executive summary cards / split-hero
- comparison columns
- roadmap timeline / swimlane
- process flow
- architecture diagram variants such as layered stack and left-to-right pipeline

Use [assets/catalog/component_catalog_v1.json](/Users/Srinidhi/my_projects/ppt-gen/assets/catalog/component_catalog_v1.json) as the seed library rather than inventing a blank-slate visual grammar.

### 4. Make the asset pipeline a first-class differentiator

Promote the repo’s existing asset/catalog work into core architecture:

- explicit provider/logo/icon routing
- concept-to-icon mapping via [assets/catalog/visual_vocabulary.json](/Users/Srinidhi/my_projects/ppt-gen/assets/catalog/visual_vocabulary.json)
- branded image reuse and diversity policy via [assets/catalog/planner_policy_v1.json](/Users/Srinidhi/my_projects/ppt-gen/assets/catalog/planner_policy_v1.json)
- recipe-specific asset requirements and icon style consistency

This is the clearest way to outperform Claude’s generic icon/tooling limitations.

### 5. Narrow and harden the review loop

Revise [SPEC-v2.md](/Users/Srinidhi/my_projects/ppt-gen/SPEC-v2.md) so multimodal review:

- scores message clarity, hierarchy, aesthetic balance, and brand fit
- does not own micro-alignment truth when preview fidelity is uncertain
- has strict convergence rules, bounded editable fields, and accept-with-warnings outcomes
- distinguishes PowerPoint-fidelity issues from headless-render artifacts

### 6. Add template-compatibility and fallback classes

The current template-first stance is right, but the spec should classify templates into compatibility tiers:

- strong template support
- partial token extraction only
- blank-canvas-with-theme fallback

That keeps the promise realistic across messy customer templates.

## What To Change In The Plan

Update [PLAN.md](/Users/Srinidhi/my_projects/ppt-gen/PLAN.md) to expose the hardest risks earlier and reduce speculative work:

- split the current S2 into a deterministic rendering-physics slice first, then AI composition on top
- move text measurement and slot-based recipe instantiation ahead of richer planner/runtime work
- defer broad repair-loop ambition until one composed slide renders correctly without visual thrash
- make the first proof point “one ugly but physically correct composed slide,” then “one polished recipe-backed slide”
- delay broad archetype expansion until at least one connector-bearing recipe is stable

Recommended revised sequence:

1. Template compatibility + token extraction audit
2. Text measurement + slot sizing spike
3. One recipe instantiated deterministically from mock data
4. One AI-generated recipe/slot plan on top of that renderer
5. One bounded review/repair loop
6. Expand recipes/archetypes gradually

## Objective Assessment

The repo is already ahead of Claude-for-PowerPoint in a few important ways:

- It has a stronger template-first philosophy than Claude’s raw OOXML-on-empty-canvas workflow.
- It already has asset, component, and policy catalogs that can become a recipe/asset intelligence layer.
- It already plans a review loop and quality gates, which is directionally better than a blind verifier-only architecture.

But the current spec is also still over-ambitious in ways Claude’s transcript helps expose:

- Claude’s biggest weakness is spatial blindness; your current spec still leaves too much spatial authority with the model.
- Claude defaults to uniform grids because blind coordinate math is brittle; your spec risks the same failure unless recipes and slots dominate.
- Claude’s icon weakness is solvable with your asset catalogs, but only if the asset-routing contract is made central, not peripheral.
- Claude’s review loop is weak because it sees only textual critiques; your planned review loop is better, but only if it is bounded and not asked to repair geometry that the deterministic layer should have prevented.

## Deliverables

The rewrite should produce:

- a revised [SPEC-v2.md](/Users/Srinidhi/my_projects/ppt-gen/SPEC-v2.md) with new planning/rendering contracts, bounded recipe-first composed path, and explicit measurement/review semantics
- a revised [PLAN.md](/Users/Srinidhi/my_projects/ppt-gen/PLAN.md) with earlier proof of physical feasibility and narrower initial scope
- a short consistency pass over [README.md](/Users/Srinidhi/my_projects/ppt-gen/README.md) so operational docs no longer lag the target architecture

