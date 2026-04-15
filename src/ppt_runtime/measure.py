"""Text measurement via Pillow + bundled substitute fonts.

All measurements are at 72 DPI (1 pt = 1 px). Pixel dimensions are
converted to EMU via the constant 12 700 EMU/px.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import ImageFont

from .errors import PptRuntimeError, TokenNotFoundError

# 1 pt = 1 px at 72 DPI; 1 inch = 914400 EMU = 72 pt → 1 pt = 12700 EMU
_PX_TO_EMU = 12700

_FONTS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "fonts"
_font_map: dict | None = None
_font_cache: dict[tuple, ImageFont.FreeTypeFont] = {}


# ---------------------------------------------------------------------------
# Font resolution
# ---------------------------------------------------------------------------


def _load_font_map() -> dict[str, dict]:
    global _font_map
    if _font_map is None:
        with open(_FONTS_DIR / "font_map.json") as f:
            data = json.load(f)
        _font_map = {}
        for entry in data["mappings"]:
            _font_map[entry["substitute_family"]] = entry["files"]
    return _font_map


def _resolve_font_path(font_family: str, bold: bool = False) -> Path:
    fm = _load_font_map()
    files = fm.get(font_family)
    if files is None:
        raise PptRuntimeError(
            f"No font files mapped for '{font_family}'. "
            f"Available families: {', '.join(sorted(fm))}"
        )
    if bold and "bold" in files:
        return _FONTS_DIR / files["bold"]
    if "regular" in files:
        return _FONTS_DIR / files["regular"]
    return _FONTS_DIR / next(iter(files.values()))


def _get_font(font_family: str, size_pt: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (font_family, size_pt, bold)
    if key not in _font_cache:
        path = _resolve_font_path(font_family, bold)
        _font_cache[key] = ImageFont.truetype(str(path), size=size_pt)
    return _font_cache[key]


# ---------------------------------------------------------------------------
# Word wrapping
# ---------------------------------------------------------------------------


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width_px: float) -> list[str]:
    """Greedy word-wrap that preserves explicit line breaks."""
    paragraphs = text.split("\n")
    if not paragraphs:
        return [""]

    lines: list[str] = []
    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue

        current = words[0]
        for word in words[1:]:
            candidate = current + " " + word
            bbox = font.getbbox(candidate)
            if (bbox[2] - bbox[0]) <= max_width_px:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)

    return lines


def _measure_lines(
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    line_height_px: float,
) -> tuple[int, int]:
    max_w_px = 0
    for line in lines:
        bbox = font.getbbox(line)
        w_px = bbox[2] - bbox[0]
        if w_px > max_w_px:
            max_w_px = w_px

    total_h_px = line_height_px * max(len(lines), 1)
    return (int(max_w_px * _PX_TO_EMU), int(total_h_px * _PX_TO_EMU))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def measure_text(
    text: str,
    type_style: dict,
    max_width_emu: int | None = None,
) -> tuple[int, int]:
    """Measure text extents using Pillow.

    Args:
        text: The string to measure.
        type_style: Dict from ``tokens.type()`` — must contain
            ``font``, ``size_pt``, ``bold``, ``line``.
        max_width_emu: If provided, word-wrap within this width and
            return multi-line height.

    Returns:
        ``(width_emu, height_emu)`` tuple.
    """
    font_family = type_style["font"]
    size_pt = type_style["size_pt"]
    bold = type_style.get("bold", False)
    line_factor = type_style.get("line", 1.2)
    line_height_px = size_pt * line_factor

    font = _get_font(font_family, size_pt, bold)

    if not text:
        return (0, int(line_height_px * _PX_TO_EMU))

    if max_width_emu is None:
        return _measure_lines(text.split("\n"), font, line_height_px)

    max_width_px = max_width_emu / _PX_TO_EMU
    lines = _wrap_text(text, font, max_width_px)
    return _measure_lines(lines, font, line_height_px)


def shrink_to_fit(
    text: str,
    rect,
    base: str,
    min_style: str,
    tokens,
) -> str:
    """Find the largest type style from *base* down to *min_style* that
    fits *text* inside *rect*.

    Tries each style in the type scale (sorted by ``size_pt`` descending)
    between *base* and *min_style* inclusive.  Returns the first style
    whose wrapped height fits within ``rect.height``.  If none fit,
    returns *min_style*.

    Args:
        text: The string to fit.
        rect: A :class:`Rect` with ``.width`` and ``.height`` in EMU.
        base: Starting (largest) type-style name.
        min_style: Smallest acceptable type-style name.
        tokens: A :class:`Tokens` instance.

    Returns:
        The name of the fitting type style.
    """
    scale = tokens.type_scale
    ordered = sorted(scale.items(), key=lambda x: x[1]["size_pt"], reverse=True)

    base_size = scale.get(base, {}).get("size_pt")
    min_size = scale.get(min_style, {}).get("size_pt")
    if base_size is None:
        raise TokenNotFoundError(f"Base style '{base}' not found in type scale")
    if min_size is None:
        raise TokenNotFoundError(f"Min style '{min_style}' not found in type scale")

    for name, style in ordered:
        if style["size_pt"] > base_size:
            continue
        if style["size_pt"] < min_size:
            break
        w, h = measure_text(text, style, max_width_emu=rect.width)
        if w <= rect.width and h <= rect.height:
            return name

    return min_style
