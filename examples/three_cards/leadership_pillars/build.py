"""Example: three_cards / leadership_pillars

Three equal-weight cards in a row, each opening with a top accent bar in a
distinct theme color, a card title (subtitle style), and a 2-3 line body.
The pattern is the executive "three forces / three pillars / three challenges"
shape — a fast read, claim-led, no metrics.

Source inspiration:
- assets/Corp Deck 2025 - Nov.pptx slide 13 ("Leaders Are Wrestling With Three
  Challenges") — overall framing and headline shape (the source uses a TABLE
  shape that we cannot decompose, so this is structural inspiration only).
- assets/template/Business Process Agentification (Session 4).pptx slide 8
  ("Components of Agentic Platform Buildout") — multi-card shape on light bg.

Run:
    PYTHONPATH=. .venv/bin/python examples/three_cards/leadership_pillars/build.py
"""

from pathlib import Path

from src.ppt_runtime import (
    Grid,
    Rect,
    Tokens,
    draw_card,
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

# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")
g = Grid(canvas, cols=12, gutter="md")

draw_header_bar(
    slide,
    kicker="Three forces",
    title="Three forces are reshaping enterprise AI delivery",
    canvas=canvas,
    tokens=tokens,
)

# Three cards across the body region. Each card opens with a top accent bar
# in a different theme hue so the row is read as three distinct pillars.
cards = [
    {
        "title": "Talent",
        "body": (
            "AI-augmented engineers replace single-skill roles. "
            "Pods need architecture-first thinking and prompt-discipline "
            "habits, not just senior IC headcount."
        ),
        "accent": "accent_1",
    },
    {
        "title": "Tooling",
        "body": (
            "Code-gen, evaluation, and policy guardrails ship as one "
            "platform. Fragmented copilots without review gates "
            "create more rework than they save."
        ),
        "accent": "accent_2",
    },
    {
        "title": "Trust",
        "body": (
            "Production AI requires audit trails, model-of-record "
            "controls, and explicit human review on regulated paths. "
            "Without them, leaders cannot stand behind output."
        ),
        "accent": "accent_4",
    },
]

card_top = canvas.body_top + tokens.spacing("lg")
card_h = canvas.body_top + canvas.body_height - card_top - tokens.spacing("sm")
regions = g.row(
    top=card_top,
    height_emu=card_h,
    items=[(4, "c1"), (4, "c2"), (4, "c3")],
)

for c, key in zip(cards, ["c1", "c2", "c3"]):
    draw_card(
        slide,
        regions[key],
        title=c["title"],
        body=c["body"],
        accent=tokens.color(c["accent"]),
        tokens=tokens,
        title_style="hero",
        body_style="body",
    )

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
