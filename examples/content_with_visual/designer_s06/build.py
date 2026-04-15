"""Example: content_with_visual / designer_s06

Decomposition of designer reference slide S06: Solution flow with
connectors. A split layout showing a structured solution approach
on the left with supporting details or visual elements on the right.

Source: assets/ground_truth/internal_inbox/designer_reference_slides.pptx (slide 5)

Note: This is an approximation using ppt_runtime. The original slide
may use custom connector shapes, icons, or complex visual elements
that cannot be fully expressed via the runtime shape API.

Run:
    PYTHONPATH=. .venv/bin/python examples/content_with_visual/designer_s06/build.py
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
TXT_W = tokens.color("text_on_dark")


# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")
g = Grid(canvas, cols=12, gutter="md")

draw_header_bar(slide, kicker="SOLUTION ARCHITECTURE",
                title="End-to-end delivery model with integrated checkpoints",
                canvas=canvas, tokens=tokens)

lr = g.row(top=canvas.body_top, height_emu=canvas.body_height,
           items=[(5, "left"), (7, "right")])

# --- Left: Solution flow steps ---
left_r = lr["left"]
pad = tokens.spacing("md")

add_text(slide, Rect(left_r.left, left_r.top, left_r.width, tokens.spacing("md")),
         "DELIVERY FLOW", type_style=tokens.type("kicker"), color=C2)

flow_steps = [
    ("Discovery", "Stakeholder interviews, data audit, and capability mapping "
                  "to define scope and success criteria."),
    ("Architecture", "Design solution architecture with AI integration points, "
                     "data pipelines, and governance framework."),
    ("Build & Validate", "Iterative development with weekly demos, automated testing, "
                         "and performance benchmarking."),
    ("Deploy & Operate", "Production rollout with monitoring dashboards, runbooks, "
                         "and knowledge transfer to client teams."),
]

y = left_r.top + tokens.spacing("lg")
step_h = tokens.spacing("xl") * 2 + tokens.spacing("sm")

for i, (title, desc) in enumerate(flow_steps):
    # Accent bar
    add_rect(slide, Rect(left_r.left, y, tokens.spacing("xs"), step_h), fill=C1)

    # Title
    add_text(slide, Rect(left_r.left + tokens.spacing("sm"), y,
                         left_r.width - tokens.spacing("md"), tokens.spacing("md")),
             title, type_style=tokens.type("body"), color=C1, bold=True)

    # Description
    add_text(slide, Rect(left_r.left + tokens.spacing("sm"), y + tokens.spacing("md"),
                         left_r.width - tokens.spacing("md"),
                         step_h - tokens.spacing("md")),
             desc, type_style=tokens.type("caption"), color=TXT)

    y += step_h + tokens.spacing("xs")

    # Connector line between steps (except last)
    if i < len(flow_steps) - 1:
        line_x = left_r.left + tokens.spacing("xs") // 2
        add_line(slide, line_x, y - tokens.spacing("xs"),
                 line_x, y, color=SUBTLE, width_pt=1.0)

# --- Right: Key outcomes and metrics ---
right_r = lr["right"]

add_text(slide, Rect(right_r.left, right_r.top, right_r.width, tokens.spacing("md")),
         "KEY OUTCOMES & CHECKPOINTS", type_style=tokens.type("kicker"), color=C2)

# Outcomes grid (2x2)
outcomes = [
    ("95%+", "Test coverage on\ncritical paths"),
    ("< 2 wks", "Time to first\nproduction deploy"),
    ("3x", "Developer productivity\nimprovement"),
    ("Zero", "Critical incidents\nin first 90 days"),
]

grid_top = right_r.top + tokens.spacing("lg")
gutter = tokens.spacing("xs")
cell_w = (right_r.width - gutter) // 2
cell_h = (right_r.height - tokens.spacing("lg") - tokens.spacing("xl") * 3 - gutter) // 2

for idx, (value, label) in enumerate(outcomes):
    col, row = idx % 2, idx // 2
    cl = right_r.left + col * (cell_w + gutter)
    ct = grid_top + row * (cell_h + gutter)
    cell = Rect(cl, ct, cell_w, cell_h)
    add_rect(slide, cell, fill=BG, line=SUBTLE)
    add_rect(slide, Rect(cl, ct, tokens.spacing("xs"), cell_h), fill=C2)
    add_text(slide, Rect(cl + pad, ct + tokens.spacing("sm"),
                         cell_w - 2 * pad, tokens.spacing("xl")),
             value, font_name="Space Grotesk", font_size_pt=24, bold=True, color=C1)
    add_text(slide, Rect(cl + pad, ct + tokens.spacing("xl") + tokens.spacing("sm"),
                         cell_w - 2 * pad, cell_h - tokens.spacing("xl") - tokens.spacing("md")),
             label, type_style=tokens.type("caption"), color=TXT2)

# Bottom CTA bar
cta_top = grid_top + 2 * (cell_h + gutter) + tokens.spacing("sm")
cta_h = right_r.bottom - cta_top
add_rect(slide, Rect(right_r.left, cta_top, right_r.width, cta_h), fill=C1)
add_rect(slide, Rect(right_r.left, cta_top, tokens.spacing("xs"), cta_h), fill=C2)
add_text(slide, Rect(right_r.left + pad, cta_top + tokens.spacing("sm"),
                     right_r.width - 2 * pad, tokens.spacing("md")),
         "NEXT STEP", type_style=tokens.type("kicker"), color=C2)
add_text(slide, Rect(right_r.left + pad, cta_top + tokens.spacing("lg"),
                     right_r.width - 2 * pad, cta_h - tokens.spacing("xl")),
         "Schedule a 60-minute discovery workshop to map your current "
         "capabilities against the AI-readiness framework.",
         type_style=tokens.type("body"), color=TXT_W)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
