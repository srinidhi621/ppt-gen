"""Example: timeline_roadmap / development_arc

Reproduces Slide 5 from the 10x program plan deck.
Layout: subtitle, then three equal-width phase cards with accent bar,
when/name headers, divider, body text, and risk callout boxes.

Source: alternate-approach/build_v3.py (slide 5)

Run:
    PYTHONPATH=. .venv/bin/python examples/timeline_roadmap/development_arc/build.py
"""

from pathlib import Path

from src.ppt_runtime import (
    Grid,
    Rect,
    Tokens,
    add_line,
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def phase_card(slide, rect, when, name, what, risk):
    """Development phase card with accent bar, body, and risk callout."""
    pad = tokens.spacing("md")
    add_rect(slide, rect, fill=BG, line=SUBTLE)
    add_rect(slide, Rect(rect.left, rect.top, rect.width, tokens.spacing("xs")), fill=C2)

    add_text(slide, Rect(rect.left + pad, rect.top + tokens.spacing("md"),
                         rect.width - 2 * pad, tokens.spacing("md")),
             when, type_style=tokens.type("kicker"), color=C2)
    add_text(slide, Rect(rect.left + pad, rect.top + tokens.spacing("lg") + tokens.spacing("sm"),
                         rect.width - 2 * pad, tokens.spacing("xl")),
             name, type_style=tokens.type("subtitle"), color=C1, bold=True)

    # Divider line
    div_y = rect.top + tokens.spacing("xl") * 2 + tokens.spacing("md")
    add_line(slide, rect.left + pad, div_y, rect.right - pad, div_y, color=SUBTLE, width_pt=0.5)

    add_text(slide, Rect(rect.left + pad, div_y + tokens.spacing("sm"),
                         rect.width - 2 * pad, tokens.spacing("xl") * 3),
             what, type_style=tokens.type("body"), color=TXT)

    # Risk callout
    risk_h = tokens.spacing("xl") * 2 + tokens.spacing("md")
    risk_top = rect.bottom - risk_h - tokens.spacing("sm")
    risk_rect = Rect(rect.left + tokens.spacing("sm"), risk_top,
                     rect.width - tokens.spacing("md"), risk_h)
    add_rect(slide, risk_rect, fill=MUTED)
    add_text(slide, Rect(risk_rect.left + pad, risk_rect.top + tokens.spacing("xs"),
                         risk_rect.width - 2 * pad, tokens.spacing("md")),
             "WATCH FOR", type_style=tokens.type("caption"), color=C2, bold=True)
    add_text(slide, Rect(risk_rect.left + pad, risk_rect.top + tokens.spacing("md") + tokens.spacing("xs"),
                         risk_rect.width - 2 * pad, risk_h - tokens.spacing("lg")),
             risk, type_style=tokens.type("caption"), color=TXT2)


# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")
g = Grid(canvas, cols=12, gutter="md")

draw_header_bar(slide, kicker="05  |  After admit",
                title="Selection is 20%. The development arc is 80%.",
                canvas=canvas, tokens=tokens)

sub = g.span(col=1, col_span=12, top=canvas.body_top, height_emu=tokens.spacing("lg"))
add_text(slide, sub,
         "If we cannot protect the runway, we should not run the program. "
         "This is the failure mode that quietly kills these initiatives.",
         type_style=tokens.type("body"), color=TXT2)

phases = [
    ("MONTHS 1\u20133", "PROTECTED RUNWAY",
     "60% protected time. A real problem. A named sponsor. "
     "NOT on standard delivery utilization.",
     "Requires written executive air cover. A Delivery VP will try to break this in week 2."),
    ("MONTHS 3\u20139", "SHADOW + LEAD",
     "Pair with a Principal Engineer on a real client engagement. "
     "Lead one workstream end-to-end.",
     "Quarterly review on five anchored dimensions: framing, leverage, taste, ownership, teaching."),
    ("MONTHS 9\u201318", "FORCE MULTIPLIER",
     "Own a small team or a reusable practice asset \u2014 playbook, internal tool, eval harness.",
     "Promotion or off-ramp at month 18. Off-ramp to senior IC track is graduation, not failure."),
]

ph_top = canvas.body_top + tokens.spacing("xl")
ph_h = canvas.body_top + canvas.body_height - ph_top
ph_regions = g.row(top=ph_top, height_emu=ph_h, items=[(4, "p1"), (4, "p2"), (4, "p3")])
for (when, name, what, risk), key in zip(phases, ["p1", "p2", "p3"]):
    phase_card(slide, ph_regions[key], when, name, what, risk)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
