"""Example: matrix_grid / capability_matrix

Six capability cells in a 2-row × 3-column matrix under a shared header.
Each cell has a top accent bar (rotated through the theme palette), a
short capability title, and a 1-2 sentence body. Use when six (or fewer
fillable) parallel items need to be read as a structured set rather than
a sequence — capability matrices, component overviews, scope grids.

Source inspiration: assets/ground_truth/internal_inbox/designer_reference_slides.pptx
slide 14 (S14 — "Our proposition for Globe Telecom") which uses a denser
4×3 matrix with row labels + column headers (Gap Analysis / Tech
Landscape / Talent / Roadmap × Objective / Focus / Value Adds). Our
flat-cards schema cannot express the 2D row+column structure directly,
so this example flattens to 6 representative capability cells. A 2D
variant would require schema extension (`row_labels`, `column_labels`).

Run:
    PYTHONPATH=. .venv/bin/python examples/matrix_grid/capability_matrix/build.py
"""

from pathlib import Path

from src.ppt_runtime import (
    Grid,
    Rect,
    Tokens,
    add_rect,
    add_text,
    draw_header_bar,
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
TXT = tokens.color("text_primary")
TXT2 = tokens.color("text_secondary")
SUBTLE = tokens.color("accent_6")
BG = tokens.color("bg_primary")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def matrix_cell(slide, rect, title, body, accent_color):
    """Capability cell: top accent bar + title + body."""
    bar_h = tokens.spacing("xs")
    pad = tokens.spacing("md")
    add_rect(slide, rect, fill=BG, line=SUBTLE)
    add_rect(slide, Rect(rect.left, rect.top, rect.width, bar_h), fill=accent_color)

    title_top = rect.top + bar_h + tokens.spacing("sm")
    title_h = tokens.spacing("lg")
    add_text(
        slide,
        Rect(rect.left + pad, title_top, rect.width - 2 * pad, title_h),
        title,
        type_style=tokens.type("subtitle"),
        color=TXT,
        bold=True,
    )

    body_top = title_top + title_h + tokens.spacing("xs")
    body_h = rect.bottom - body_top - pad
    add_text(
        slide,
        Rect(rect.left + pad, body_top, rect.width - 2 * pad, body_h),
        body,
        type_style=tokens.type("body"),
        color=TXT2,
    )

# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")
g = Grid(canvas, cols=12, gutter="md")

draw_header_bar(
    slide,
    kicker="AI engagement framework",
    title="Six capability areas span our enterprise AI engagements",
    canvas=canvas,
    tokens=tokens,
)

# Six cells in a 2-row × 3-column matrix. Each cell carries a distinct
# theme accent so the row reads as a structured set.
cells = [
    ("Gap Analysis",          "Identify gaps in current AI capabilities, adoption, and infrastructure across the enterprise.",                "accent_1"),
    ("Tech Landscape",        "Assess the existing tech stack and surface integration gaps for new generative-AI tooling.",                   "accent_2"),
    ("Talent Assessment",     "Evaluate workforce readiness, surface skill gaps, and recommend targeted upskilling paths.",                   "accent_3"),
    ("Data Readiness",        "Audit data quality, governance, and access controls before AI workloads land in production.",                  "accent_4"),
    ("Roadmap & Strategy",    "Define short, medium, and long-term AI goals with phased delivery and partnership dependencies.",              "accent_6"),
    ("Operating Model",       "Design pod composition, oversight cadence, and review gates for sustained delivery quality.",                  "accent_1"),
]

cards_top = canvas.body_top + tokens.spacing("md")
cards_h = canvas.body_top + canvas.body_height - cards_top - tokens.spacing("sm")

cols = 3
rows = 2
gutter = tokens.spacing("sm")
cell_w = (canvas.body_width - (cols - 1) * gutter) // cols
cell_h = (cards_h - (rows - 1) * gutter) // rows

for i, (title, body, accent_name) in enumerate(cells):
    row, col = divmod(i, cols)
    rect = Rect(
        canvas.body_left + col * (cell_w + gutter),
        cards_top + row * (cell_h + gutter),
        cell_w,
        cell_h,
    )
    matrix_cell(slide, rect, title, body, tokens.color(accent_name))

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
