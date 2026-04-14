# V1 Catalog Mining Notes

Extracted from V1-era catalogs on 2026-04-14 during SLICE-002 cleanup.
These notes inform `design_system.json` authoring (SLICE-003).

## From `template_style_baselines_v1.json`

Template `corp_deck_2025`:
- Title band ratio: 12-22% of slide height
- Body margins: 0.35"-0.80"
- Spacing scale (inches): xs=0.08, sm=0.14, md=0.24, lg=0.36
- Type sizes: title 30-44pt, heading 20-32pt, body 12-18pt, caption 10-12pt

## From `component_catalog_v1.json`

Capacity values to cross-reference with V3 archetype metadata:
- title_slide: max 2 subtitle lines, preferred 11.5"x4.5"
- section_break: max 10 title words
- content_block: max 6 bullets
- text_with_image: max 5 bullets, preferred 12"x5.5"
- metric_cards: max 4 cards
- bento_grid: max 6 cells
- icon_grid: max 8 cells
- timeline: max 8 events
- process_flow: max 7 steps
- comparison_columns: max 3 columns
- data_table: max 8 rows x 5 columns

Planner hints: min 5 distinct component types per 15 slides, max 2 same-component streak, prefer visual components for cue-rich sections.

## From `planner_policy_v1.json`

Asset diversity rules (carry forward to V3 enrichment phase):
- Min 6 unique visual assets per 10 slides
- Max reuse per branded image: 2
- No adjacent reuse of same icon concept
- Target 80% of slides have a visual element

Routing guidance:
- Force image on section break slides
- Avoid single-layout streak >3 slides
- Move text-heavy details to speaker notes

## From `visual_primitive_policy_v1.json`

Declutter rules (carry forward to V3 scanner/reviewer):
- Max 3 visual primitives per slide
- Avoid decorative elements without message support
- Preserve whitespace buffers
- Single visual focal point per slide

## From `component_examples_v1.json`

Good/bad example patterns (carry forward to example metadata):
- Good timeline: 4 concise events with single-phrase captions
- Bad timeline: 9 events with paragraph captions (should be in notes)
- Good icon_grid: 2x3 balanced grid with short labels
