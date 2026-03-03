# Architecture Review Prompt (SPEC-v2 Aligned)

Status (`2026-03-02`):
- V2 planning metadata scaffolding is now partially implemented (component catalog + planner policy wired into planner prompt).
- This review prompt remains focused on architecture-level stress testing for the full V2 rollout.

You are a senior software architect conducting an independent technical review.
Be rigorous, objective, and non-sycophantic.
Do not praise the plan. Stress-test it.

For every design choice listed below, evaluate:
- whether the reasoning holds,
- whether alternatives were dismissed fairly,
- what failure modes are underestimated,
- and what you would do differently.

---

## Context: The Project

We are building an AI-powered presentation generator (Gamma-like outcome, not necessarily Gamma-like architecture).
Input is markdown/text.
Output must be a **fully native, editable `.pptx`**.
Users must be able to manually edit text boxes, shapes, diagrams, connectors, and charts in PowerPoint.

Hard constraints:
- Must preserve and use **company-branded `.pptx` templates** (masters, color themes, font themes, layouts).
- Non-LLM runtime dependencies must be **zero-cost and locally installable** (open-source or proprietary-but-free are both acceptable if license-safe for intended use).
- Paid usage is allowed only for:
  - coding assistants used during development,
  - LLM inference used by the planning/review pipeline.
- Must retain deterministic validation/remediation and artifact logging under `runs/<run_id>/`.

---

## Context: V1 (What Failed)

V1 used Python + `python-pptx` + LLM planning.
It worked end-to-end but produced low-polish decks.

Observed failures:
- placeholder filling behaved like form entry, not design composition,
- text overflow due to weak pre-layout reasoning,
- no true diagram composition from native shapes,
- repetitive image reuse,
- narrow layout vocabulary.

V1 strengths preserved:
- deterministic pipeline structure,
- Pydantic contracts,
- remediation and quality gates,
- review loop,
- logging and tests.

---

## Context: Current SPEC-v2 Direction

The current spec keeps Python rendering, adds a bounded custom layout solver, introduces a component library, and uses a hybrid route (`template_native` + `composed`).

Major updates in the latest spec:
- zero-cost local dependency policy is explicit,
- planner architecture changed to **single model, two-pass orchestration**,
- solver scope now has explicit escalation thresholds,
- schema versioning and migration controls are defined,
- timeline revised from 10 weeks to **12–14 weeks**.

---

## The Plan Under Review

### Design Choice 1: Keep Python + `python-pptx` as the rendering core

**Reasoning given:**
Template import/edit/preservation is mandatory, and `python-pptx` is the practical zero-cost local anchor for native PPTX generation with editable objects.

**Alternatives considered:**
- JS PPTX generators/wrappers (insufficient template-edit parity)
- Java/POI split-stack
- direct OOXML-heavy implementation

**Questions for the reviewer:**
- Is this the best zero-cost local baseline, or should a different renderer be primary?
- Are `python-pptx` limitations likely to block polish goals?
- Is the proposed OOXML bridge layer the right containment strategy?

---

### Design Choice 2: Bounded custom geometry solver (not full Flexbox)

**Reasoning given:**
Slides are fixed-size canvases; responsive CSS semantics are unnecessary.
Solver primitives are limited to `inset`, `split_h`, `split_v`, `grid`, `flow`, `center`.
Scope guards and escalation thresholds are defined.

**Alternatives considered:**
- Yoga/Flexbox engines
- constraint solvers (Cassowary/Kiwi) from the start

**Questions for the reviewer:**
- Are the scope boundaries realistic in practice?
- Are escalation thresholds concrete enough to prevent solver sprawl?
- Which slide patterns are likely to break this model first?

---

### Design Choice 3: Smart component library with strict payload limits

**Reasoning given:**
Composition quality comes from reusable, theme-aware components rendering native shapes in bounded regions.
Each component has size constraints, payload validation, and remediation policies.

**Alternatives considered:**
- expanding template-only approach
- generic freeform shape generation without typed components

**Questions for the reviewer:**
- Is this abstraction level correct, or too rigid/too loose?
- How likely is schema-valid but visually poor output to dominate?
- Are the remediation policies enough to avoid degenerate slides?

---

### Design Choice 4: Hybrid routing (`template_native` + `composed`)

**Reasoning given:**
Simple slides keep designer-tuned template quality; complex slides use composition.
A style-consistency gate is added to reduce visual discontinuity.

**Alternatives considered:**
- all-template
- all-composed

**Questions for the reviewer:**
- Does this create unavoidable quality discontinuity?
- Is route classification robust enough?
- Does this double the bug/test surface in a way that outweighs benefits?

---

### Design Choice 5: Single model family, two-pass planner orchestration

**Reasoning given:**
Reject both extremes:
- one giant monolithic planning call (too brittle),
- many role agents with long dependency chains (too much coordination overhead).

Adopt two deterministic passes:
- Pass A: slide skeleton (arc, archetypes, route, components, intent)
- Pass B: per-slide payload fill (text budgets, assets, component data)

**Alternatives considered:**
- single-call full AST planning
- multi-agent role pipeline

**Questions for the reviewer:**
- Is this the best reliability/latency tradeoff for the chosen LLM backend (API or self-hosted)?
- What failure modes emerge between Pass A and Pass B consistency?
- Should any pass be deterministic/non-LLM instead?

---

### Design Choice 6: PPTX-derived image preview (no dual renderer)

**Reasoning given:**
PPTX remains source of truth; preview uses `soffice -> pdf -> png`.
Avoids long-term fidelity drift of parallel HTML/canvas renderer.

**Alternatives considered:**
- dual renderer (web + pptx)
- Office Online embedding / hosted office stacks

**Questions for the reviewer:**
- Is this acceptable as an MVP ceiling, or a UX dead-end?
- At what scale does `soffice` become the bottleneck?
- Are cache + async worker mitigations enough?

---

### Design Choice 7: Evolutionary migration with anti-coupling controls

**Reasoning given:**
Preserve V1 modules and artifacts where possible, but separate V2 schema and render paths to avoid monolith drift.

Controls include:
- `DeckIR v2` versioning,
- side-by-side readers during migration,
- explicit decommission plan for V1-only paths.

**Alternatives considered:**
- full rewrite

**Questions for the reviewer:**
- Will migration still accumulate accidental coupling?
- Is the decommission strategy concrete enough to prevent permanent dual-maintenance?
- Is schema compatibility strategy sufficiently robust?

---

### Design Choice 8: Revised timeline and delivery model (12–14 weeks)

**Reasoning given:**
10 weeks was optimistic; 12–14 weeks is set for AI-agent-driven implementation with buffer for performance hardening and polish.

**Questions for the reviewer:**
- Is 12–14 weeks still optimistic given component polish and review-loop tuning?
- Where are the true critical path bottlenecks?
- Which milestones are most likely to slip first?

---

## Your Deliverables

1. **Per-choice verdict:**
For each of the 8 design choices, mark `agree`, `partially agree`, or `disagree`, with concrete technical justification.

2. **Top 3 underestimated risks:**
What will fail first during real implementation and why?

3. **One override recommendation:**
If you can override exactly one design choice, which one and why?

4. **Missing concerns:**
Identify critical gaps still not sufficiently addressed, especially:
- visual testing strategy robustness,
- performance profiling methodology,
- accessibility and localization realism,
- error recovery UX,
- component catalog versioning,
- backward compatibility for DeckIR schema evolution.

5. **Timeline sanity check:**
Assess whether 12–14 weeks is credible for AI-agent-authored code, and identify likely bottlenecks and sequencing fixes.

6. **Decision-quality check:**
Call out where reasoning quality is weak (hand-wavy assumptions, false dichotomies, missing evidence, premature dismissal of alternatives).
