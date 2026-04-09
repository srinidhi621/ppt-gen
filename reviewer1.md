# Architectural Review: SPEC-v2.md & PLAN.md

## Findings

### F1 — `critical` — Layout solver is drastically underspecified for the ambition level

**Sections:** SPEC §5.4, PLAN S2

The layout solver is described in 7 lines. It supports `inset`, `split_h`, `split_v`, `grid`, `stack`, `center`, `anchor`. Yet the system promises to render architecture diagrams, hub-spoke layouts, swimlane roadmaps, process flows with connectors, and metric card grids — all as "composed" slides.

**Why this is a real problem:** These constructs require relational layout (element A connects to element B, which is positioned relative to C). The listed solver primitives are container-level layout modes, not relational positioning primitives. A `grid` mode cannot express a hub-spoke diagram. A `stack` mode cannot express a timeline with branching connectors. The spec does not define how these solver modes compose, nest, or interact with the connector router.

**Likely consequence:** The team will either (a) build a far more complex solver than specified, blowing scope, or (b) hardcode positions per-recipe, making the "solver" a misnomer and the visual recipe system brittle. Either way, this is where the project will stall.

---

### F2 — `critical` — No specification of how the LLM produces valid absolute coordinates

**Sections:** SPEC §3.7, §4.3 Pass 3, §5.5

The `SlideElementPlan` requires `bounds` (absolute coordinates). Pass 3 says the slide composer "must decide region layout, exact primitive families, shape/line/connector choices." The renderer then consumes these as absolute bounds in slide coordinates (§5.5).

**Why this is a real problem:** Asking an LLM to emit pixel-perfect absolute coordinates for 10-20 elements on a fixed canvas, with non-overlap guarantees, correct connector routing, and typographic fit — and then validating that output deterministically — is an extremely hard problem. The spec treats it as if the LLM will just produce good coordinates. It won't. Not reliably. Not even with gpt-5.4.

The spec mentions validation in Pass 4 (non-overlap, bounds sanity) but doesn't say what happens when the LLM produces overlapping elements. "Deterministic compression" and "component swap" are listed as fallbacks but not defined.

**Likely consequence:** The majority of composed slides will fail validation on the first pass. The system will need either a constraint-solving layer between LLM output and render (not specified), or the LLM will need to be constrained to pick from pre-computed layout templates (which defeats the "composed" philosophy). This is the single hardest unsolved problem in the architecture and it receives the least attention.

---

### F3 — `high` — Review-loop oscillation is acknowledged nowhere

**Sections:** SPEC §6.5, §2.4, PLAN S3

The spec mandates that every rendered slide is reviewed, feedback is structured, and repairs are applied. It allows one review/repair loop per slide per run (§2.4). But the spec says "the repaired slide is re-reviewed when it was previously blocking" (§6.5). This contradicts the one-loop cap, or at minimum creates ambiguity about whether a re-review that still fails triggers another repair.

**Why this is a real problem:** Multimodal review is subjective. A repair that fixes spacing may introduce a new visual balance complaint. Without explicit termination conditions, budget caps, or score-delta thresholds, the loop can oscillate or burn tokens without converging.

**Likely consequence:** In practice, teams will hardcode `max_retries=1` and ignore unconverged slides. The review loop — positioned as the core quality mechanism — will be unreliable for the hardest cases (complex composed slides) where it matters most.

---

### F4 — `high` — Connector routing is a known-hard problem, treated as a line item

**Sections:** SPEC §3.4 (`connector_straight`, `connector_elbow`, `connector_curved`), §5.3 (`connector_router`), §5.5.2

The spec lists three connector types and names a `connector_router` module. No further detail. Process flows, architecture diagrams, and timelines all depend on connectors that avoid overlapping shapes and route cleanly.

**Why this is a real problem:** Connector routing on a fixed canvas with arbitrary shape placement is a graph-layout / computational-geometry problem. PowerPoint's own connector routing uses heuristics that `python-pptx` does not expose. The OOXML bridge might help, but the spec says OOXML patches must be "helper APIs only" with "no business logic."

**Likely consequence:** Connectors will either be straight lines placed by the LLM (ugly, overlapping shapes), or the team will spend significant unplanned effort on a routing algorithm. Architecture diagrams and process flows — two of the four S4 archetypes — will be the most visually broken slide types.

---

### F5 — `high` — Skill system is conceptually described but operationally unspecified

**Sections:** SPEC §2.5, §4.2, §4.2.1, §4.2.2, PLAN S0

The spec says skills are "the source of truth" and "make the system opinionated and repeatable." But:
- No skill schema is defined.
- No example skill is shown.
- No versioning mechanism is specified (just "must be versioned").
- The projection from internal skills to OpenAI Skills is described as possible but not defined.
- The fallback ("injected as structured prompt context") is not bounded — how large can a skill be before it blows the context window?

**Why this is a real problem:** Skills are positioned as a core differentiator, but the spec doesn't define what a skill actually looks like. The team will have to design the entire skill format, loading mechanism, and versioning system from scratch during S0, with no constraints from the spec.

**Likely consequence:** Skills will either become glorified system prompts (losing the "reusable, versioned" value proposition) or will require significant design work that delays S0 and S1.

---

### F6 — `high` — Reference-slide ingestion is a hidden workload mountain

**Sections:** SPEC §7, §7.2, PLAN S6

The spec requires reference slides to guide archetypes, recipes, spacing, density, hierarchy, and review rubrics. The plan defers this to S6 ("Reference-Backed Quality Evaluation"). But archetypes and visual recipes are needed in S1-S2, long before S6.

**Why this is a real problem:** Without annotated reference slides, the archetype definitions and visual recipes in S1-S4 will be hand-authored by developers guessing what "good" looks like. The quality signal that reference slides are supposed to provide won't exist during the critical early slices when the visual grammar is being established.

Additionally, ingesting and annotating reference slides (extracting layout patterns, spacing norms, density targets) from real consulting decks is a significant manual effort that is not scoped anywhere.

**Likely consequence:** The visual recipes and archetype definitions will be built on developer intuition rather than reference data, then need to be reworked in S6 when reference-backed evaluation reveals gaps.

---

### F7 — `high` — `python-pptx` limitations are underestimated for the composed path

**Sections:** SPEC §2.1, §5.6

The spec correctly identifies `python-pptx` limitations and introduces an OOXML bridge. But the gap between what `python-pptx` supports well and what the composed path demands is larger than acknowledged:

- `python-pptx` has limited/no support for: gradient fills on shapes (partial), shadow effects, glow, reflection, 3D effects, SmartArt, curved connector routing, advanced text effects, shape unions/intersections.
- The design tokens include `shadow/effect policy` (§3.3) — but `python-pptx` cannot reliably produce shadows.
- Grouped constructs with mixed fills and connector bindings require OOXML manipulation.

**Why this is a real problem:** The OOXML bridge is scoped as "targeted gaps" and "helper APIs only," but for consulting-quality output, a significant fraction of visual polish (shadows, gradients, connectors) will need to go through it. The bridge will become a second renderer, not an escape hatch.

**Likely consequence:** Either visual quality will be limited to what `python-pptx` can produce natively (below the stated quality bar), or the OOXML bridge will grow into an unplanned major subsystem.

---

### F8 — `medium` — LibreOffice rendering fidelity as review ground truth

**Sections:** SPEC §1.6, §6.1

The review loop uses `soffice` for PPTX→PDF→PNG. LibreOffice renders PowerPoint files with known fidelity gaps: font substitution, shape rendering differences, connector placement, chart rendering, and theme color interpretation all differ from PowerPoint.

**Why this is a real problem:** The multimodal reviewer will be trained/prompted to evaluate slide quality based on images that don't match what the user sees in PowerPoint. The reviewer might flag issues that don't exist in PowerPoint, or miss issues that do.

**Likely consequence:** The review loop will have a systematic bias. Repairs optimized for LibreOffice rendering may degrade PowerPoint rendering. This is a fundamental measurement problem that the spec doesn't acknowledge.

---

### F9 — `medium` — Cost and latency model is absent

**Sections:** SPEC §4.3 (all passes), §6.5, PLAN S5

A 10-slide deck requires: Pass 0 (intake) + Pass 1 (blueprint) + Pass 2 (briefs) + Pass 3 (10 composition calls) + Pass 4 (validation) + render + export + Pass 5 (10 review calls with images) + Pass 6 (repair for flagged slides) + re-render + re-review. That's at minimum ~25 LLM calls, 10 of which include images. With gpt-5.4 pricing, a single deck generation could cost $5-20+ and take 3-10 minutes.

**Why this is a real problem:** The spec targets "CLI first" and "local web UI" — users expect interactive-ish latency. The cost model is never discussed, and there's no strategy for parallelism, caching, or cost control.

**Likely consequence:** Early adopters will be shocked by latency and cost. The team will need to retrofit batching, parallelism, and caching strategies that should have been designed upfront.

---

### F10 — `medium` — Chart rendering complexity is handwaved

**Sections:** SPEC §5.5.3, §3.4

The spec lists four chart types (`chart_bar`, `chart_column`, `chart_line`, `chart_pie`). `python-pptx` chart support requires structured data series with specific formatting. The spec says "use native PowerPoint charts when structured numeric data exists" but doesn't specify:
- How the LLM extracts/generates chart data from narrative input.
- Chart data schema in the `SlideElementPlan`.
- Axis labels, legends, formatting tokens.
- How chart styling maps to design tokens.

**Likely consequence:** Charts will be the last feature to work reliably and will produce the ugliest output, because the data pipeline and styling pipeline are both unspecified.

---

### F11 — `medium` — Template drift across customer templates is unaddressed

**Sections:** SPEC §1.2, §3.2

The spec assumes a single template inspection produces stable tokens. But customer templates vary wildly: some have 3 layouts, some have 40. Some use theme colors correctly, some hardcode RGB values. Some have placeholder alt_text conventions, some don't.

**Why this is a real problem:** The system promises to work with "customer-provided branded .pptx templates" but doesn't define what makes a template compatible, what happens when extraction fails, or how to handle templates that violate assumptions.

**Likely consequence:** The system will work well with 2-3 hand-tested templates and break unpredictably on real customer templates.

---

### F12 — `medium` — S0 and S1 are not independently verifiable end-to-end

**Sections:** PLAN S0, S1

S0 produces planning artifacts but no rendered output. S1 produces template inspection but no rendered output. Neither slice produces a user-visible "this works" artifact that proves the architecture. The first real proof-of-concept is S2.

**Why this is a real problem:** The build rules say "every slice must produce user-visible functionality" (Rule 2), but S0's demo is "show a deck blueprint" (JSON) and S1's demo is "print template summary" (JSON). These are developer tools, not user-visible functionality. The team could spend weeks on S0+S1 and still not know if the core architecture works.

**Likely consequence:** S0 and S1 will feel productive but won't expose integration risks. The real pain will hit in S2 when everything has to connect.

---

### F13 — `low` — Accessibility and localization are absent

**Sections:** Neither document mentions either.

The spec targets "consulting and executive communication polish" but says nothing about alt-text on images, reading order, color contrast for colorblind users, or RTL/non-Latin text support. These are increasingly required for enterprise deliverables.

---

### F14 — `low` — Testing strategy lacks visual regression baseline

**Sections:** SPEC §11.3

The spec says "no pixel-perfect snapshots" and "structural and perceptual assertions only." But for a visual output system, there's no defined mechanism for detecting visual regressions across code changes. Structural assertions (primitive counts, collision checks) won't catch styling regressions.

---

## Open Questions / Assumptions

1. **Who authors visual recipes?** The spec assumes recipes exist but doesn't say who writes them, how they're validated, or how many are needed per archetype for adequate variety. If each archetype needs 3-5 recipes, the initial 13 archetypes require 40-65 hand-authored recipes before the system can produce varied output.

2. **What is the actual gpt-5.4 capability surface?** The spec is written as if gpt-5.4 exists and its capabilities are known. If gpt-5.4's structured output, image understanding, or Skills support differs from assumptions, the architecture may need significant adjustment. The spec does not define fallback behavior for capability gaps.

3. **How does the system handle sparse or vague prompts?** The spec assumes "a prompt, optional visualization cues, and optional reference slides." What happens when the prompt is "Make me a strategy deck"? The planner needs to either refuse or hallucinate content. Neither outcome is addressed.

4. **What is the boundary between "template_native" and "composed" routing?** The spec describes principles but no algorithm. Who decides — the LLM? A rule engine? The spec says the planner recommends a route, but validation might reroute. The routing decision tree is not defined.

5. **How will the system handle a template with no usable layouts?** If a customer template has only a title slide layout and a blank layout, the `template_native` path has almost nothing to work with. Does everything become `composed`? Is that tested?

6. **What is the token budget for skills in the context window?** If 3 skill classes are loaded per run, each with instructions, examples, patterns, rubrics, and tests — this could easily consume 20-40K tokens. Add the slide plan schema, design tokens, reference packet, and neighboring slide context, and you're at risk of exceeding context limits for complex slides.

---

## Architecture Assessment

**Technically coherent:** Mostly yes. The five-layer decomposition is sound. The separation between planning, rendering, and review is correct. The artifact model is thorough.

**Implementable by a small team / coding-agent-driven workflow:** Doubtful at stated scope. The system has 13 archetypes, each needing multiple visual recipes, a layout solver, a connector router, chart rendering, OOXML bridging, multimodal review, three delivery surfaces, and a skill system. This is 6-12 months of focused work for an experienced team of 3-4. A single developer with coding agents will need to aggressively cut scope to make progress.

**Appropriately scoped:** No. The scope creep risk is extreme. The spec defines the target state of a mature product, not an MVP. The plan tries to sequence it, but each slice contains more work than acknowledged.

**Missing layers/contracts/guardrails:** The layout solver contract is the most critical gap. The LLM-to-coordinates translation contract is missing. The skill schema is missing. The routing decision algorithm is missing. Cost/latency guardrails are missing.

---

## Tradeoff Assessment

| Decision | Verdict |
|---|---|
| **python-pptx vs PptxGenJS** | Reasonable. Template preservation matters, existing code exists, and a renderer rewrite doesn't solve the core problem. The OOXML bridge scope risk is real but manageable if visual ambitions are bounded. |
| **Hybrid template_native + composed** | Correct in principle. The routing decision is underspecified — needs a concrete algorithm, not just principles. |
| **gpt-5.4 + Skills** | Reasonable bet, but speculative. The architecture is tightly coupled to a model that may not exist yet or may not behave as assumed. The skill projection mechanism is vaporware until proven. |
| **Internal skills repo** | Good idea, poor specification. Without a schema and example, it's an aspiration, not a design. |
| **Element-level slide planning** | This is the right architectural move. The key risk is the LLM's ability to produce valid coordinates, not the concept itself. |
| **Per-slide multimodal review** | Correct and necessary. The LibreOffice fidelity gap and oscillation risk are real but manageable with bounds. |
| **Python renderer + OOXML escape hatch** | Reasonable if the escape hatch stays small. At risk of becoming a second renderer. |
| **CLI → local UI → cloud** | Correct ordering. The plan handles this well. |

---

## Presentation-Layer Critique

- **Slide archetypes:** Well-enumerated but each archetype is a sentence, not a contract. The spec says each archetype defines "narrative role, content contract, visual recipe options, default route, allowed primitives, text budgets, density limits, reference examples, review checklist" — but none of these are actually defined. The spec defines the schema for archetypes but no archetypes.
- **Visual recipes:** Same problem. Recipe IDs are listed. No recipe is defined. How large is a recipe definition? How does it translate to a slide plan? Not specified.
- **Design tokens:** The most concrete section. Token roles are well-defined. The extraction mechanism is underspecified — theme colors don't always map cleanly to semantic roles (`bg_primary`, `accent_1`, etc.).
- **Primitive catalog:** The allowed list is clear. The derived constructs section is useful. The mapping requirement (§3.4.1) is good practice.
- **Layout solver:** Already discussed in F1. Critically underspecified.
- **How the system decides what each slide looks like:** The chain is prompt → blueprint → brief → composition plan → slide plan. The brief-to-composition step is where the LLM makes visual decisions, guided by skills and recipes. This is reasonable but depends entirely on the skill quality, which is unspecified.

---

## AI-Layer Critique

- **Deck planner:** Adequate specification. The hierarchical pass structure is sound.
- **Slide composer:** The hardest role, least specified. Must produce element-level plans with absolute coordinates — the core unsolved problem.
- **Visual reviewer:** Well-specified review dimensions. LibreOffice fidelity gap is the main risk.
- **Repair planner:** Underspecified. "Updates the slide plan" — but what's the scope of allowed changes? Can it change the archetype? The recipe? The number of elements?
- **Skill loading:** Schema missing. Versioning mechanism missing. Context budget missing.
- **Review-to-planner feedback:** The feedback schema (§6.2) is adequate. The translation from review findings to repair actions is not specified — this is where "fix spacing" needs to become "change element X bounds from {a} to {b}."
- **Oscillation control:** Not addressed. Need at minimum: max iterations, score-delta termination, budget cap, and a "good enough" threshold.

---

## Deterministic Renderer Critique

- **Route selection:** Underspecified (see tradeoff assessment).
- **Validation before render:** Listed but not defined. What constitutes a non-overlap violation? What's the tolerance? How are bounds sanity checked?
- **Layout solver realism:** The solver is too simple for the stated ambitions. The fundamental question — does the LLM or the solver decide coordinates? — is unanswered.
- **Object-level rendering:** Well-covered for basic shapes and text. Connectors, charts, and grouped constructs are underspecified.
- **Editability guarantees:** Implicit in "native PowerPoint objects" but not tested. How do you verify editability? Open in PowerPoint and check? Automated?
- **OOXML bridge containment:** Good rules stated. Risk of rule erosion is high under delivery pressure.
- **PowerPoint failure modes:** Not discussed. Common issues: repair prompts from malformed XML, font embedding, image resolution limits, maximum shape counts, file size, and theme corruption when mixing template elements with composed elements.

---

## Plan Critique

- **Thin enough?** S0 and S1 are thin. S2 is deceptively large (SlidePlan schema + layout solver + element factory + composed rendering — each is substantial). S4 adds two archetypes, which means new recipes, new connector handling, and new validation rules. S5 is a multi-slide orchestration layer. None of these are two-week slices.
- **Independently verifiable?** S0 and S1 are verifiable but not very useful alone (see F12). S2 is the first real verification point.
- **Right order?** Mostly yes. Debatable whether review (S3) should come before archetype expansion (S4). Argument for: review on one archetype validates the loop. Argument against: if the architecture doesn't generalize to connectors (S4), S3's review loop may need redesign.
- **Fast learning?** S2 will produce fast learning. S0 and S1 will not. The plan should consider collapsing S0+S1 into a single slice that ends with a rendered (even ugly) slide.
- **Hardest risks early enough?** The hardest risks are (1) LLM coordinate generation, (2) layout solver adequacy, and (3) connector routing. Risk 1 is first hit in S2 — good. Risk 3 is deferred to S4 — acceptable. But if S2 reveals that LLM coordinate generation doesn't work, S3-S9 are all invalid.

---

## Missing Concerns

1. **Benchmark realism:** Benchmark thresholds (S6) require reference-backed scoring, but who calibrates the thresholds? If thresholds are set too low, the gates are meaningless. Too high, every deck fails.
2. **Skill governance:** Who approves changes to skills? How do skill changes propagate to existing runs? How do you debug a bad skill?
3. **Image/icon sourcing:** The primitive catalog includes `image` and `icon`, but the spec doesn't say where images and icons come from. Stock libraries? User upload? Generated? This is a significant content pipeline gap.
4. **Error UX:** What does the user see when generation fails a quality gate? "Your deck failed" is not actionable. The spec defines machine-readable gates but no user-facing error experience.
5. **Concurrency and state:** The cloud endpoint (S8) implies concurrent runs. The artifact model (`runs/<run_id>/`) supports this, but the renderer and review pipeline assume exclusive access to files. No concurrency model is defined.
6. **Azure deployment specifics:** "Azure-hosted deployment" is mentioned but not specified. Container? App Service? Function? GPU requirements for soffice? None addressed.

---

## Overall Verdict

**Approve with major revisions.**

The architectural direction is correct. The five-layer decomposition, element-level planning, multimodal review loop, and hybrid rendering strategy are all sound decisions. The artifact model is thorough. The delivery surface ordering is right.

But the spec has a critical gap at its center: the interface between LLM planning and deterministic rendering. The layout solver, coordinate generation strategy, connector routing, and repair-loop convergence — the four hardest technical problems — are the least specified parts of the document. The spec is strongest where the problems are easiest (token extraction, artifact naming, quality gate enumeration) and weakest where the problems are hardest.

The plan is sequenced reasonably but underestimates the size of S2-S5 and defers reference-backed evaluation too late.

---

## Top 5 Recommended Changes

1. **Define the LLM-to-coordinates contract explicitly.** Decide now: does the LLM emit absolute coordinates, or does it emit a high-level layout intent (e.g., "3-column grid with a header bar") that a deterministic solver resolves into coordinates? The latter is dramatically more likely to work. Specify the vocabulary of layout intents, how they map to solver operations, and what the solver guarantees. This is the single most important design decision in the system and it is currently unspecified.

2. **Collapse S0+S1 and extend S2 into the first real proof-of-concept.** The first milestone the team should celebrate is "one ugly but correct composed slide renders from a prompt." Move S0 and S1 content into a combined slice that ends with rendering, not with JSON artifacts. This will expose integration risks 2-4 weeks earlier.

3. **Define one complete skill as a worked example in the spec.** Pick `executive_summary`. Write the actual skill definition: its instructions, examples, allowed patterns, prohibited patterns, review rubric, and how it's loaded into the prompt. This will force resolution of the skill schema, context budget, and versioning questions before implementation starts.

4. **Add explicit convergence controls to the review loop.** Define: maximum repair iterations (recommend 1 for MVP, with clear escalation to "accept with warnings"), minimum score-delta to justify a repair attempt, total token budget per slide for review+repair, and what happens when a slide cannot be fixed (accept-with-caveats, not infinite retry).

5. **Scope the layout solver to recipe-driven templates, not general constraint solving.** Instead of a general solver, define each visual recipe as a parameterized layout template with named slots (e.g., "3-card row with header" has slots for header text, card 1-3 content, card 1-3 icon). The LLM's job becomes selecting a recipe and filling slots, not computing coordinates. The solver's job becomes instantiating the recipe template with token-correct styling. This is dramatically more tractable and produces more consistent results.
