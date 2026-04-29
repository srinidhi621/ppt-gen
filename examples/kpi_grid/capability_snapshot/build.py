"""Example: kpi_grid / capability_snapshot

Six headline metrics laid out as a 3x2 stat grid under a shared header bar.
Each cell has a thin vertical accent bar, a large numeric value, and a short
descriptive label.

Source inspiration: assets/ground_truth/internal_inbox/designer_reference_slides.pptx
slide 15 (S15 - "AI Services Suite") — KPI band simplified to a clean kpi_grid shape.

Run:
    PYTHONPATH=. .venv/bin/python examples/kpi_grid/capability_snapshot/build.py
"""

from pathlib import Path

from src.ppt_runtime import (
    Grid,
    Rect,
    Tokens,
    add_rect,
    add_text,
    draw_header_bar,
    draw_stat_block,
    load_template,
)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_PATH = PROJECT_ROOT / "assets" / "template" / "template.pptx"
DS_PATH = PROJECT_ROOT / "assets" / "template" / "design_system.json"
OUTPUT_PATH = Path(__file__).resolve().parent / "output.pptx"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

canvas = load_template(TEMPLATE_PATH, DS_PATH)
tokens = Tokens.from_design_system(DS_PATH)

C1 = tokens.color("accent_1")
C2 = tokens.color("accent_2")
TXT = tokens.color("text_primary")
TXT2 = tokens.color("text_secondary")

# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")
g = Grid(canvas, cols=12, gutter="md")

draw_header_bar(
    slide,
    kicker="Capability snapshot",
    title="What 10x AI engineering looks like in production today",
    canvas=canvas,
    tokens=tokens,
)

# Sub-line introducing the metrics
sub_top = canvas.body_top + tokens.spacing("sm")
sub_h = tokens.spacing("md")
add_text(
    slide,
    Rect(canvas.body_left, sub_top, canvas.body_width, sub_h),
    "Six measured outcomes from production AI engagements over the last year.",
    type_style=tokens.type("caption"),
    color=TXT2,
)

# 3x2 stat grid below the sub-line — rotate accent colors per cell so the
# vertical bars carry the slide's full theme palette instead of a single hue.
grid_top = sub_top + sub_h + tokens.spacing("md")
grid_h = canvas.body_top + canvas.body_height - grid_top - tokens.spacing("sm")

metrics = [
    {"value": "1,100+",  "label": "Generative AI certified engineers", "accent": "accent_1"},
    {"value": "25+",     "label": "Production AI solutions shipped",   "accent": "accent_2"},
    {"value": "40%",     "label": "Average delivery cycle time reduction", "accent": "accent_3"},
    {"value": "150+",    "label": "Engineers in 10x AI pods",         "accent": "accent_4"},
    {"value": "$2.3M",   "label": "Annual operating savings per engagement", "accent": "accent_6"},
    {"value": "3 weeks", "label": "Time to first production deploy",  "accent": "accent_1"},
]

cols = 3
gutter = tokens.spacing("sm")
rows = (len(metrics) + cols - 1) // cols
cell_w = (canvas.body_width - (cols - 1) * gutter) // cols
cell_h = (grid_h - (rows - 1) * gutter) // rows

for i, m in enumerate(metrics):
    row, col = divmod(i, cols)
    cell = Rect(
        canvas.body_left + col * (cell_w + gutter),
        grid_top + row * (cell_h + gutter),
        cell_w,
        cell_h,
    )
    draw_stat_block(
        slide, cell,
        value=m["value"],
        label=m["label"],
        accent=tokens.color(m["accent"]),
        tokens=tokens,
        value_color=TXT,
        label_color=TXT2,
    )

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
