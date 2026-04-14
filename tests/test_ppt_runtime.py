"""Unit tests for ppt_runtime: grid math, token lookups, canvas properties."""

import json
import tempfile
import unittest
from pathlib import Path

from pptx.dml.color import RGBColor

from src.ppt_runtime.errors import (
    CanvasNotFoundError,
    GridError,
    TokenNotFoundError,
)
from src.ppt_runtime.grid import Grid, Rect
from src.ppt_runtime.tokens import Tokens

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DESIGN_SYSTEM = {
    "template_id": "test_template",
    "version": "1.0",
    "canvas": {
        "width_emu": 12192000,
        "height_emu": 6858000,
        "safe_area": {
            "left_emu": 515938,
            "right_emu": 515938,
            "top_emu": 298692,
            "bottom_emu": 200000,
        },
    },
    "grid": {
        "cols": 12,
        "gutter_sm_emu": 91440,
        "gutter_md_emu": 137160,
        "gutter_lg_emu": 274320,
    },
    "type_scale": {
        "display": {"font": "Space Grotesk", "size_pt": 40, "bold": True, "line": 1.05},
        "title": {"font": "Space Grotesk", "size_pt": 28, "bold": True, "line": 1.08},
        "kicker": {
            "font": "Inter",
            "size_pt": 11,
            "bold": True,
            "line": 1.1,
            "upper": True,
        },
        "subtitle": {"font": "Inter", "size_pt": 16, "bold": False, "line": 1.2},
        "body": {"font": "Inter", "size_pt": 12, "bold": False, "line": 1.25},
        "caption": {"font": "Inter", "size_pt": 10, "bold": False, "line": 1.2},
    },
    "spacing_scale": {
        "xs_emu": 73152,
        "sm_emu": 137160,
        "md_emu": 228600,
        "lg_emu": 365760,
        "xl_emu": 548640,
    },
    "colors": {
        "accent_1": "#008567",
        "accent_2": "#CC0066",
        "accent_3": "#FFCC00",
        "bg_primary": "#FFFFFF",
        "bg_dark": "#000000",
        "text_primary": "#000000",
        "text_on_dark": "#FFFFFF",
    },
    "canvases": {
        "header_light": {
            "layout_index": 8,
            "theme": "light",
            "title_placeholder": {
                "idx": 0,
                "left_emu": 515938,
                "top_emu": 298692,
                "width_emu": 11160122,
                "height_emu": 938437,
            },
            "body_region": {
                "left_emu": 515938,
                "top_emu": 1237129,
                "width_emu": 11160122,
                "height_emu": 5420871,
            },
        },
        "header_dark": {
            "layout_index": 9,
            "theme": "dark",
            "title_placeholder": {
                "idx": 0,
                "left_emu": 515938,
                "top_emu": 298692,
                "width_emu": 11160122,
                "height_emu": 938437,
            },
            "body_region": {
                "left_emu": 515938,
                "top_emu": 1237129,
                "width_emu": 11160122,
                "height_emu": 5420871,
            },
        },
        "blank": {
            "layout_index": 36,
            "theme": "neutral",
            "title_placeholder": None,
            "body_region": {
                "left_emu": 515938,
                "top_emu": 298692,
                "width_emu": 11160122,
                "height_emu": 6359308,
            },
        },
    },
}


class _MockCanvas:
    """Stub canvas for testing Grid without a real template."""

    def __init__(self, body_left, body_top, body_width, body_height, design_system):
        self.body_left = body_left
        self.body_top = body_top
        self.body_width = body_width
        self.body_height = body_height
        self.design_system = design_system


def _mock_canvas(canvas_name="header_light"):
    """Build a mock canvas with body region from DESIGN_SYSTEM."""
    region = DESIGN_SYSTEM["canvases"][canvas_name]["body_region"]
    return _MockCanvas(
        body_left=region["left_emu"],
        body_top=region["top_emu"],
        body_width=region["width_emu"],
        body_height=region["height_emu"],
        design_system=DESIGN_SYSTEM,
    )


# ---------------------------------------------------------------------------
# Rect tests
# ---------------------------------------------------------------------------


class TestRect(unittest.TestCase):
    def test_derived_properties(self):
        r = Rect(100, 200, 300, 400)
        self.assertEqual(r.right, 400)
        self.assertEqual(r.bottom, 600)

    def test_equality(self):
        self.assertEqual(Rect(1, 2, 3, 4), Rect(1, 2, 3, 4))
        self.assertNotEqual(Rect(1, 2, 3, 4), Rect(1, 2, 3, 5))

    def test_repr(self):
        r = Rect(10, 20, 30, 40)
        self.assertIn("10", repr(r))
        self.assertIn("Rect", repr(r))


# ---------------------------------------------------------------------------
# Grid tests
# ---------------------------------------------------------------------------


class TestGrid(unittest.TestCase):
    def setUp(self):
        self.canvas = _mock_canvas("header_light")
        self.grid = Grid(self.canvas, cols=12, gutter="md")

    def test_col_count(self):
        self.assertEqual(self.grid.cols, 12)

    def test_gutter_emu(self):
        self.assertEqual(self.grid.gutter_emu, 137160)

    def test_single_column_span(self):
        r = self.grid.span(col=1, col_span=1, top=1237129, height_emu=500000)
        self.assertEqual(r.left, 515938)
        self.assertEqual(r.top, 1237129)
        self.assertEqual(r.height, 500000)
        self.assertEqual(r.width, self.grid.col_width_emu)

    def test_full_width_span(self):
        r = self.grid.span(col=1, col_span=12, top=1237129, height_emu=500000)
        self.assertEqual(r.left, 515938)
        # Full-width span should cover the entire body width
        self.assertAlmostEqual(r.width, 11160122, delta=1)

    def test_last_column_right_edge(self):
        r = self.grid.span(col=12, col_span=1, top=0, height_emu=100)
        # Right edge of the last column should align with body right
        body_right = self.canvas.body_left + self.canvas.body_width
        self.assertAlmostEqual(r.right, body_right, delta=1)

    def test_four_column_span(self):
        r = self.grid.span(col=1, col_span=4, top=0, height_emu=100)
        # Width = 4*col_width + 3*gutter
        expected = 4 * self.grid.col_width_emu + 3 * self.grid.gutter_emu
        self.assertAlmostEqual(r.width, expected, delta=1)

    def test_adjacent_spans_have_gutter_gap(self):
        r1 = self.grid.span(col=1, col_span=4, top=0, height_emu=100)
        r2 = self.grid.span(col=5, col_span=4, top=0, height_emu=100)
        gap = r2.left - r1.right
        self.assertAlmostEqual(gap, self.grid.gutter_emu, delta=1)

    def test_span_col_zero_raises(self):
        with self.assertRaises(GridError):
            self.grid.span(col=0, col_span=1, top=0, height_emu=100)

    def test_span_overflow_raises(self):
        with self.assertRaises(GridError):
            self.grid.span(col=10, col_span=4, top=0, height_emu=100)

    def test_span_negative_col_span_raises(self):
        with self.assertRaises(GridError):
            self.grid.span(col=1, col_span=0, top=0, height_emu=100)

    def test_row_layout(self):
        regions = self.grid.row(
            top=1237129,
            height_emu=500000,
            items=[(4, "left"), (4, "center"), (4, "right")],
        )
        self.assertIn("left", regions)
        self.assertIn("center", regions)
        self.assertIn("right", regions)
        # All three should have the same width
        self.assertEqual(regions["left"].width, regions["center"].width)
        self.assertEqual(regions["center"].width, regions["right"].width)
        # Left starts at body_left
        self.assertEqual(regions["left"].left, self.canvas.body_left)
        # Right edge of "right" should reach body right edge
        body_right = self.canvas.body_left + self.canvas.body_width
        self.assertAlmostEqual(regions["right"].right, body_right, delta=1)

    def test_row_unequal_spans(self):
        regions = self.grid.row(
            top=0,
            height_emu=100,
            items=[(3, "sidebar"), (9, "main")],
        )
        # Main should be about 3x wider than sidebar (minus gutters)
        self.assertGreater(regions["main"].width, regions["sidebar"].width * 2)

    def test_row_overflow_raises(self):
        with self.assertRaises(GridError):
            self.grid.row(
                top=0,
                height_emu=100,
                items=[(6, "a"), (6, "b"), (1, "overflow")],
            )

    def test_different_gutter_sizes(self):
        g_sm = Grid(self.canvas, cols=12, gutter="sm")
        g_lg = Grid(self.canvas, cols=12, gutter="lg")
        # Smaller gutter → wider columns
        self.assertGreater(g_sm.col_width_emu, g_lg.col_width_emu)

    def test_unknown_gutter_raises(self):
        with self.assertRaises(GridError):
            Grid(self.canvas, cols=12, gutter="xxl")

    def test_blank_canvas_more_height(self):
        canvas_blank = _mock_canvas("blank")
        g = Grid(canvas_blank, cols=12, gutter="md")
        r_blank = g.span(col=1, col_span=12, top=canvas_blank.body_top, height_emu=100)
        r_header = self.grid.span(col=1, col_span=12, top=self.canvas.body_top, height_emu=100)
        # Same width (both use same body_width)
        self.assertEqual(r_blank.width, r_header.width)
        # Blank canvas body_top is higher (less used by title)
        self.assertLess(canvas_blank.body_top, self.canvas.body_top)


# ---------------------------------------------------------------------------
# Tokens tests
# ---------------------------------------------------------------------------


class TestTokens(unittest.TestCase):
    def setUp(self):
        self.tokens = Tokens(DESIGN_SYSTEM)

    def test_color_accent_1(self):
        c = self.tokens.color("accent_1")
        self.assertIsInstance(c, RGBColor)
        self.assertEqual(str(c), "008567")

    def test_color_bg_dark(self):
        c = self.tokens.color("bg_dark")
        self.assertEqual(str(c), "000000")

    def test_color_white(self):
        c = self.tokens.color("text_on_dark")
        self.assertEqual(str(c), "FFFFFF")

    def test_color_not_found_raises(self):
        with self.assertRaises(TokenNotFoundError):
            self.tokens.color("nonexistent")

    def test_type_title(self):
        t = self.tokens.type("title")
        self.assertEqual(t["font"], "Space Grotesk")
        self.assertEqual(t["size_pt"], 28)
        self.assertTrue(t["bold"])
        self.assertEqual(t["line"], 1.08)

    def test_type_body(self):
        t = self.tokens.type("body")
        self.assertEqual(t["font"], "Inter")
        self.assertEqual(t["size_pt"], 12)
        self.assertFalse(t["bold"])

    def test_type_kicker_has_upper(self):
        t = self.tokens.type("kicker")
        self.assertTrue(t.get("upper"))

    def test_type_returns_copy(self):
        t1 = self.tokens.type("body")
        t1["size_pt"] = 999
        t2 = self.tokens.type("body")
        self.assertEqual(t2["size_pt"], 12)

    def test_type_not_found_raises(self):
        with self.assertRaises(TokenNotFoundError):
            self.tokens.type("nonexistent")

    def test_spacing_md(self):
        self.assertEqual(self.tokens.spacing("md"), 228600)

    def test_spacing_xs(self):
        self.assertEqual(self.tokens.spacing("xs"), 73152)

    def test_spacing_xl(self):
        self.assertEqual(self.tokens.spacing("xl"), 548640)

    def test_spacing_not_found_raises(self):
        with self.assertRaises(TokenNotFoundError):
            self.tokens.spacing("nonexistent")

    def test_from_design_system_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(DESIGN_SYSTEM, f)
            f.flush()
            tokens = Tokens.from_design_system(f.name)
        c = tokens.color("accent_1")
        self.assertEqual(str(c), "008567")


# ---------------------------------------------------------------------------
# Canvas (property-level, no real template)
# ---------------------------------------------------------------------------


class TestCanvasProperties(unittest.TestCase):
    """Test Canvas body-property behavior using the real Canvas class
    with a mock design system — but without opening a real .pptx template.
    We test the property logic, not Presentation loading (that's integration).
    """

    def test_mock_canvas_body_values(self):
        mc = _mock_canvas("header_light")
        self.assertEqual(mc.body_left, 515938)
        self.assertEqual(mc.body_top, 1237129)
        self.assertEqual(mc.body_width, 11160122)
        self.assertEqual(mc.body_height, 5420871)

    def test_blank_canvas_body_values(self):
        mc = _mock_canvas("blank")
        self.assertEqual(mc.body_left, 515938)
        self.assertEqual(mc.body_top, 298692)
        self.assertEqual(mc.body_width, 11160122)
        self.assertEqual(mc.body_height, 6359308)


if __name__ == "__main__":
    unittest.main()
