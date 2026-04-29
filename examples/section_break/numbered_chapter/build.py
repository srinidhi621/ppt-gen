"""Example: section_break / numbered_chapter

Chapter divider that resets the deck rhythm. Right half is a full-bleed
accent panel (stand-in for an editorial photo); left half holds a large
section number and the chapter title underneath.

Source inspiration: assets/template/Business Process Agentification (Session 4).pptx
slides 3, 5, 13, 17, 24 — all 5 chapter dividers in that deck use this exact
3-shape pattern (right-half image + number + title).

Run:
    PYTHONPATH=. .venv/bin/python examples/section_break/numbered_chapter/build.py
"""

from pathlib import Path

from src.ppt_runtime import (
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

C1 = tokens.color("accent_1")
C2 = tokens.color("accent_2")
TXT = tokens.color("text_primary")
TXT_W = tokens.color("text_on_dark")

# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("blank")

# Right half: full-bleed accent panel (visual anchor — substitutes for an
# editorial photo on a real chapter divider).
half_left = canvas.slide_width // 2
add_rect(
    slide,
    Rect(half_left, 0, canvas.slide_width - half_left, canvas.slide_height),
    fill=C1,
)

# Thin secondary accent strip running along the bottom of the slide on the
# left half — visually links the divider to the deck's accent system without
# repeating the right-panel hue.
strip_h = tokens.spacing("xs")
add_rect(
    slide,
    Rect(0, canvas.slide_height - strip_h, half_left, strip_h),
    fill=C2,
)

# Left half content cluster.
# Section number sits at upper-third; section title sits below it.
left_pad = tokens.spacing("xl")
left_w = half_left - left_pad - tokens.spacing("lg")

num_top = canvas.slide_height // 3 - tokens.spacing("xl")
num_h = tokens.spacing("xl") * 2
add_text(
    slide,
    Rect(left_pad, num_top, left_w, num_h),
    "03",
    type_style=tokens.type("display"),
    color=C1,
    bold=True,
)

title_top = num_top + num_h + tokens.spacing("md")
title_h = tokens.spacing("xl") * 3
add_text(
    slide,
    Rect(left_pad, title_top, left_w, title_h),
    "Operating model and pod design",
    type_style=tokens.type("title"),
    color=TXT,
)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
