"""Example: hero_statement_with_support_columns / operating_principle

Reproduces Slide 1 from the 10x program plan deck.
Layout: hero band spanning full width with accent bar, followed by
three equal-width support cards below.

Source: alternate-approach/build_v3.py (slide 1)

Run:
    PYTHONPATH=. .venv/bin/python examples/hero_statement_with_support_columns/operating_principle/build.py
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
MUTED = tokens.color("accent_5")
TXT = tokens.color("text_primary")
TXT_W = tokens.color("text_on_dark")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hero_band(slide, grid, text, kicker_text=None):
    """Dark hero band spanning full width with optional kicker."""
    band = grid.span(col=1, col_span=12,
                     top=canvas.body_top, height_emu=tokens.spacing("xl") * 4)
    add_rect(slide, band, fill=C1)
    # Accent bar on left edge
    add_rect(slide, Rect(band.left, band.top, tokens.spacing("xs"), band.height), fill=C2)

    inner_left = band.left + tokens.spacing("md") * 2
    inner_w = band.width - tokens.spacing("md") * 4

    if kicker_text:
        k_rect = Rect(inner_left, band.top + tokens.spacing("md"), inner_w, tokens.spacing("lg"))
        add_text(slide, k_rect, kicker_text,
                 type_style=tokens.type("kicker"), color=C2)
        txt_top = k_rect.bottom + tokens.spacing("sm")
    else:
        txt_top = band.top + tokens.spacing("md")

    txt_rect = Rect(inner_left, txt_top,
                    inner_w, band.bottom - txt_top - tokens.spacing("md"))
    add_text(slide, txt_rect, text,
             type_style=tokens.type("hero"), color=TXT_W, fill=C1)
    return band


def support_card(slide, rect, heading, body):
    """Light card with accent bar, heading, and body."""
    add_rect(slide, rect, fill=MUTED)
    add_rect(slide, Rect(rect.left, rect.top, tokens.spacing("lg"), tokens.spacing("xs")), fill=C2)
    pad = tokens.spacing("md")
    add_text(slide, Rect(rect.left + pad, rect.top + pad, rect.width - 2 * pad, tokens.spacing("lg")),
             heading, type_style=tokens.type("kicker"), color=C1)
    add_text(slide, Rect(rect.left + pad, rect.top + pad + tokens.spacing("lg") + tokens.spacing("sm"),
                         rect.width - 2 * pad, rect.height - 3 * pad - tokens.spacing("lg")),
             body, type_style=tokens.type("body"), color=TXT)


# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")
g = Grid(canvas, cols=12, gutter="md")

draw_header_bar(slide, kicker="01  |  The thesis",
                title="What this program is for", canvas=canvas, tokens=tokens)

band = hero_band(slide, g,
    "Find engineers who use judgment and AI leverage to remove work \u2014\n"
    "then put them on a track that doesn't destroy that capability.",
    kicker_text="OPERATING PRINCIPLE")

cols_data = [
    ("THE PROBLEM",
     "Conventional hiring rewards pedigree, narrow correctness, and confidence. "
     "None of these find force multipliers."),
    ("WHAT WE WON'T DO",
     "No essay prompts. No personality interviews. No steering committees. "
     "No '10x' marketing language externally."),
    ("WHAT WE WILL DO",
     "Verifiable artifacts. Scaffolded take-homes with AI allowed and scored. "
     "Anchored defense panels. Clear runway after admission to ensure continuity"),
]
card_top = band.bottom + tokens.spacing("md")
card_h = canvas.body_top + canvas.body_height - card_top
regions = g.row(top=card_top, height_emu=card_h, items=[(4, "c1"), (4, "c2"), (4, "c3")])
for (heading, body), name in zip(cols_data, ["c1", "c2", "c3"]):
    support_card(slide, regions[name], heading, body)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
