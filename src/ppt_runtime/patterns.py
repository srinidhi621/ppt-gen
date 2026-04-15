"""Opinionated shape-level patterns built on top of shapes.py.

Each pattern composes multiple shapes into a single visual element
(card, header bar, stat block, kicker) within a bounding :class:`Rect`.
"""

from __future__ import annotations

from pptx.dml.color import RGBColor

from .grid import Rect
from .shapes import add_rect, add_text


def draw_card(
    slide,
    rect,
    title: str,
    body: str,
    *,
    accent: RGBColor,
    tokens,
    title_style: str = "subtitle",
    body_style: str = "body",
    padding_name: str = "md",
):
    """Draw a card with a coloured title bar and body text.

    Layout (top to bottom within *rect*):
    - thin accent bar (xs height)
    - title region (title style line height + padding)
    - body text fills remaining space
    """
    pad = tokens.spacing(padding_name)
    bar_h = tokens.spacing("xs")
    t_style = tokens.type(title_style)
    b_style = tokens.type(body_style)
    title_h = int(t_style["size_pt"] * t_style.get("line", 1.2) * 12700) + pad

    # Accent bar
    add_rect(slide, Rect(rect.left, rect.top, rect.width, bar_h), fill=accent)

    # Title
    title_rect = Rect(
        rect.left + pad, rect.top + bar_h + pad // 2,
        rect.width - 2 * pad, title_h,
    )
    add_text(
        slide, title_rect, title,
        type_style=t_style, color=tokens.color("text_primary"),
        bold=True,
    )

    # Body
    body_top = title_rect.bottom + pad // 2
    body_rect = Rect(
        rect.left + pad, body_top,
        rect.width - 2 * pad, rect.bottom - body_top - pad,
    )
    add_text(
        slide, body_rect, body,
        type_style=b_style, color=tokens.color("text_primary"),
    )


def draw_header_bar(
    slide,
    kicker: str,
    title: str,
    *,
    canvas,
    tokens,
):
    """Draw a slide header: top accent bar, kicker with dot, and title.

    Uses the full slide width.  Places elements relative to the canvas
    safe area.
    """
    ds = canvas.design_system
    sa = ds["canvas"]["safe_area"]
    sw = ds["canvas"]["width_emu"]
    left = sa["left_emu"]
    pad = tokens.spacing("sm")

    # Top accent bar (full width, xs height)
    bar_h = tokens.spacing("xs")
    add_rect(
        slide,
        Rect(0, 0, sw, bar_h),
        fill=tokens.color("accent_1"),
    )

    # Kicker dot + text
    dot_size = tokens.spacing("sm")
    dot_top = sa["top_emu"] + pad
    add_rect(
        slide,
        Rect(left, dot_top, dot_size, dot_size),
        fill=tokens.color("accent_2"),
    )

    k_style = tokens.type("kicker")
    kicker_rect = Rect(
        left + dot_size + pad // 2, dot_top,
        sw - left * 2 - dot_size - pad, int(dot_size),
    )
    add_text(
        slide, kicker_rect, kicker,
        type_style=k_style, color=tokens.color("accent_2"),
    )

    # Title
    t_style = tokens.type("title")
    title_top = dot_top + dot_size + pad
    title_rect = Rect(
        left, title_top,
        sw - left * 2, int(t_style["size_pt"] * t_style.get("line", 1.08) * 12700),
    )
    add_text(
        slide, title_rect, title,
        type_style=t_style, color=tokens.color("text_primary"),
    )


def draw_kicker(
    slide,
    rect,
    text: str,
    *,
    tokens,
):
    """Draw a kicker label (small bold uppercase text with accent colour)."""
    k_style = tokens.type("kicker")
    add_text(
        slide, rect, text,
        type_style=k_style, color=tokens.color("accent_2"),
    )


def draw_stat_block(
    slide,
    rect,
    value: str,
    label: str,
    *,
    accent: RGBColor,
    tokens,
):
    """Draw a stat block: accent bar on the left, large value, smaller label.

    Layout within *rect*:
    - thin vertical accent bar on the left (xs width)
    - value text (title style) in the top portion
    - label text (caption style) below
    """
    bar_w = tokens.spacing("xs")
    pad = tokens.spacing("sm")
    v_style = tokens.type("title")
    l_style = tokens.type("caption")

    # Accent bar
    add_rect(slide, Rect(rect.left, rect.top, bar_w, rect.height), fill=accent)

    # Value
    inner_left = rect.left + bar_w + pad
    inner_width = rect.width - bar_w - pad
    value_h = int(v_style["size_pt"] * v_style.get("line", 1.08) * 12700) + pad
    add_text(
        slide,
        Rect(inner_left, rect.top + pad, inner_width, value_h),
        value,
        type_style=v_style, color=tokens.color("text_primary"),
        bold=True,
    )

    # Label
    label_top = rect.top + pad + value_h
    add_text(
        slide,
        Rect(inner_left, label_top, inner_width, rect.bottom - label_top - pad),
        label,
        type_style=l_style, color=tokens.color("text_secondary"),
    )
