"""Example: comparison_split / two_tracks

Reproduces Slide 2 from the 10x program plan deck.
Layout: subtitle line, two large side-by-side track cards with dark
headers and label/value rows, plus a footer note.

Source: alternate-approach/build_v3.py (slide 2)

Run:
    PYTHONPATH=. .venv/bin/python examples/comparison_split/two_tracks/build.py
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
SUBTLE = tokens.color("accent_6")
TXT = tokens.color("text_primary")
TXT2 = tokens.color("text_secondary")
TXT_W = tokens.color("text_on_dark")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def track_card(slide, rect, name, profile, rows):
    """Large card with dark header and label/value rows."""
    header_h = tokens.spacing("xl") + tokens.spacing("md")
    add_rect(slide, rect, fill=BG, line=SUBTLE)
    add_rect(slide, Rect(rect.left, rect.top, rect.width, header_h), fill=C1)
    pad = tokens.spacing("md")
    add_text(slide, Rect(rect.left + pad, rect.top + tokens.spacing("sm"),
                         rect.width - 2 * pad, tokens.spacing("lg")),
             name, font_name="Space Grotesk", font_size_pt=20, bold=True, color=TXT_W)
    add_text(slide, Rect(rect.left + pad, rect.top + tokens.spacing("lg") + tokens.spacing("sm"),
                         rect.width - 2 * pad, tokens.spacing("md")),
             profile, type_style=tokens.type("caption"), color=TXT_W)

    y = rect.top + header_h + tokens.spacing("md")
    for label, val in rows:
        add_text(slide, Rect(rect.left + pad, y, tokens.spacing("xl") * 3, tokens.spacing("lg")),
                 label, type_style=tokens.type("kicker"), color=C2)
        add_text(slide, Rect(rect.left + pad + tokens.spacing("xl") * 3, y,
                             rect.width - 3 * pad - tokens.spacing("xl") * 3,
                             tokens.spacing("xl") * 2),
                 val, type_style=tokens.type("body"), color=TXT)
        y += tokens.spacing("xl") * 2


# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")
g = Grid(canvas, cols=12, gutter="md")

draw_header_bar(slide, kicker="02  |  Program shape",
                title="Two tracks. Small cohorts. On purpose.", canvas=canvas, tokens=tokens)

sub_rect = g.span(col=1, col_span=12, top=canvas.body_top, height_emu=tokens.spacing("lg"))
add_text(slide, sub_rect,
         "A 10x program with 200 admits is not a 10x program. We optimize for precision, not recall.",
         type_style=tokens.type("body"), color=TXT2)

card_top = canvas.body_top + tokens.spacing("xl")
card_h = canvas.body_top + canvas.body_height - card_top - tokens.spacing("lg")
lr = g.row(top=card_top, height_emu=card_h, items=[(6, "left"), (6, "right")])

track_card(slide, lr["left"], "ASCENDER TRACK",
           "0\u20132 yrs experience  |  external + internal",
           [("Cohort size", "10\u201315 per cohort"),
            ("Cadence", "Twice yearly"),
            ("Test for", "Decomposition under ambiguity. Taste in deciding what NOT to fix. "
                         "Healthy AI use the candidate can defend line by line.")])

track_card(slide, lr["right"], "PRINCIPAL TRACK",
           "2\u20136 yrs experience  |  lateral + skip-level nomination",
           [("Cohort size", "10\u201315 per cohort"),
            ("Cadence", "Twice yearly"),
            ("Test for", "Sequencing and trade-off articulation. Resisting the urge to rewrite. "
                         "Systems thinking, governance awareness, ability to teach.")])

# Footer note
footer = g.span(col=1, col_span=12,
                top=canvas.body_top + canvas.body_height - tokens.spacing("md"),
                height_emu=tokens.spacing("md"))
add_text(slide, footer,
         "Internal nominations run from day one and enter at Stage 2. Highest-yield source.",
         type_style=tokens.type("kicker"), color=C1)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
