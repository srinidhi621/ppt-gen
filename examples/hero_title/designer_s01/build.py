"""Example: hero_title / designer_s01

Decomposition of designer reference slide S01: Hero title with
background visual. A light canvas with a large hero title, subtitle,
and brand accent elements.

Source: assets/ground_truth/internal_inbox/designer_reference_slides.pptx (slide 0)

Note: This is an approximation using ppt_runtime. The original slide
may use background images or gradients that cannot be fully expressed
via the runtime shape API. We focus on layout structure and typography.

Run:
    PYTHONPATH=. .venv/bin/python examples/hero_title/designer_s01/build.py
"""

from pathlib import Path

from src.ppt_runtime import (
    Grid,
    Rect,
    Tokens,
    add_rect,
    add_text,
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

# Shorthand colours
C1 = tokens.color("accent_1")
C2 = tokens.color("accent_2")
BG = tokens.color("bg_primary")
TXT = tokens.color("text_primary")
TXT2 = tokens.color("text_secondary")

# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")
g = Grid(canvas, cols=12, gutter="md")

# NOTE: canvas.add_slide() automatically sets the slide background
# based on the canvas theme — no full-slide rect needed.

# Top accent bar
bar_h = tokens.spacing("xs")
add_rect(slide, Rect(0, 0, canvas.slide_width, bar_h), fill=C1)

# Kicker / category label
kicker_rect = g.span(col=1, col_span=8,
                     top=canvas.body_top + tokens.spacing("xl"),
                     height_emu=tokens.spacing("lg"))
add_text(slide, kicker_rect, "ASCENDION",
         type_style=tokens.type("kicker"), color=C1)

# Hero title
title_rect = g.span(col=1, col_span=10,
                    top=canvas.body_top + tokens.spacing("xl") * 2,
                    height_emu=tokens.spacing("xl") * 4)
add_text(slide, title_rect,
         "Engineering the future\nwith AI-powered talent",
         type_style=tokens.type("display"), color=TXT, fill=BG)

# Subtitle
sub_rect = g.span(col=1, col_span=8,
                  top=canvas.body_top + tokens.spacing("xl") * 6,
                  height_emu=tokens.spacing("xl") * 2)
add_text(slide, sub_rect,
         "A new model for identifying and developing 10x engineers "
         "who combine judgment, AI leverage, and taste.",
         type_style=tokens.type("subtitle"), color=TXT2, fill=BG)

# Bottom accent line
accent_y = canvas.slide_height - tokens.spacing("xl")
accent_rect = Rect(canvas.body_left, accent_y,
                   tokens.spacing("xl") * 4, tokens.spacing("xs"))
add_rect(slide, accent_rect, fill=C2)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
