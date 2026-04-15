"""Example: content_with_visual / governance_and_risks

Reproduces Slide 6 from the 10x program plan deck.
Layout: left panel with governance roles (4 named owners with accent
bars), right panel with 3 numbered risks + "first moves" box below.

Source: alternate-approach/build_v3.py (slide 6)

Run:
    PYTHONPATH=. .venv/bin/python examples/content_with_visual/governance_and_risks/build.py
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
TXT2 = tokens.color("text_secondary")
TXT_W = tokens.color("text_on_dark")


# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")
g = Grid(canvas, cols=12, gutter="md")

draw_header_bar(slide, kicker="06  |  Make it real",
                title="Governance, the three risks that kill this, and the first moves",
                canvas=canvas, tokens=tokens)

lr = g.row(top=canvas.body_top, height_emu=canvas.body_height,
           items=[(5, "left"), (7, "right")])

# --- Left: Governance ---
left_r = lr["left"]
pad = tokens.spacing("md")
add_text(slide, Rect(left_r.left, left_r.top, left_r.width, tokens.spacing("md")),
         "GOVERNANCE \u2014 FOUR NAMED OWNERS, NO COMMITTEES",
         type_style=tokens.type("kicker"), color=C2)

owners = [
    ("Executive Sponsor",
     "One named VP. Air cover for protected runway. Authority to kill the program if quality slips."),
    ("Program Lead",
     "One named Director. End-to-end accountability. Rubric integrity. Calibration."),
    ("Tech Panel",
     "4\u20136 named Principals. Task design. Scoring. Defense panels."),
    ("TA Partner",
     "One named recruiter. Funnel mechanics. Candidate experience. Data."),
]
y = left_r.top + tokens.spacing("lg")
row_h = tokens.spacing("xl") * 2
for role, desc in owners:
    add_rect(slide, Rect(left_r.left, y, tokens.spacing("xs"), row_h), fill=C2)
    add_text(slide, Rect(left_r.left + tokens.spacing("sm"), y, left_r.width - tokens.spacing("md"),
                         tokens.spacing("md")),
             role, type_style=tokens.type("body"), color=C1, bold=True)
    add_text(slide, Rect(left_r.left + tokens.spacing("sm"), y + tokens.spacing("md"),
                         left_r.width - tokens.spacing("md"), row_h - tokens.spacing("md")),
             desc, type_style=tokens.type("caption"), color=TXT)
    y += row_h + tokens.spacing("xs")

# --- Right: Risks ---
right_r = lr["right"]
add_text(slide, Rect(right_r.left, right_r.top, right_r.width, tokens.spacing("md")),
         "THREE RISKS THAT WILL ACTUALLY KILL THIS",
         type_style=tokens.type("kicker"), color=C2)

risks = [
    "Delivery pressure breaks the protected runway in month 2.",
    "AI-use rubric drifts across panelists across cycles.",
    "Excellent ICs admitted with no senior IC ladder to graduate them onto.",
]
y = right_r.top + tokens.spacing("lg")
risk_h = tokens.spacing("xl")
for i, r in enumerate(risks, 1):
    add_rect(slide, Rect(right_r.left, y, right_r.width, risk_h), fill=MUTED)
    add_text(slide, Rect(right_r.left + tokens.spacing("sm"), y + tokens.spacing("xs"),
                         tokens.spacing("md"), tokens.spacing("md")),
             str(i), type_style=tokens.type("subtitle"), color=C2, bold=True)
    add_text(slide, Rect(right_r.left + tokens.spacing("lg"), y + tokens.spacing("xs"),
                         right_r.width - tokens.spacing("xl"), risk_h - tokens.spacing("sm")),
             r, type_style=tokens.type("caption"), color=TXT)
    y += risk_h + tokens.spacing("xs")

# First moves box
mv_top = y + tokens.spacing("sm")
mv_h = right_r.bottom - mv_top
add_rect(slide, Rect(right_r.left, mv_top, right_r.width, mv_h), fill=C1)
add_rect(slide, Rect(right_r.left, mv_top, tokens.spacing("xs"), mv_h), fill=C2)
add_text(slide, Rect(right_r.left + tokens.spacing("md"), mv_top + tokens.spacing("sm"),
                     right_r.width - tokens.spacing("lg"), tokens.spacing("md")),
         "FIRST THREE MOVES", type_style=tokens.type("kicker"), color=C2)

moves = [
    ("This week",
     "Get one VP to sign the protected-runway commitment in writing. No signature, no program."),
    ("Next 2 weeks",
     "Tech panel writes one Ascender task and one Principal task. Three Principals submit benchmarks."),
    ("Weeks 3\u20134",
     "Run internal pilot with 20 nominees. Decide on external Cohort 1 from data, not enthusiasm."),
]
y = mv_top + tokens.spacing("lg") + tokens.spacing("sm")
for when, what in moves:
    add_text(slide, Rect(right_r.left + tokens.spacing("md"), y,
                         tokens.spacing("xl") * 2 + tokens.spacing("lg"), tokens.spacing("md")),
             when, type_style=tokens.type("kicker"), color=C2)
    add_text(slide, Rect(right_r.left + tokens.spacing("xl") * 3, y,
                         right_r.width - tokens.spacing("xl") * 3 - tokens.spacing("md"),
                         tokens.spacing("xl")),
             what, type_style=tokens.type("caption"), color=TXT_W)
    y += tokens.spacing("xl")

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
