## Content

<!-- section_id: legacy_xray_title -->


## Legacy System X-Ray & Navigator

AI-assisted understanding for mainframes and monoliths
From trapped SME knowledge → shared, governed system model → safer modernization

---


<!-- section_id: business_problem -->


## The Business Problem
- Critical COBOL / FORTRAN / PL/SQL / Java monoliths run core business, but knowledge is trapped in a few SMEs
- Onboarding new engineers and doing impact analysis takes weeks, slows releases, increases risk
- “Just give 5 devs a copilot” helps individuals, but does not create org-wide understanding of the estate

---


<!-- section_id: why_not_just_copilot -->


## Why “Just Give the Team Copilot” Fails
- IDE assistance is ephemeral and individual (summaries live in chat history and local context)
- Legacy systems need a persistent system model: call graphs, data flows, entity maps
- Without shared governance, impact analysis and onboarding remain SME-dependent

---


<!-- section_id: three_tier_overview -->


## Our 3-Tier Offering
- Tier 1 — Legacy System X-Ray (2–4 weeks): rapid assessment + system map + traceable Q&A demo
- Tier 2 — Legacy Code Navigator: production-grade knowledge layer for daily engineering work
- Tier 3 — Modernization Accelerator: de-risk modernization using the knowledge layer

---


<!-- section_id: tier1_xray -->


## Tier 1 — Legacy System X-Ray (Assessment, 2–4 weeks)
- Parse legacy code, jobs, schemas into a system map: modules, interfaces, key business entities
- Produce entity-to-code impact maps (Customer / Account / Policy) + hot-spot analysis
- Ship a lightweight “Ask Your Legacy System” demo to query flows and rules with traceable code references

---


<!-- section_id: tier2_navigator -->


## Tier 2 — Legacy Code Navigator (Team Copilot)
- Turn the X-Ray into a production-grade knowledge layer for daily engineering work
- Pre-built query recipes:
- Impact analysis
- Business flow tracing
- “Explain this program”
- Data lineage
- Outputs always include file paths + line numbers
- Guided onboarding walkthroughs for new engineers; optional IDE / web integration; deployed in client VPC

---


<!-- section_id: tier3_modernization -->


## Tier 3 — Modernization Accelerator
- Use the knowledge layer to prioritize and de-risk modernization (strangler pattern, refactors, re-platforming)
- Generate candidate interface specs, sequence diagrams, and test suggestions from existing flows
- AI-assisted refactoring support so new code preserves legacy semantics while moving to modern stacks

---


<!-- section_id: differentiation -->


## How This Differs from “Just Buy Cursor / Claude Code Licenses”
- We build a persistent system model (call graphs, data flows, entity maps), not ad-hoc file summaries
- Knowledge is shared and governed across teams (onboarding tours, impact reports, dashboards)
- Everything runs in the client-controlled environment (on-prem / VPC) with auditability and traceability for regulators

---


<!-- section_id: business_outcomes -->


## Business Outcomes
- Reduce onboarding time on legacy systems from months → weeks
- Cut impact-analysis effort for major changes from days → hours
- Lower dependency on a handful of legacy SMEs and create a living knowledge base for future modernization

---


<!-- section_id: engagement_approach -->


## Engagement Approach (Typical)
- Week 0: scope, access, success criteria, guardrails (security, audit, residency)
- Weeks 1–2: ingestion + initial system map + first impact maps
- Weeks 3–4: traceable Q&A demo + findings readout + tiered roadmap (Navigator + Modernization)
- Deliverables: System Atlas, Impact Maps, Query Recipes, Deployment Plan

---

## Visualization Cues

```json
{
  "cues": [
    {
      "section_id": "legacy_xray_title",
      "layout_hint": "title_image_light",
      "notes": "Hero slide. Use an X-ray scan metaphor on a mainframe/monolith silhouette revealing a network graph beneath. Keep subtitle and value chain concise. Add three badges: Traceable, Client-controlled, Org-wide model.",
      "icon_hints": ["xray", "mainframe", "graph", "compass", "shield"],
      "image_hint": "Monolith/mainframe silhouette with x-ray overlay revealing nodes/edges (system graph) on a blueprint grid background."
    },
    {
      "section_id": "business_problem",
      "layout_hint": "three_content_light",
      "notes": "Three tiles left-to-right: SME bottleneck, slow onboarding, risky changes. Add a single bold statement line across the slide: 'Understanding is the constraint.'",
      "icon_hints": ["key", "people", "calendar", "warning", "pipeline"],
      "image_hint": null
    },
    {
      "section_id": "why_not_just_copilot",
      "layout_hint": "two_content_light",
      "notes": "Split comparison: left 'Individual augmentation' (IDE + suggestions), right 'Estate understanding' (persistent system map). Use a simple metaphor: sticky notes vs engineering atlas.",
      "icon_hints": ["ide", "chat", "atlas", "graph", "governance"],
      "image_hint": "Side-by-side illustrative panel: IDE suggestion overlay vs system map/knowledge base."
    },
    {
      "section_id": "three_tier_overview",
      "layout_hint": "agenda_light",
      "notes": "Use a 3-step horizontal pipeline with tier icons and short deliverable captions. Add a maturity bar: Understanding → Daily Use → Modernize.",
      "icon_hints": ["scanner", "compass", "rocket", "timeline"],
      "image_hint": null
    },
    {
      "section_id": "tier1_xray",
      "layout_hint": "two_content_image_light",
      "notes": "Left: system map diagram + entity-to-code impact map with hotspot markers. Right: demo screenshot placeholder 'Ask Your Legacy System' with explicit 'Sources: file path + line numbers'. Use stamped artifact badges for deliverables.",
      "icon_hints": ["map", "entity", "heatmap", "chat", "link"],
      "image_hint": "Composite visual: module/interface map + entity impact network + small chat UI with citations."
    },
    {
      "section_id": "tier2_navigator",
      "layout_hint": "content_image_light",
      "notes": "Show a simple architecture mini-diagram: code/jobs/schemas → ingestion → Knowledge Layer → IDE/Web/API. Below or side: 4 recipe cards with consistent 'paths + line numbers' footer. Include a guided onboarding tour UI motif (step 1/2/3).",
      "icon_hints": ["architecture", "database", "index", "ide-plugin", "recipe", "tour"],
      "image_hint": "Clean architecture flow diagram with small recipe cards."
    },
    {
      "section_id": "tier3_modernization",
      "layout_hint": "two_content_image_light",
      "notes": "Use strangler pattern visual: monolith gradually hollowed out to services via routing layer. Add thumbnail montage of generated artifacts: interface spec, sequence diagram, tests. Emphasize 'preserve semantics' with a lock/seal icon.",
      "icon_hints": ["strangler-pattern", "services", "sequence-diagram", "tests", "lock"],
      "image_hint": "Strangler pattern illustration: monolith → routing layer → microservices with phased cutover."
    },
    {
      "section_id": "differentiation",
      "layout_hint": "two_content_light",
      "notes": "Comparison table: Tool license vs X-Ray & Navigator across 3 rows (persistent model, shared governance, client-controlled + audit). Use icons per row and a 'Non-negotiables' strip at bottom: Traceable, Auditable, VPC/on-prem.",
      "icon_hints": ["table", "graph", "org-chart", "shield", "audit"],
      "image_hint": null
    },
    {
      "section_id": "business_outcomes",
      "layout_hint": "four_content_light",
      "notes": "Use three before/after bars (months→weeks, days→hours, high→lower). Add a small flywheel in a corner: Learn → Document → Query → Improve → Modernize. Keep metrics as placeholders for tailoring.",
      "icon_hints": ["before-after", "speed", "flywheel", "metrics"],
      "image_hint": null
    },
    {
      "section_id": "engagement_approach",
      "layout_hint": "one_content_light",
      "notes": "Timeline with gates: Week 0, Weeks 1–2, Weeks 3–4. Add a small risk-controls row with icons: residency, access control, audit logs. End with a deliverables 'starter kit' box.",
      "icon_hints": ["timeline", "checkpoint", "shield", "audit-log", "deliverable-box"],
      "image_hint": null
    }
  ]
}
```
