"""Token lookups from design_system.json — colors, type styles, spacing."""

from __future__ import annotations

import json
from pathlib import Path

from pptx.dml.color import RGBColor

from .errors import TokenNotFoundError


class Tokens:
    """Typed access to design-system tokens.

    Usage::

        tokens = Tokens.from_design_system("assets/template/design_system.json")
        tokens.color("accent_1")   # → RGBColor
        tokens.type("title")       # → dict {font, size_pt, bold, line, ...}
        tokens.spacing("md")       # → int (EMU)
    """

    def __init__(self, design_system: dict) -> None:
        self._colors: dict = design_system["colors"]
        self._type_scale: dict = design_system["type_scale"]
        self._spacing: dict = design_system["spacing_scale"]

    @classmethod
    def from_design_system(cls, path: str | Path) -> Tokens:
        with open(Path(path)) as f:
            ds = json.load(f)
        return cls(ds)

    def color(self, name: str) -> RGBColor:
        hex_val = self._colors.get(name)
        if hex_val is None:
            raise TokenNotFoundError(
                f"Color token '{name}' not found. "
                f"Available: {', '.join(sorted(self._colors))}"
            )
        h = hex_val.lstrip("#")
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    def type(self, name: str) -> dict:
        style = self._type_scale.get(name)
        if style is None:
            raise TokenNotFoundError(
                f"Type style '{name}' not found. "
                f"Available: {', '.join(sorted(self._type_scale))}"
            )
        return dict(style)

    def spacing(self, name: str) -> int:
        key = f"{name}_emu"
        val = self._spacing.get(key)
        if val is None:
            raise TokenNotFoundError(
                f"Spacing token '{name}' not found. "
                f"Available: {', '.join(k.removesuffix('_emu') for k in sorted(self._spacing))}"
            )
        return val
