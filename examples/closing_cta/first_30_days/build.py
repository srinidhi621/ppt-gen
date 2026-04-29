"""Example: closing_cta / first_30_days

Closing slide that pairs a claim-style call-to-action with three concrete
next-step bullets. The headline owns the page; the bullets give the
audience exactly three things they should do or expect after the deck.

Source inspiration: assets/template/Ascendion-Data Practice-Capability Deck_final.pptx
slide 19 ('Next Steps') and slide 25 ('Thank You'), and assets/template/
Business Process Agentification (Session 4).pptx slide 26 ('Thank you').
The originals are minimal placeholder closes; this example richens the
pattern with three concrete next-step items so the slide actually advances
a sale or hand-off.

Run:
    PYTHONPATH=. .venv/bin/python examples/closing_cta/first_30_days/build.py
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
C2 = tokens.color("accent_2")
TXT = tokens.color("text_primary")
TXT2 = tokens.color("text_secondary")
TXT_W = tokens.color("text_on_dark")

# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")
g = Grid(canvas, cols=12, gutter="md")

draw_header_bar(
    slide,
    kicker="Next steps",
    title="Let’s lock the first 30 days before scaling",
    canvas=canvas,
    tokens=tokens,
)

# Three numbered next-step rows. Each row: large numeral + label + body.
bullets = [
    ("01", "Sign discovery SOW",
     "Confirm scope, named owners, and a one-week kickoff window."),
    ("02", "Run a 5-day capability audit",
     "Map gaps in data, talent, and tooling against the target operating model."),
    ("03", "Produce a 30-60-90 plan",
     "Prioritized backlog with named delivery leads, dates, and success criteria."),
]

block_top = canvas.body_top + tokens.spacing("xl") + tokens.spacing("md")
block_h = canvas.body_top + canvas.body_height - block_top - tokens.spacing("xl")
row_gutter = tokens.spacing("md")
row_h = (block_h - row_gutter * 2) // 3
pad = tokens.spacing("md")
num_w = tokens.spacing("xl") * 2

for i, (num, label, body) in enumerate(bullets):
    rt = block_top + i * (row_h + row_gutter)
    # Numeral on the left in a colored block
    num_rect = Rect(canvas.body_left, rt, num_w, row_h)
    add_rect(slide, num_rect, fill=C1)
    add_text(
        slide,
        Rect(num_rect.left + pad, num_rect.top + pad,
             num_rect.width - 2 * pad, row_h - 2 * pad),
        num,
        type_style=tokens.type("title"),
        color=TXT_W,
        fill=C1,
    )
    # Label + body to the right
    text_left = num_rect.right + tokens.spacing("md")
    text_w = canvas.body_left + canvas.body_width - text_left
    label_h = tokens.spacing("lg")
    add_text(
        slide,
        Rect(text_left, rt + tokens.spacing("xs"), text_w, label_h),
        label,
        type_style=tokens.type("subtitle"),
        color=TXT,
        bold=True,
    )
    add_text(
        slide,
        Rect(text_left, rt + tokens.spacing("xs") + label_h, text_w,
             row_h - label_h - tokens.spacing("xs")),
        body,
        type_style=tokens.type("body"),
        color=TXT2,
    )

# Closing accent stripe along the bottom — reads as a rule-line under the CTA.
strip_h = tokens.spacing("xs")
add_rect(
    slide,
    Rect(canvas.body_left,
         canvas.body_top + canvas.body_height - strip_h,
         canvas.body_width,
         strip_h),
    fill=C2,
)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
