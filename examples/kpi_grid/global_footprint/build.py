"""Example: kpi_grid / global_footprint

Six headline scale-of-business metrics laid out in a 2-row × 3-column grid
under a shared header bar, with **vertical line dividers between columns**
instead of the per-cell accent bars used by ``capability_snapshot``. Each
cell shows a large display-size value (in accent_1) above a short noun-led
label.

Source inspiration: assets/Corp Deck 2025 - Nov.pptx slide 3
("An AI-Powered Software Engineering Disruptor"). The original packs 8
stats into a 4×2 grid with thin vertical line connectors between columns
("11,000+ / 400 / 4 / 36% / 40+ / 13 / 10 / 500+"). This example collapses
to 6 stats — the kpi_grid archetype caps at 6 — by selecting the most
brand-relevant scale measures: Ascenders, Clients, AI Studios, Fortune-500
share, Countries, Global Delivery Hubs.

Style differentiation vs. ``capability_snapshot``:
- divider style: line connectors between columns (here) vs. per-cell
  accent bars (there)
- value treatment: display type size (here) vs. title size in stat block
- accent strategy: monochrome_plus_one (numbers + thin dividers) vs.
  full_palette (rotated accents per cell)

Run:
    PYTHONPATH=. .venv/bin/python examples/kpi_grid/global_footprint/build.py
"""

from pathlib import Path

from src.ppt_runtime import (
    Rect,
    Tokens,
    add_line,
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
SUBTLE = tokens.color("accent_6")
TXT = tokens.color("text_primary")
TXT2 = tokens.color("text_secondary")

# ---------------------------------------------------------------------------
# Build slide
# ---------------------------------------------------------------------------

slide = canvas.add_slide("header_light")

draw_header_bar(
    slide,
    kicker="Global footprint",
    title="An AI-powered software engineering disruptor scaling globally",
    canvas=canvas,
    tokens=tokens,
)

# Six stats in a 2-row × 3-column grid. Column dividers are drawn ONCE
# spanning both rows, not per cell — the visual signature borrowed from
# Corp Deck S03.
stats = [
    ("11,000+", "Ascenders globally"),
    ("400",     "Enterprise clients"),
    ("4",       "AI studios"),
    ("36%",     "Of Fortune 500 are clients"),
    ("13",      "Countries"),
    ("10",      "Global delivery hubs"),
]

cols = 3
rows = 2
grid_top = canvas.body_top + tokens.spacing("lg")
grid_h = canvas.body_top + canvas.body_height - grid_top - tokens.spacing("md")
col_w = canvas.body_width // cols
row_h = grid_h // rows
pad = tokens.spacing("md")

# Column dividers (vertical lines between cols) — span the full grid height.
for c in range(1, cols):
    x = canvas.body_left + c * col_w
    add_line(
        slide,
        x, grid_top + tokens.spacing("xs"),
        x, grid_top + grid_h - tokens.spacing("xs"),
        color=SUBTLE,
        width_pt=0.75,
    )

# Stat tiles
for i, (value, label) in enumerate(stats):
    row, col = divmod(i, cols)
    cell_left = canvas.body_left + col * col_w
    cell_top = grid_top + row * row_h

    # Large display-size value
    value_h = tokens.spacing("xl") + tokens.spacing("sm")
    add_text(
        slide,
        Rect(cell_left + pad, cell_top + tokens.spacing("sm"),
             col_w - 2 * pad, value_h),
        value,
        type_style=tokens.type("display"),
        color=C1,
        bold=True,
    )

    # Body-style label below
    label_top = cell_top + tokens.spacing("sm") + value_h + tokens.spacing("xs")
    label_h = row_h - (label_top - cell_top) - tokens.spacing("sm")
    add_text(
        slide,
        Rect(cell_left + pad, label_top, col_w - 2 * pad, label_h),
        label,
        type_style=tokens.type("body"),
        color=TXT2,
    )

# Row divider (horizontal) between row 1 and row 2 — subtle visual rhythm.
mid_y = grid_top + row_h
add_line(
    slide,
    canvas.body_left + tokens.spacing("xs"), mid_y,
    canvas.body_left + canvas.body_width - tokens.spacing("xs"), mid_y,
    color=SUBTLE,
    width_pt=0.5,
)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

canvas.save(OUTPUT_PATH)
print(f"OK  saved {OUTPUT_PATH}")
