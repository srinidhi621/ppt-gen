"""Section-level composers that lay out multi-shape regions.

Each composer takes a bounding :class:`Rect` (the "region"), content
data, and design-system tokens, and draws a complete section inside
that region.  The builder calls composers with a region from the grid;
the composer handles subdivision into individual shapes.
"""

from __future__ import annotations

from pptx.dml.color import RGBColor

from .grid import Rect
from .patterns import draw_card, draw_stat_block
from .shapes import add_rect, add_text


def compose_card_row(
    slide,
    region,
    items: list[dict],
    *,
    accent: RGBColor,
    tokens,
    gutter_name: str = "md",
    text_color: RGBColor | None = None,
):
    """Lay out N equal-width cards horizontally within *region*.

    Each item in *items* is a dict with ``title`` and ``body`` keys.
    """
    n = len(items)
    if n == 0:
        return

    gutter = tokens.spacing(gutter_name)
    total_gutter = (n - 1) * gutter
    card_w = (region.width - total_gutter) // n

    for i, item in enumerate(items):
        card_left = region.left + i * (card_w + gutter)
        card_rect = Rect(card_left, region.top, card_w, region.height)
        draw_card(
            slide, card_rect,
            title=item["title"],
            body=item["body"],
            accent=accent,
            tokens=tokens,
            text_color=text_color,
        )


def compose_stat_grid(
    slide,
    region,
    metrics: list[dict],
    *,
    cols: int = 3,
    tokens,
    value_color: RGBColor | None = None,
    label_color: RGBColor | None = None,
):
    """Lay out a grid of stat blocks within *region*.

    Each metric in *metrics* is a dict with ``value`` and ``label`` keys.
    Blocks are arranged in a grid with *cols* columns.
    """
    n = len(metrics)
    if n == 0:
        return

    rows = (n + cols - 1) // cols
    gutter = tokens.spacing("sm")

    cell_w = (region.width - (cols - 1) * gutter) // cols
    cell_h = (region.height - (rows - 1) * gutter) // rows

    for i, metric in enumerate(metrics):
        row, col = divmod(i, cols)
        cell_left = region.left + col * (cell_w + gutter)
        cell_top = region.top + row * (cell_h + gutter)
        cell_rect = Rect(cell_left, cell_top, cell_w, cell_h)

        draw_stat_block(
            slide, cell_rect,
            value=metric["value"],
            label=metric["label"],
            accent=tokens.color("accent_1"),
            tokens=tokens,
            value_color=value_color,
            label_color=label_color,
        )


def compose_split_columns(
    slide,
    region,
    left_content: str,
    right_content: str,
    *,
    split: float = 0.5,
    tokens,
    left_style: str = "body",
    right_style: str = "body",
    text_color: RGBColor | None = None,
):
    """Lay out a two-panel split within *region*.

    *split* is the fraction of width given to the left panel (0.0–1.0).
    *text_color* defaults to ``tokens.color("text_primary")``.
    """
    if text_color is None:
        text_color = tokens.color("text_primary")

    gutter = tokens.spacing("md")
    left_w = int((region.width - gutter) * split)
    right_w = region.width - gutter - left_w

    left_rect = Rect(region.left, region.top, left_w, region.height)
    right_rect = Rect(region.left + left_w + gutter, region.top, right_w, region.height)

    add_text(
        slide, left_rect, left_content,
        type_style=tokens.type(left_style),
        color=text_color,
    )
    add_text(
        slide, right_rect, right_content,
        type_style=tokens.type(right_style),
        color=text_color,
    )


def compose_timeline(
    slide,
    region,
    phases: list[dict],
    *,
    accent: RGBColor,
    tokens,
):
    """Lay out a horizontal timeline within *region*.

    Each phase in *phases* is a dict with ``label`` and ``body`` keys.

    Layout:
    - thin horizontal track line across the region
    - equal-width phase columns below the track
    - each column: accent dot on the track, label, body text
    """
    n = len(phases)
    if n == 0:
        return

    gutter = tokens.spacing("sm")
    track_y = region.top + tokens.spacing("lg")
    track_h = tokens.spacing("xs")
    dot_size = tokens.spacing("sm")

    # Track line
    add_rect(
        slide,
        Rect(region.left, track_y, region.width, track_h),
        fill=tokens.color("accent_5"),
    )

    col_w = (region.width - (n - 1) * gutter) // n
    label_style = tokens.type("kicker")
    body_style = tokens.type("body")
    label_h = int(label_style["size_pt"] * label_style.get("line", 1.1) * 12700)
    content_top = track_y + track_h + dot_size + tokens.spacing("sm")

    for i, phase in enumerate(phases):
        col_left = region.left + i * (col_w + gutter)

        # Accent dot on the track
        dot_left = col_left + col_w // 2 - dot_size // 2
        add_rect(
            slide,
            Rect(dot_left, track_y - dot_size // 3, dot_size, dot_size),
            fill=accent,
        )

        # Label
        add_text(
            slide,
            Rect(col_left, content_top, col_w, label_h),
            phase["label"],
            type_style=label_style,
            color=accent,
            align="center",
        )

        # Body
        body_top = content_top + label_h + tokens.spacing("xs")
        add_text(
            slide,
            Rect(col_left, body_top, col_w, region.bottom - body_top),
            phase["body"],
            type_style=body_style,
            color=tokens.color("text_primary"),
            align="center",
        )
