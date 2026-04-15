"""Example: process_flow / designer_s02

Decomposition of designer reference slide S02: Numbered infographic
overlay. A process flow with numbered steps overlaid on a structured
layout with step descriptions.

Source: assets/ground_truth/internal_inbox/designer_reference_slides.pptx (slide 1)

Note: This is an approximation using ppt_runtime. The original slide
may use custom shapes, icons, or image backgrounds that cannot be
fully expressed via the runtime shape API.

Run:
    PYTHONPATH=. .venv/bin/python examples/process_flow/designer_s02/build.py
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

# Shorthand colours
C1 = tokens.color("accent_1")
C2 = tokens.color("accent_2")
BG = tokens.color("bg_primary")
MUTED = tokens.color("accent_5")
SUBTLE = tokens.color("accent_6")
TXT = tokens.color("text_primary")
TXT_W = tokens.color("text_on_dark")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def numbered_step(slide, rect, number, title, description):
    """Numbered infographic step with large number, title, and description."""
    pad = tokens.spacing("md")

    # Card background
    add_rect(slide, rect, fill=BG, line=SUBTLE)

    # Number circle area (large number in accent color)
    num_h = tokens.spacing("xl") + tokens.spacing("lg")
    add_rect(slide, Rect(rect.left, rect.top, rect.width, num_h), fill=C1)
    add_text(slide, Rect(rect.left + pad, rect.top + tokens.spacing("sm"),
                         rect.width - 2 * pad, tokens.spacing("xl")),
             number, font_name="Space Grotesk", font_size_pt=32, bold=True, color=C2)

    # Title
    title_top = rect.top + num_h + tokens.spacing("sm")
    add_text(slide, Rect(rect.left + pad, title_top,
                         rect.width - 2 * pad, tokens.spacing("lg")),
             title, type_style=tokens.type("subtitle"), color=C1, bold=True)

    # Description
    desc_top = title_top + tokens.spacing("lg") + tokens.spacing("sm")
    add_text(slide, Rect(rect.left + pad, desc_top,
                         rect.width - 2 * pad,
                         rect.bottom - desc_top - pad),
             description, type_style=tokens.type("body"), color=TXT)


# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")
g = Grid(canvas, cols=12, gutter="md")

draw_header_bar(slide, kicker="OUR APPROACH",
                title="A structured path from assessment to impact",
                canvas=canvas, tokens=tokens)

steps = [
    ("01", "ASSESS",
     "Evaluate current capabilities against the AI-readiness framework. "
     "Identify gaps and opportunities."),
    ("02", "DESIGN",
     "Custom program architecture aligned to organizational maturity "
     "and strategic priorities."),
    ("03", "BUILD",
     "Develop talent pipelines with hands-on projects, mentorship, "
     "and progressive challenges."),
    ("04", "SCALE",
     "Operationalize the model across business units with governance "
     "and measurement frameworks."),
]

card_top = canvas.body_top + tokens.spacing("sm")
card_h = canvas.body_top + canvas.body_height - card_top
regions = g.row(top=card_top, height_emu=card_h,
                items=[(3, "s1"), (3, "s2"), (3, "s3"), (3, "s4")])
for (num, title, desc), key in zip(steps, ["s1", "s2", "s3", "s4"]):
    numbered_step(slide, regions[key], num, title, desc)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
