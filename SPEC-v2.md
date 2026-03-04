# SPEC-v2.md — AI Presentation Generator (Zero-Cost Runtime, Compositor Architecture)

## 0) Purpose

This spec replaces the prior V2 draft with an implementation-ready architecture that:

1. Produces **fully native, editable `.pptx`** files
2. Preserves **company template branding** (masters, theme colors, theme fonts)
3. Uses **zero-cost, locally installable runtime dependencies**
4. Fixes V1’s composition quality ceiling without discarding V1’s deterministic backbone

This is an architectural document and source-of-truth contract for V2 implementation.

---

## 0.1) Implementation Progress Snapshot (`2026-03-04`)

Implemented in current branch:
- planner metadata loading:
  - `assets/catalog/component_catalog_v1.json`
  - `assets/catalog/planner_policy_v1.json`
- planner prompt now includes:
  - component metadata summary
  - visual planning policy summary
  - policy-derived diversity/routing constraints
- benchmark + style metadata scaffolding:
  - `assets/benchmarks/benchmark_manifest_v1.json`
  - `assets/catalog/component_examples_v1.json`
  - `assets/catalog/template_style_baselines_v1.json`
- regression coverage for metadata wiring:
  - `tests/test_assets_metadata.py`
  - `tests/test_planner_prompt_metadata.py`
- DeckIR v2 fixture directory scaffold:
  - `tests/fixtures/deckir_v2/README.md`
- deterministic planning guardrails (new pre-planning stage):
  - `src/planning/guardrails.py`
  - `src/models/planning.py`
  - artifacts persisted under `runs/<run_id>/`:
    - `intent_briefs_v1.json`
    - `structure_plans_v1.json`
    - `visual_realization_plan_v1.json`
    - `planning_validation_v1.json`
- archetype and visual policy catalogs:
  - `assets/ground_truth/archetype_message_contracts_v1.json`
  - `assets/catalog/visual_primitive_policy_v1.json`
- planner prompt now includes planning guardrail context:
  - section-level core theme and bottom line
  - structure plan constraints
  - visual primitive realization plan
- quality gates expanded to include:
  - `message_contract_alignment`
  - `structure_layout_alignment`
  - `visual_primitive_policy`

Not yet implemented:
- expanded KPI emission into `quality_gates_v2.json` and `run_summary.json`
- runtime composed renderer and bounded solver implementation
- benchmark-calibrated archetype contract scoring against curated ground-truth corpus

---

## 1) Hard Constraints

### 1.1 Output Contract
- Output is a `.pptx` file that opens in Microsoft PowerPoint.
- Text, shapes, charts, connectors, and diagrams must be manually editable.
- No slide-as-image rendering in exported PPTX.

### 1.2 Template Contract
- Input template is a customer-provided `.pptx` with branded masters/themes/layouts.
- System must open/modify/preserve that template.
- Placeholder binding remains `shape.alt_text == field_key` for template-native path.

### 1.3 Dependency Cost and Licensing Policy
- All non-LLM runtime dependencies must be zero-cost to install and run locally (no paid SDK/runtime licenses).
- Open-source and proprietary-but-free tools are both allowed if they are locally installable and license-safe for intended use.
- Paid usage is allowed only for:
  - coding assistants used during development, and
  - LLM inference used by the planning/review pipeline.

### 1.4 Deterministic Safety
- LLM output must always be schema-validated.
- Deterministic validation/remediation remains mandatory.
- Run artifacts and logs must persist under `runs/<run_id>/`.

---

## 2) Architectural Decisions (Final)

## 2.1 Rendering Engine: Python + `python-pptx` (Accepted)

**Decision**
- Primary renderer remains Python with `python-pptx`.

**Why**
- Must open and preserve existing branded templates.
- Need editable native shapes/charts/connectors in output.
- Reuses V1 deterministic infrastructure.

**Alternatives considered**
- `PptxGenJS` / `react-pptx`: generation-oriented; no reliable template import/edit parity.
- Direct OOXML write-only approach: high complexity, low maintainability for V2 timeline.
- Apache POI route: feasible but introduces JVM split and higher team complexity.

**Risks**
- `python-pptx` feature gaps and slow upstream evolution.
- Some operations may require low-level XML workarounds.

**Mitigations**
- Introduce `src/render/ooxml_bridge.py` for isolated XML escape hatches.
- Keep XML manipulation behind tested helper APIs, never inline in component code.

## 2.2 Layout Engine: Bounded Geometry Solver (Partially Accepted)

**Decision**
- Implement a small deterministic solver for fixed-canvas layouts, not full Flexbox.

**Allowed primitives only**
- `inset`, `split_h`, `split_v`, `grid`, `flow`, `center`

**Why**
- Slide canvas is fixed; responsive web semantics are unnecessary for MVP.

**Guardrails (non-negotiable)**
- Solver scope is layout regioning only; no generic CSS clone.
- Max nesting depth: 3 (`slide -> region -> component internals`).
- If solver complexity exceeds thresholds, escalate to constraint solver evaluation.

**Escalation thresholds**
- `solver.py` > 600 LOC excluding tests, or
- > 12 ad-hoc special-case branches for overflow/collision, or
- > 5 unresolved layout bug classes after two sprints

If any threshold is hit, run a focused spike comparing bounded Cassowary/Kiwi constraints for the failing cases.

## 2.3 Smart Component Library (Accepted with strict scope)

**Decision**
- Build a component library that renders native PPT shapes into solver-computed regions.

**Component contract**
- `min_size()`
- `preferred_size()`
- `validate_payload(data)`
- `render(slide, bounds, theme) -> list[Shape]`
- `to_composition_meta() -> dict`

**MVP component set (do not exceed in initial build)**
- `TitleSlide`, `SectionBreak`, `ContentBlock`, `TextWithImage`, `MetricCards`, `BentoGrid`, `IconGrid`, `Timeline`, `ProcessFlow`, `ComparisonColumns`, `ArchitectureDiagram`, `DataTable`

**Risks**
- Programmatic visuals can look mechanical.
- Payloads may be schema-valid but visually unfit (example: 15 timeline items).

**Mitigations**
- Per-component hard caps (`max_items`, `max_words_per_cell`, etc.).
- Component-specific remediation (`paginate`, `compress`, `swap_component`).
- Centralized theme tokens and spacing scale to avoid inconsistent look.

## 2.4 Hybrid Slide Strategy: `template_native` + `composed` (Accepted)

**Decision**
- Keep two slide paths:
  - `template_native`: V1 placeholder-fill path for simple slides.
  - `composed`: freeform component rendering for visual/diagram-heavy slides.

**Why**
- Preserves template designer polish where it already works.
- Removes V1 ceiling for advanced visuals.

**Primary risk**
- Deck looks inconsistent between template and composed slides.

**Mitigations**
- Shared theme token system from template extraction.
- Shared slide rhythm constraints (title zone, margin grid, spacing scale).
- Gate: mixed-mode decks fail if typography or spacing drift exceeds thresholds.

## 2.5 Planning Architecture: Single Model, Two-Pass Orchestration (Override)

**Decision**
- Keep a single model family, but split planning into two deterministic passes.

**Pass A (Deck Skeleton)**
- Narrative arc
- Slide archetype
- Route choice (`template_native` vs `composed`)
- Component type selection
- Visual intent tags

**Pass B (Slide Payload Fill)**
- Component data payload per slide
- Asset references with diversity constraints
- Text budgets per component

**Why this override**
- One giant call is brittle (token pressure + inconsistent structure).
- Full multi-agent chain is overhead-heavy.
- Two-pass with one model keeps coordination simple while improving reliability.

**Concurrency**
- Pass B can run in parallel per slide batch after Pass A is fixed.

## 2.6 Web Preview: PPTX-Derived Images (Accepted as MVP ceiling)

**Decision**
- PPTX remains source of truth.
- Preview uses rendered slide images (`soffice -> pdf -> pdftoppm/png`).

**Why**
- Avoids permanent dual-renderer fidelity drift.

**Known limitation**
- 2–3s slide refresh is not Gamma-level instant editing.

**Mitigations**
- Per-slide render cache keyed by `(slide_hash, template_hash)`.
- Async render workers with bounded queue.
- Incremental rerender only for affected slides.

## 2.7 Migration Strategy: Evolutionary (Accepted with anti-coupling controls)

**Decision**
- Extend V1 modules and artifacts instead of clean-room rewrite.

**Anti-coupling controls**
- `deck_ir_v2` in separate module namespace from V1 schema.
- Renderer split into explicit engines, not flag-heavy monolith.
- Decommission policy for V1-only code paths after stable adoption window.

---

## 3) Runtime Tech Stack (Locked)

## 3.1 Runtime and Core Libraries
- Python 3.11+
- `python-pptx`
- `pydantic` v2
- `fastapi`, `uvicorn`
- `pytest`, `pytest-xdist`
- `orjson`

## 3.2 Preview Toolchain
- LibreOffice `soffice` (headless PPTX->PDF)
- `pdftoppm` (PDF->PNG)

## 3.3 LLM Inference Backend
- Supported modes:
  - API-based hosted LLMs (paid allowed), or
  - self-hosted models (`vLLM` preferred, `llama.cpp` fallback)
- Planner model class: strong instruct model suitable for structured JSON output
- Multimodal reviewer model class: VLM suitable for slide image critique

Model name/version must be persisted in run artifacts for reproducibility.

## 3.4 Queue/Concurrency (Phase 2+)
- Redis + RQ/Celery for async generation/re-render jobs

---

## 4) System Architecture

```text
Input Markdown
  -> Normalize (deterministic)
  -> Theme + Catalog Load (deterministic)
  -> Plan Pass A (LLM, skeleton)
  -> Validate Skeleton (deterministic)
  -> Plan Pass B (LLM, payload fill)
  -> Validate + Remediate (deterministic)
  -> Render V1 (deterministic)
  -> Diagnose + Preview Export (deterministic)
  -> Multimodal Review (LLM)
  -> Replan Pass B only (LLM, bounded changes)
  -> Validate + Render V2 (deterministic)
  -> Quality Gates (deterministic)
  -> Artifacts + Summary
```

Loop policy remains one review loop maximum.

---

## 4.1 Deck Blueprint Library Contract (New)

The system must support blueprint-guided planning for common AI consulting deck types.  
Blueprints define expected narrative structure and required slide roles before layout selection.

Required blueprint IDs:
1. `proposal_rfp`
2. `solution_approach`
3. `case_study`
4. `gtm_offering`
5. `ai_strategy`
6. `opportunity_assessment`
7. `business_case_roi`
8. `responsible_ai_governance`
9. `data_ai_platform_blueprint`
10. `executive_steering_update`

Minimum blueprint contract per type:
- `blueprint_id`
- `required_sections[]`
- `optional_sections[]`
- `target_slide_range`
- `required_archetypes[]`
- `required_evidence_types[]`

Canonical section expectations:
- `proposal_rfp`: executive summary, client context/problem, proposed solution, delivery plan, team/governance, risks/assumptions, commercials, proof points, next steps.
- `solution_approach`: objectives/scope, current state, design principles, target-state architecture, prioritized use cases, phased implementation, dependencies/risks, success metrics.
- `case_study`: client context, challenge, intervention, implementation highlights, measurable outcomes, lessons learned, repeatable pattern.
- `gtm_offering`: market opportunity, ICP, value proposition, offer/package, pricing model, channel and sales motion, launch plan, pipeline KPIs.
- `ai_strategy`: ambition and value thesis, value pools, use-case portfolio, operating model, data/platform foundation, governance/risk, talent/change, roadmap, investment case.

---

## 4.2 Reusable Slide Archetype Library Contract (New)

A shared archetype library must be used across all blueprint types to avoid one-off slide logic.

Minimum archetype set:
- `title_section_break`
- `executive_summary`
- `problem_statement`
- `current_vs_target_state`
- `use_case_prioritization_matrix`
- `capability_heatmap`
- `architecture_diagram`
- `process_flow`
- `roadmap_workplan`
- `governance_raci`
- `risk_issue_matrix`
- `kpi_dashboard`
- `value_waterfall_roi`
- `team_roles`
- `pricing_options`
- `case_study_problem_solution_impact`
- `decision_next_steps`

Archetype contract:
- `archetype_id`
- `intent_tags[]`
- `content_schema`
- `visual_schema`
- `layout_affinity[]`
- `quality_checks[]`

---

## 4.3 Ground-Truth Corpus Contract (New)

Ground truth is a curated, annotated reference corpus used as the north star for both planning and quality gates.

Required artifacts:
- `assets/ground_truth/deck_blueprints_v1.json`
- `assets/ground_truth/slide_archetypes_v1.json`
- `assets/ground_truth/quality_rubric_v1.json`
- `assets/ground_truth/ground_truth_manifest_v1.json`
- `assets/ground_truth/annotations/*.json`
- `assets/ground_truth/reference_slides/*.png` (and source metadata)

Annotation requirements per reference slide:
- `blueprint_id`
- `archetype_id`
- `story_role` (opening/problem/analysis/recommendation/close)
- `content_structure` (headline, evidence blocks, takeaway line)
- `visual_structure` (chart/diagram/image/table/icon mix)
- `hierarchy_signals` (typography contrast, focal order)
- `density_metrics` (text load, whitespace ratio, visual coverage)
- `quality_scores` (1-5) across rubric dimensions

Rubric dimensions (minimum):
1. Message clarity
2. Narrative role fit
3. Evidence quality and specificity
4. Visual hierarchy and scanability
5. Layout balance and spacing discipline
6. Visual relevance and non-repetition

Only slides with average score `>= 4.0/5.0` can be included as north-star references.

---

## 4.4 First-Slide Validation Protocol (New)

No broad feature expansion is allowed until one archetype can pass ground-truth validation end-to-end.

Pilot protocol:
1. Select one blueprint + one archetype pair (initial recommendation: `proposal_rfp` + `executive_summary`).
2. Generate a single-slide output via full deterministic pipeline.
3. Validate against:
- archetype structural checks;
- rubric score thresholds;
- existing hard safety gates (overflow/markdown/style constraints).
4. Persist a comparison artifact:
- `runs/<run_id>/ground_truth_eval_v1.json`

This gate is required before implementing additional archetypes/components.

---

## 5) DeckIR v2 Contract

## 5.1 Schema Versioning
- Every IR payload includes:
  - `schema_name = "deck_ir"`
  - `schema_version = "2.0.0"`
- Breaking changes require major version bump.
- V1 and V2 readers live side-by-side during migration.

## 5.2 Core Types

```python
class DeckIRv2(BaseModel):
    schema_name: Literal["deck_ir"] = "deck_ir"
    schema_version: str = "2.0.0"
    run_id: str
    template_id: str
    title: str
    slides: list[SlideIRv2]

class SlideIRv2(BaseModel):
    slide_id: str
    title: str
    archetype: Literal[
        "title", "section_break", "content", "comparison",
        "data_heavy", "visual_story", "closing"
    ]
    layout: SlideLayout
    visual_intent: list[VisualIntent]
    speaker_notes: str = ""

class SlideLayout(BaseModel):
    route: Literal["template_native", "composed"]
    template_layout_id: str | None = None
    structure: Literal["single", "split_h", "split_v", "grid"] = "single"
    weights: list[float] = [1.0]
    gap: float = 0.2
    padding: Insets
    regions: list[RegionSpec] = []
```

## 5.3 Compatibility Rules
- `template_native` slides may omit `regions`.
- `composed` slides must include region/component payloads.
- Unknown component types fail validation; no soft fallback to generic text slide.

---

## 6) Layout and Composition Rules

## 6.1 Slide Rhythm Constraints
Apply to both routes for visual coherence:
- Outer margins: derived from template, clamped to `[0.35, 0.8]` inches.
- Title band reserve: fixed ratio per archetype.
- Vertical spacing scale: `{xs, sm, md, lg} = {0.08, 0.14, 0.24, 0.36}` inches.

## 6.2 Overflow Policy
Overflow is handled before render:
1. Component-level compress (truncate low-priority detail)
2. Component swap (e.g., `Timeline -> ContentBlock`)
3. Slide split (preferred for major overflow)
4. Speaker-notes spillover (last resort)

Blocking overflow after step 3 fails quality gates.

## 6.3 Collision Policy
- No overlaps between title band and body regions.
- No inter-region overlap in composed path.
- Connectors must terminate within source/target node bounds.

---

## 7) Theme Extraction and Styling

## 7.1 Theme Extraction
Extract from template:
- Accent colors
- Text/background colors
- Heading/body fonts
- Slide dimensions

## 7.2 Design Tokens
Generated deterministic token map:
- Typography scale (`h1/h2/h3/body/caption`)
- Spacing scale
- Radius and stroke profiles
- Component role colors (`surface`, `accent`, `muted`)

Components may use only tokenized style values; no arbitrary local styling.

---

## 8) Asset Strategy

## 8.1 Inputs
- `assets/catalog/asset_catalog.json`
- `assets/catalog/visual_vocabulary.json`
- `assets/catalog/branded_images.json`
- `assets/icons/icons.json`
- `assets/catalog/component_catalog_v1.json`
- `assets/catalog/component_examples_v1.json`
- `assets/catalog/planner_policy_v1.json`
- `assets/catalog/template_style_baselines_v1.json`
- `assets/benchmarks/benchmark_manifest_v1.json`
- `assets/ground_truth/deck_blueprints_v1.json`
- `assets/ground_truth/slide_archetypes_v1.json`
- `assets/ground_truth/quality_rubric_v1.json`
- `assets/ground_truth/ground_truth_manifest_v1.json`

## 8.2 Selection Rules
- Intent-first matching (`diagram_map`, `icon_cluster`, `hero_image`, etc.)
- Repetition penalty per deck
- Role weighting (`hero`, `primary`, `secondary`, `accent`)

## 8.3 Hard Diversity Constraints
- Same branded image max reuse: `2`
- Minimum unique visual assets per 10 slides: `>= 6`
- Hero image cannot be reused in adjacent sections

---

## 9) Quality Gates (V2)

Existing gates retained:
- `no_blocking_overflow`
- `visual_coverage_image_layouts`
- `no_icon_hero_stretch`
- `no_markdown_marker_leak`
- `min_visual_density`
- `min_image_asset_presence`

New gates:
- `component_bounds_respected`
- `visual_intent_coverage`
- `layout_variety`
- `asset_diversity`
- `mixed_mode_style_consistency`
- `component_payload_limits_respected`
- `ground_truth_archetype_alignment`
- `ground_truth_quality_floor`

Any blocking gate failure marks run as failed quality.

---

## 10) Testing Strategy (Missing Concern Closed)

## 10.1 Unit Tests
- Solver geometry invariants
- Theme extraction correctness
- Component payload validation and min/preferred size checks

## 10.2 Integration Tests
- End-to-end `generate-auto` with fixed seeds/model settings
- Artifact contract checks under `runs/<run_id>/`

## 10.3 Visual Regression (non-pixel-perfect)
- Structural assertions from composition metadata (counts, bounds, overlaps)
- Perceptual checks on preview images (density, whitespace bands, repetition)
- No strict pixel snapshots

## 10.4 Schema Compatibility Tests
- Golden IR fixtures for `2.0.x`
- Reader behavior for older compatible minor versions

## 10.5 Ground-Truth Evaluation Tests
- Annotation schema validation tests
- Rubric scorer determinism tests
- Archetype alignment tests for pilot slide generation

---

## 11) Performance and Scale Plan

## 11.1 SLO Targets (MVP)
- 15-slide deck generation (single loop): p50 <= 90s, p95 <= 180s
- Single-slide edit rerender: p50 <= 2.5s, p95 <= 5s

## 11.2 Bottlenecks
- Primary bottleneck: `soffice` conversion throughput
- Secondary bottleneck: large model inference latency

## 11.3 Scaling Controls
- Worker pools separated by task class:
  - LLM planning workers
  - render workers
  - preview conversion workers
- Cache preview artifacts by slide hash
- Queue backpressure and request shedding under overload

---

## 12) UX Error Recovery

When generation fails gates:
- Return deck with failure report, not silent failure.
- Expose top blocking reasons in API response.
- Allow user to accept draft or trigger targeted slide remix.

When a component fails render:
- Fallback to deterministic safe component (`ContentBlock`) and log degraded status.
- Mark slide as degraded in `run_summary.json`.

---

## 13) Accessibility and Localization

## 13.1 Accessibility Baseline
- Enforce minimum contrast thresholds from theme token roles.
- Maintain readable font-size floors per component.
- Preserve alt text for inserted images where available.

## 13.2 Localization Baseline
- Text expansion budget: +30% for non-English languages.
- RTL not in MVP; must fail fast with explicit unsupported warning if requested.

---

## 14) Execution Plan and Timeline (Revised)

A 10-week timeline is optimistic for AI-agent-only implementation if polished components are in scope.  
Revised baseline with ground-truth buildout: **13–15 weeks**.

## Phase G (Week 1)
- Ground-truth acquisition and curation kickoff (internal + external references)
- Blueprint/archetype/rubric schema finalization
- Exit: approved `ground_truth_manifest_v1.json` and pilot archetype selection

## Phase 0 (Week 2)
- DeckIR v2 schema + versioning
- Theme extraction + token map
- Exit: schema fixtures and extractor tests green

## Phase 1 (Weeks 3–4)
- Bounded layout solver + exhaustive unit tests
- Exit: all solver invariants pass

## Phase 2 (Weeks 5–7)
- MVP component library implementation
- Component payload validators + caps/remediation
- Exit: handcrafted benchmark decks meet non-overlap + overflow constraints

## Phase 3 (Weeks 8–9)
- Two-pass planner integration with selected LLM backend (API or self-hosted)
- Deterministic routing checks and retry handling
- Exit: mixed `template_native/composed` decks generated reliably

## Phase 4 (Weeks 10–11)
- Review loop tuning + expanded quality gates
- Visual regression heuristics + benchmark run suite
- Exit: V2 wins on benchmark KPIs vs V1

## Phase 5 (Weeks 12–13)
- FastAPI endpoints + async workers + preview cache
- Slide-edit rerender workflow
- Exit: end-to-end web flow operational at target p50 latencies

## Buffer (Weeks 14–15)
- performance hardening, bug backlog, polish pass

---

## 15) Success Criteria

V2 is accepted when all are true:
1. A 15-slide benchmark deck uses >= 5 distinct visual structures.
2. Diagram/timeline/process slides are editable grouped native shapes.
3. Blocking overflow count is zero.
4. Asset diversity gates pass consistently across benchmark runs.
5. Mixed-mode deck style consistency gate passes.
6. Template swap changes deck branding without code changes.
7. Ground-truth quality-floor gates pass for pilot archetypes.
8. End-to-end pipeline artifacts/logging contracts remain intact.

---

## 16) Out of Scope (for this spec)

- SmartArt generation
- Rich animation choreography
- WYSIWYG browser canvas matching PowerPoint layout semantics
- Non-PPTX output formats as primary target

---

## 17) Required Follow-up Artifacts

To operationalize this spec, the following must be updated immediately after approval:
- `PLAN.md` (phase breakdown + owners + dates)
- `README.md` (LLM backend setup and runtime dependency install instructions)
- `tests/` golden fixtures for DeckIR v2
