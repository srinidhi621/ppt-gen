"""ppt_runtime — runtime library for V3 builder code."""

from .canvas import Canvas, load_template
from .composers import (
    compose_card_row,
    compose_split_columns,
    compose_stat_grid,
    compose_timeline,
)
from .errors import CanvasNotFoundError, GridError, PptRuntimeError, TokenNotFoundError
from .grid import Grid, Rect
from .measure import measure_text, shrink_to_fit
from .patterns import draw_card, draw_header_bar, draw_kicker, draw_stat_block
from .shapes import add_connector, add_image, add_line, add_rect, add_text
from .tokens import Tokens

__all__ = [
    # canvas
    "Canvas",
    "load_template",
    # grid
    "Grid",
    "Rect",
    # tokens
    "Tokens",
    # measure
    "measure_text",
    "shrink_to_fit",
    # shapes
    "add_rect",
    "add_text",
    "add_image",
    "add_line",
    "add_connector",
    # patterns
    "draw_card",
    "draw_header_bar",
    "draw_kicker",
    "draw_stat_block",
    # composers
    "compose_card_row",
    "compose_stat_grid",
    "compose_split_columns",
    "compose_timeline",
    # errors
    "PptRuntimeError",
    "TokenNotFoundError",
    "CanvasNotFoundError",
    "GridError",
]
