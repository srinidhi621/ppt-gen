"""Example: process_flow / funnel_stages

Reproduces Slide 3 from the 10x program plan deck.
Layout: four equal-width stage cards in a row, each with a numbered
dark header, body text, and a bottom stat section.

Source: alternate-approach/build_v3.py (slide 3)

Run:
    PYTHONPATH=. .venv/bin/python examples/process_flow/funnel_stages/build.py
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

def stage_card(slide, rect, num, when, name, what, funnel_label, funnel_val):
    """Funnel stage card with number, header, body, and bottom stats."""
    header_h = tokens.spacing("xl") + tokens.spacing("lg")
    pad = tokens.spacing("md")
    add_rect(slide, rect, fill=BG, line=SUBTLE)
    add_rect(slide, Rect(rect.left, rect.top, rect.width, header_h), fill=C1)
    add_text(slide, Rect(rect.left + pad, rect.top + tokens.spacing("sm"),
                         rect.width - 2 * pad, tokens.spacing("xl")),
             num, type_style=tokens.type("title"), color=TXT_W, fill=C1)
    add_text(slide, Rect(rect.left + pad, rect.top + tokens.spacing("sm") + tokens.spacing("xl"),
                         rect.width - 2 * pad, tokens.spacing("md")),
             when, type_style=tokens.type("kicker"), color=TXT_W, fill=C1)

    body_top = rect.top + header_h + tokens.spacing("sm")
    name_h = tokens.spacing("xl")
    add_text(slide, Rect(rect.left + pad, body_top, rect.width - 2 * pad, name_h),
             name, type_style=tokens.type("subtitle"), color=C1, bold=True)
    add_text(slide, Rect(rect.left + pad, body_top + name_h + tokens.spacing("sm"),
                         rect.width - 2 * pad, tokens.spacing("xl") * 4),
             what, type_style=tokens.type("body"), color=TXT)

    # Bottom stat
    bot_h = tokens.spacing("xl") + tokens.spacing("lg")
    bot_top = rect.bottom - bot_h
    add_rect(slide, Rect(rect.left, bot_top, rect.width, bot_h), fill=MUTED)
    add_text(slide, Rect(rect.left + pad, bot_top + tokens.spacing("xs"),
                         rect.width - 2 * pad, tokens.spacing("md")),
             funnel_label, type_style=tokens.type("caption"), color=SUBTLE, bold=True)
    add_text(slide, Rect(rect.left + pad, bot_top + tokens.spacing("md") + tokens.spacing("xs"),
                         rect.width - 2 * pad, tokens.spacing("lg")),
             funnel_val, type_style=tokens.type("subtitle"), color=C1, bold=True)


# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")
g = Grid(canvas, cols=12, gutter="sm")

draw_header_bar(slide, kicker="03  |  The funnel",
                title="Four stages. Five weeks. ~150 in, 8\u201312 out.",
                canvas=canvas, tokens=tokens)

stages = [
    ("01", "WEEK 1", "EVIDENCE GATE",
     "GitHub link + 3-min Loom + one shipped artifact. No essays.",
     "FUNNEL", "1,500\u201315,000 \u2192 ~400"),
    ("02", "WEEK 2\u20133", "SCAFFOLDED TAKE-HOME",
     "48 hrs. Real repo. AI allowed and expected. PR + 10-min walkthrough.",
     "FUNNEL", "~400 \u2192 ~50"),
    ("03", "WEEK 4", "DEFENSE PANEL",
     "60 min. Two panelists. Five anchored questions. Independent scoring.",
     "FUNNEL", "~50 \u2192 ~15"),
    ("04", "WEEK 5", "ADMIT DECISION",
     "30 min. Director + Principal. Confirms appetite. No new tech eval.",
     "FUNNEL", "10\u201315 admits"),
]

card_top = canvas.body_top + tokens.spacing("sm")
card_h = canvas.body_top + canvas.body_height - card_top
regions = g.row(top=card_top, height_emu=card_h,
                items=[(3, "s1"), (3, "s2"), (3, "s3"), (3, "s4")])
for (num, when, name, what, fl, fv), key in zip(stages, ["s1", "s2", "s3", "s4"]):
    stage_card(slide, regions[key], num, when, name, what, fl, fv)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
