"""Example: comparison_split / discriminators

Reproduces Slide 4 from the 10x program plan deck.
Layout: left panel with AI-use rubric (3 columns) + right panel with
a 2x3 stat grid. Both panels under a shared header.

Source: alternate-approach/build_v3.py (slide 4)

Run:
    PYTHONPATH=. .venv/bin/python examples/comparison_split/discriminators/build.py
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
TXT2 = tokens.color("text_secondary")
TXT_W = tokens.color("text_on_dark")


# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")
g = Grid(canvas, cols=12, gutter="md")

draw_header_bar(slide, kicker="04  |  Where this differs",
                title="The two design decisions that determine whether it works",
                canvas=canvas, tokens=tokens)

lr = g.row(top=canvas.body_top, height_emu=canvas.body_height,
           items=[(6, "left"), (6, "right")])

# --- Left: AI-use rubric ---
left_r = lr["left"]
pad = tokens.spacing("md")
add_text(slide, Rect(left_r.left, left_r.top, left_r.width, tokens.spacing("md")),
         "AI-USE RUBRIC", type_style=tokens.type("kicker"), color=C2)
add_text(slide, Rect(left_r.left, left_r.top + tokens.spacing("md"),
                     left_r.width, tokens.spacing("md")),
         "Scored explicitly. Without this, calibration collapses.",
         type_style=tokens.type("caption"), color=TXT2)

rubric_top = left_r.top + tokens.spacing("xl")
rubric_h = left_r.height - tokens.spacing("xl")
rubric_cols = [
    ("HEALTHY USE", C1,
     "Used AI for boilerplate, scaffolding, tests. Verified outputs. Can explain every line."),
    ("OVER-RELIANCE", C2,
     "Cannot explain choices. Inconsistent style. Hallucinated comments. Tests don't match code."),
    ("AVOIDANCE", SUBTLE,
     "Avoided AI in an AI-appropriate task. Slower with no quality gain."),
]
rub_gutter = tokens.spacing("xs")
rub_w = (left_r.width - 2 * rub_gutter) // 3
for i, (h, c, body) in enumerate(rubric_cols):
    rl = left_r.left + i * (rub_w + rub_gutter)
    r = Rect(rl, rubric_top, rub_w, rubric_h)
    add_rect(slide, r, fill=MUTED)
    add_rect(slide, Rect(rl, rubric_top, rub_w, tokens.spacing("lg")), fill=c)
    add_text(slide, Rect(rl + pad, rubric_top + tokens.spacing("xs"),
                         rub_w - 2 * pad, tokens.spacing("md")),
             h, type_style=tokens.type("caption"), color=TXT_W, fill=c, bold=True)
    add_text(slide, Rect(rl + pad, rubric_top + tokens.spacing("lg") + tokens.spacing("sm"),
                         rub_w - 2 * pad, rubric_h - tokens.spacing("xl")),
             body, type_style=tokens.type("caption"), color=TXT)

# --- Right: Base rates stat grid ---
right_r = lr["right"]
add_text(slide, Rect(right_r.left, right_r.top, right_r.width, tokens.spacing("md")),
         "BASE RATES PER TRACK PER CYCLE", type_style=tokens.type("kicker"), color=C2)
add_text(slide, Rect(right_r.left, right_r.top + tokens.spacing("md"),
                     right_r.width, tokens.spacing("md")),
         "If they want recall, this is the wrong program.",
         type_style=tokens.type("caption"), color=TXT2)

stats = [
    ("1,500\u201315,000", "applicants"),
    ("~400", "Stage 2 invitees"),
    ("~50", "Stage 3 invitees"),
    ("10\u201315", "admits"),
    ("~6 hrs", "reviewer cost / admit"),
    ("25%", "false-positive tolerance"),
]
stat_top = right_r.top + tokens.spacing("xl")
stat_gutter = tokens.spacing("xs")
sw_ = (right_r.width - stat_gutter) // 2
sh_ = (right_r.height - tokens.spacing("xl") - 2 * stat_gutter) // 3
for idx, (big, label) in enumerate(stats):
    col, row = idx % 2, idx // 2
    sl = right_r.left + col * (sw_ + stat_gutter)
    st = stat_top + row * (sh_ + stat_gutter)
    cell = Rect(sl, st, sw_, sh_)
    add_rect(slide, cell, fill=BG, line=SUBTLE)
    add_rect(slide, Rect(sl, st, tokens.spacing("xs"), sh_), fill=C2)
    add_text(slide, Rect(sl + pad, st + tokens.spacing("sm"), sw_ - 2 * pad, tokens.spacing("xl")),
             big, type_style=tokens.type("metric_value"), color=C1)
    add_text(slide, Rect(sl + pad, st + tokens.spacing("xl") + tokens.spacing("sm"),
                         sw_ - 2 * pad, tokens.spacing("lg")),
             label, type_style=tokens.type("caption"), color=TXT2)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
