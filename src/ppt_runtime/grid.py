"""Grid math and named rectangles.

Provides a 12-column (configurable) grid over a canvas body region.
All coordinates are in EMU. Columns are 1-indexed.
"""

from __future__ import annotations

from .errors import GridError


class Rect:
    """Axis-aligned rectangle in EMU coordinates."""

    __slots__ = ("left", "top", "width", "height")

    def __init__(self, left: int, top: int, width: int, height: int) -> None:
        self.left = left
        self.top = top
        self.width = width
        self.height = height

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def __repr__(self) -> str:
        return (
            f"Rect(left={self.left}, top={self.top}, "
            f"width={self.width}, height={self.height})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rect):
            return NotImplemented
        return (
            self.left == other.left
            and self.top == other.top
            and self.width == other.width
            and self.height == other.height
        )


class Grid:
    """Column grid over a canvas body region.

    Usage::

        g = Grid(canvas, cols=12, gutter="md")
        rect = g.span(col=1, col_span=4, top=canvas.body_top, height_emu=500000)
        regions = g.row(top=..., height_emu=..., items=[(4, "left"), (8, "right")])
    """

    def __init__(self, canvas, cols: int = 12, gutter: str = "md") -> None:
        ds = canvas.design_system
        grid_cfg = ds["grid"]

        gutter_key = f"gutter_{gutter}_emu"
        if gutter_key not in grid_cfg:
            available = [
                k.removeprefix("gutter_").removesuffix("_emu")
                for k in grid_cfg
                if k.startswith("gutter_")
            ]
            raise GridError(
                f"Unknown gutter size '{gutter}'. Available: {', '.join(available)}"
            )

        self._body_left: int = canvas.body_left
        self._body_top: int = canvas.body_top
        self._body_width: int = canvas.body_width
        self._body_height: int = canvas.body_height
        self._cols: int = cols
        self._gutter_emu: int = grid_cfg[gutter_key]

        total_gutter = (cols - 1) * self._gutter_emu
        self._col_width: float = (self._body_width - total_gutter) / cols

    @property
    def cols(self) -> int:
        return self._cols

    @property
    def col_width_emu(self) -> int:
        return int(self._col_width)

    @property
    def gutter_emu(self) -> int:
        return self._gutter_emu

    def span(self, col: int, col_span: int, top: int, height_emu: int) -> Rect:
        """Return a Rect spanning *col_span* columns starting at *col* (1-indexed).

        ``top`` and ``height_emu`` are absolute EMU values — the caller
        decides vertical placement.
        """
        if col < 1:
            raise GridError(f"col must be ≥ 1, got {col}")
        if col_span < 1:
            raise GridError(f"col_span must be ≥ 1, got {col_span}")
        if col + col_span - 1 > self._cols:
            raise GridError(
                f"span(col={col}, col_span={col_span}) exceeds "
                f"{self._cols}-column grid"
            )

        left = self._body_left + (col - 1) * (self._col_width + self._gutter_emu)
        width = col_span * self._col_width + (col_span - 1) * self._gutter_emu

        return Rect(int(left), int(top), int(width), int(height_emu))

    def row(
        self,
        top: int,
        height_emu: int,
        items: list[tuple[int, str]],
    ) -> dict[str, Rect]:
        """Lay out named items left-to-right across the grid.

        *items* is a list of ``(col_span, name)`` tuples.
        Returns a dict mapping each *name* to its :class:`Rect`.
        """
        total_span = sum(span for span, _ in items)
        if total_span > self._cols:
            raise GridError(
                f"Row items span {total_span} columns but grid has {self._cols}"
            )

        result: dict[str, Rect] = {}
        current_col = 1
        for col_span, name in items:
            result[name] = self.span(current_col, col_span, top, height_emu)
            current_col += col_span

        return result
