# 10x Approach v1 — Deck Breakdown

Source deck: `assets/ground_truth/internal_inbox/10x Approach-v1.pptx`
Rendered slide previews: `assets/ground_truth/annotations/10x_approach_v1_images/`
Montage: `assets/ground_truth/annotations/10x_approach_v1_montage.png`

## Deck-Level Read

This is a 15-slide operating-model and talent-assessment deck for a "10x AI Engineering" approach. It mixes a premium executive opener, capability framing, service packaging, candidate selection, staged assessment funnel, detailed level-by-level evaluation slides, operational ownership, and a closing brand slide.

The strongest reusable structure is a **dense assessment funnel / operating-model pattern**:

- A clean white working canvas for most content slides.
- A consistent title/header band with a small footer and Ascendion mark.
- Color-coded modules: teal, purple, yellow, gray, green, and magenta.
- Step/gate sequencing with short labels, durations, owners, and signal criteria.
- Heavy use of compact cards, connectors, numbered stages, and platform/role lanes.
- A repeated "Signal we're looking for" or "Operating principle" summary band at the bottom.
- Visual proof slides inserted between framework slides, including a product/platform screenshot.

## Archetype Ingestion

Map this deck into the current supported V3 archetype vocabulary as a **process_flow-led multi-slide benchmark**:

- Primary archetype: `process_flow`
- Supporting archetypes: `hero_title`, `hero_statement_with_support_columns`, `content_with_visual`, `comparison_split`, `timeline_roadmap`
- Unsupported-but-observed pattern: `matrix_grid` / operating matrix. Until `matrix_grid` is supported by V3, represent dense matrices as `content_with_visual`, `comparison_split`, or split across multiple `process_flow` slides.

This should not create a new runtime archetype yet. Treat it as a benchmark for whether the existing archetypes can express a detailed, visually structured operating model without text overlap or layout collapse.

## Slide Constituents

| Slide | Role | Content Constituents | Visual / Layout Cues | V3 Archetype Mapping |
|---|---|---|---|---|
| 1 | Cover | Title: "The 10x AI Engineering Approach"; date: April 2026 | Full-width photographic/AI background, green top brand bar, oversized "10x" highlight, compact date. Avoid full-black backgrounds. | `hero_title` |
| 2 | Definition | Characteristics of 10x AI professionals: architecture-first, AI-driven problem-solving, zoom in/out, systems thinking, fast learning/teaching, security-first mindset | Six modular capability blocks in two rows; each block has a small icon/accent line and concise body text. | `hero_statement_with_support_columns` split into two slides if needed |
| 3 | Delivery framework | Three connected frameworks: Architecture to Code, Code Generation, Code to Production; each contains 4 operating bullets | Three large connected stage cards with colored headers/icons and directional flow. | `process_flow` |
| 4 | Candidate selection | Hiring context plus three areas: profiles to target, evaluation criteria, talent sourcing | Three large columns with color-coded icons and dense but bounded text. | `hero_statement_with_support_columns` |
| 5 | Pod packaging | 10x AI pods for Test Unit/Others; composition, pricing, engagement model, scope; premium offshore pricing 10-15K/resource/month | Four quadrant operating model with center divider; pricing statement highlighted; mix of dashed outlines and color accents. | `comparison_split` or two `hero_statement_with_support_columns` slides |
| 6 | Outcomes | Faster time-to-value, higher quality/reliability, AI maturity uplift, ROI, economic advantage | Left-side stacked outcome callouts over a photographic business/ROI image on the right. | `content_with_visual` |
| 7 | Campus rollout overview | Six-stage funnel: HackerRank, business problem, solution presentation, HR/org fit, offer/rollout, psychometric test; plus teams/platform handoff | Top horizontal 6-step pipeline with durations and descriptions; bottom swimlane showing Talent Teams, Technical Panels, HR, Eightfold, HackerRank. | `process_flow` + `timeline_roadmap` |
| 8 | Level 1 test detail | HackerRank baseline screen; Python, SQL, GenAI/RAG, timing, question pool depth, controls, signal criteria | Dense assessment card with skill tiles, question types, timing, and bottom "signal" band. | `content_with_visual` |
| 9 | Level 1 screenshot | HackerRank test snapshot | Single large platform screenshot framed by a light border. | `content_with_visual` |
| 10 | Level 2 detail | Business problem/system design; structure, complexity, timing, output, evaluation, example problem statements | Top parameter cards, middle evaluation strip, bottom two example problem statements, summary signal band. | `comparison_split` or `content_with_visual` |
| 11 | Level 3 detail | Solution presentation/technical panel interview; format, panel, timing, focus, sample Q&A | Top parameter cards, middle evaluation strip, bottom sample Q&A split by example, signal band. | `comparison_split` |
| 12 | Final assessment | HR interview + offer rollout; behavior, attitude, personality fit; offer rollout and onboarding/training timeline | Multi-row process/assessment board with three evaluation cards and lower onboarding timeline. | `timeline_roadmap` |
| 13 | Operational mechanics | Platforms: Eightfold and HackerRank; owners: TA, business leaders, technical panel, HR; operating principle | Dense owner/platform matrix with four role columns and platform cards. | Split into `process_flow` plus `hero_statement_with_support_columns` |
| 14 | Section/close | The 10x AI Engineering Approach | Dark-purple/patterned transition cover with decorative diagonal pills and bold title. | `hero_title` using light-safe brand treatment |
| 15 | Closing brand | Ascendion global AI/software engineering positioning and legal/footer copy | AI face imagery, green footer brand band, concise positioning paragraph. | `content_with_visual` |

## Benchmark Intent

Use this reference to test whether V3 can produce a detailed deck that:

- Maintains a consistent brand system across 10+ slides.
- Uses process and assessment structures without overlapping headers or content.
- Breaks dense source content into multiple readable slides instead of cramming.
- Uses screenshots or visual placeholders as real slide objects, not decoration.
- Preserves a clear narrative from "what the role is" to "how we package, assess, hire, and operate it."

