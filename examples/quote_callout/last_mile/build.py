"""Example: quote_callout / last_mile

Single oversized statement with attribution beneath it. The quote is
the entire purpose of the slide — no supporting bullets, no metrics,
no cards. A thin accent vertical bar on the left anchors the quote
to the brand palette.

Source inspiration: assets/Corp Deck 2025 - Nov.pptx slide 17
("… AI-powered solutions don't work 'out of the box' / Nearly every
company needs help to go the Last Mile for value / That's where we
come in!"). The original stacks three statements; this example
collapses to the single canonical quote_callout shape (one
statement + attribution).

Run:
    PYTHONPATH=. .venv/bin/python examples/quote_callout/last_mile/build.py
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
TXT2 = tokens.color("text_secondary")

# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")

# Vertical accent bar on the left edge of the body region — anchors the quote
# to the brand without a header bar (a quote_callout is not a content slide).
bar_w = tokens.spacing("xs")
bar_top = canvas.body_top + tokens.spacing("xl")
bar_h = canvas.body_height - tokens.spacing("xl") * 2
add_rect(
    slide,
    Rect(canvas.body_left, bar_top, bar_w, bar_h),
    fill=C1,
)

# Oversized opening glyph (decorative quotation mark in display style).
glyph_left = canvas.body_left + bar_w + tokens.spacing("md")
glyph_top = bar_top
glyph_w = tokens.spacing("xl") * 2
glyph_h = tokens.spacing("xl")
add_text(
    slide,
    Rect(glyph_left, glyph_top, glyph_w, glyph_h),
    "“",  # left double quotation mark
    type_style=tokens.type("display"),
    color=C2,
)

# The quote itself — single statement, hero type style.
quote_left = glyph_left
quote_top = glyph_top + glyph_h + tokens.spacing("xs")
quote_w = canvas.body_left + canvas.body_width - quote_left - tokens.spacing("md")
quote_h = tokens.spacing("xl") * 4
add_text(
    slide,
    Rect(quote_left, quote_top, quote_w, quote_h),
    "AI-powered solutions don’t work out of the box. "
    "Every enterprise needs the last mile of engineering "
    "to turn a model into measurable value.",
    type_style=tokens.type("hero"),
    color=TXT,
)

# Attribution beneath the quote.
attr_top = quote_top + quote_h + tokens.spacing("sm")
attr_h = tokens.spacing("md")
add_text(
    slide,
    Rect(quote_left, attr_top, quote_w, attr_h),
    "ASCENDION CORP DECK — NOV 2025",
    type_style=tokens.type("kicker"),
    color=C1,
)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
