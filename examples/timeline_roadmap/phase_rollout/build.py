"""Example: timeline_roadmap / phase_rollout

Four sequential phases laid out horizontally with phase number, name,
2-3 activity bullets, and a duration pill. Differs from
``development_arc`` (3 phases with risk callouts) — this is a denser
4-phase rollout pattern with explicit week durations and connector
arrows between phases.

Source inspiration: assets/ground_truth/internal_inbox/designer_reference_slides.pptx
slide 21 (S21 — "Roadmap & Timeline – Phase 2.0"). Original has 4 phase
blocks with rounded-corner duration tags ("6 weeks", "8 weeks", "6 weeks")
and "Feedback Alignment" descriptions per phase, connected by directional
arrows. This example reproduces the 4-phase shape with simplified phase
contents and adds explicit phase numbering for executive readability.

Style differentiation vs. ``development_arc``:
- phase count: 4 (here) vs. 3 (there)
- per-phase elements: number + name + 2-3 bullets + duration pill (here)
  vs. when/name + body + risk callout (there)
- density: high (4 columns × 5 elements) vs. medium-high

Run:
    PYTHONPATH=. .venv/bin/python examples/timeline_roadmap/phase_rollout/build.py
"""

from pathlib import Path

from src.ppt_runtime import (
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

C1 = tokens.color("accent_1")
C2 = tokens.color("accent_2")
SUBTLE = tokens.color("accent_6")
BG = tokens.color("bg_primary")
TXT = tokens.color("text_primary")
TXT2 = tokens.color("text_secondary")
TXT_W = tokens.color("text_on_dark")

# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")

draw_header_bar(
    slide,
    kicker="Rollout plan",
    title="Four phases move the program from MVP to scale in 26 weeks",
    canvas=canvas,
    tokens=tokens,
)

# Four phases: number, name, activities, duration.
phases = [
    ("01", "Foundation",   "6 weeks",
     ["Stand up agentic core engine", "Wire baseline telemetry", "Set up engagement governance"]),
    ("02", "MVP",          "8 weeks",
     ["Showcase agent-human collaboration", "Land first business use case", "Run UAT with named users"]),
    ("03", "Scale",        "6 weeks",
     ["Expand to two more workflows", "Add automation depth", "Tighten observability"]),
    ("04", "Production",   "6 weeks",
     ["Full production readiness", "Dashboards for ongoing ops", "Hand off to client SRE"]),
]

block_top = canvas.body_top + tokens.spacing("lg")
block_h = canvas.body_top + canvas.body_height - block_top - tokens.spacing("md")
gutter = tokens.spacing("md")
col_w = (canvas.body_width - gutter * (len(phases) - 1)) // len(phases)

# Connector line spanning the timeline (sits behind phase blocks)
line_y = block_top + tokens.spacing("xl")
add_line(
    slide,
    canvas.body_left + col_w // 2, line_y,
    canvas.body_left + canvas.body_width - col_w // 2, line_y,
    color=SUBTLE,
    width_pt=1.0,
)

for i, (num, name, duration, activities) in enumerate(phases):
    left = canvas.body_left + i * (col_w + gutter)
    pad = tokens.spacing("sm")

    # Phase number — bold accent disc on the connector line. The text
    # shape's own fill draws the disc; no separate rect needed (a separate
    # rect would 100%-overlap the text box and trip VH-13).
    disc_size = tokens.spacing("lg") + tokens.spacing("sm")
    disc_left = left + col_w // 2 - disc_size // 2
    disc_top = line_y - disc_size // 2
    add_text(
        slide,
        Rect(disc_left, disc_top, disc_size, disc_size),
        num,
        type_style=tokens.type("subtitle"),
        color=TXT_W,
        bold=True,
        fill=C1,
    )

    # Phase name below disc
    name_top = disc_top + disc_size + tokens.spacing("sm")
    name_h = tokens.spacing("lg")
    add_text(
        slide,
        Rect(left, name_top, col_w, name_h),
        name,
        type_style=tokens.type("subtitle"),
        color=TXT,
        bold=True,
    )

    # Duration pill — text-with-fill draws the pill itself.
    pill_top = name_top + name_h + tokens.spacing("xs")
    pill_h = tokens.spacing("md")
    pill_w = tokens.spacing("xl") + tokens.spacing("md")
    pill_left = left + (col_w - pill_w) // 2
    add_text(
        slide,
        Rect(pill_left, pill_top, pill_w, pill_h),
        duration,
        type_style=tokens.type("kicker"),
        color=TXT_W,
        bold=True,
        fill=C2,
    )

    # Activity bullets in a card below pill
    card_top = pill_top + pill_h + tokens.spacing("md")
    card_h = block_top + block_h - card_top
    add_rect(
        slide,
        Rect(left, card_top, col_w, card_h),
        fill=BG,
        line=SUBTLE,
    )

    # Activity bullets — give each line generous height since narrow
    # columns force most activities to wrap onto 2 lines.
    bullet_h = tokens.spacing("lg") + tokens.spacing("xs")
    by = card_top + tokens.spacing("sm")
    for activity in activities:
        # Bullet marker (small accent square)
        marker_size = tokens.spacing("xs")
        add_rect(
            slide,
            Rect(left + pad, by + tokens.spacing("sm"),
                 marker_size, marker_size),
            fill=C1,
        )
        # Bullet text — wide enough box to fit two wrapped lines
        add_text(
            slide,
            Rect(left + pad + tokens.spacing("md"), by,
                 col_w - pad * 2 - tokens.spacing("md"), bullet_h),
            activity,
            type_style=tokens.type("body"),
            color=TXT2,
        )
        by += bullet_h + tokens.spacing("xs")

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
