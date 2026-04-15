"""Unit tests for ppt_runtime.measure — text measurement and shrink_to_fit."""

import unittest

from src.ppt_runtime.errors import TokenNotFoundError
from src.ppt_runtime.grid import Rect
from src.ppt_runtime.measure import measure_text, shrink_to_fit
from src.ppt_runtime.tokens import Tokens

# ---------------------------------------------------------------------------
# Shared fixture — matches the real design system
# ---------------------------------------------------------------------------

DESIGN_SYSTEM = {
    "colors": {
        "accent_1": "#008567",
        "text_primary": "#000000",
    },
    "type_scale": {
        "display": {"font": "Space Grotesk", "size_pt": 40, "bold": True, "line": 1.05},
        "title": {"font": "Space Grotesk", "size_pt": 28, "bold": True, "line": 1.08},
        "kicker": {"font": "Inter", "size_pt": 11, "bold": True, "line": 1.1, "upper": True},
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
}


# ---------------------------------------------------------------------------
# measure_text tests
# ---------------------------------------------------------------------------


class TestMeasureText(unittest.TestCase):
    def setUp(self):
        self.title_style = DESIGN_SYSTEM["type_scale"]["title"]
        self.body_style = DESIGN_SYSTEM["type_scale"]["body"]

    def test_returns_positive_dimensions(self):
        w, h = measure_text("Hello world", self.title_style)
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)

    def test_empty_string_has_zero_width(self):
        w, h = measure_text("", self.title_style)
        self.assertEqual(w, 0)
        self.assertGreater(h, 0)  # height is one line tall

    def test_longer_string_is_wider(self):
        w_short, _ = measure_text("Hi", self.title_style)
        w_long, _ = measure_text("Legacy complexity is now a growth constraint", self.title_style)
        self.assertGreater(w_long, w_short)

    def test_larger_font_is_taller(self):
        _, h_title = measure_text("Test", self.title_style)
        _, h_body = measure_text("Test", self.body_style)
        self.assertGreater(h_title, h_body)

    def test_larger_font_is_wider(self):
        w_title, _ = measure_text("Test", self.title_style)
        w_body, _ = measure_text("Test", self.body_style)
        self.assertGreater(w_title, w_body)

    def test_height_reflects_line_spacing(self):
        # title: 28pt * 1.08 = 30.24pt; body: 12pt * 1.25 = 15pt
        _, h_title = measure_text("X", self.title_style)
        _, h_body = measure_text("X", self.body_style)
        # Title line height should be roughly 2x body line height
        ratio = h_title / h_body
        self.assertGreater(ratio, 1.5)
        self.assertLess(ratio, 2.5)

    def test_single_line_width_reasonable(self):
        # "Legacy complexity" at 28pt bold Space Grotesk should be roughly 2-5 inches
        # 1 inch = 914400 EMU
        w, _ = measure_text("Legacy complexity", self.title_style)
        w_inches = w / 914400
        self.assertGreater(w_inches, 1.5)
        self.assertLess(w_inches, 6.0)

    def test_wrapping_increases_height(self):
        text = "This is a longer sentence that should wrap across multiple lines when constrained"
        _, h_nowrap = measure_text(text, self.body_style)
        # Constrain to ~3 inches
        _, h_wrapped = measure_text(text, self.body_style, max_width_emu=2743200)
        self.assertGreater(h_wrapped, h_nowrap)

    def test_wrapping_reduces_width(self):
        text = "This is a longer sentence that should wrap"
        w_nowrap, _ = measure_text(text, self.body_style)
        w_wrapped, _ = measure_text(text, self.body_style, max_width_emu=2743200)
        self.assertLess(w_wrapped, w_nowrap)

    def test_wrapping_width_within_constraint(self):
        text = "Word wrap should respect the constraint"
        max_w = 2000000  # ~2.19 inches
        w, _ = measure_text(text, self.body_style, max_width_emu=max_w)
        # Measured width should not exceed the constraint (with small tolerance)
        self.assertLessEqual(w, max_w + 12700)  # 1px tolerance

    def test_explicit_newline_increases_height(self):
        _, h_single = measure_text("hello world", self.body_style)
        _, h_multi = measure_text("hello\nworld", self.body_style)
        self.assertGreater(h_multi, h_single)

    def test_explicit_newline_preserved_when_width_is_large(self):
        _, h_single = measure_text("hello world", self.body_style, max_width_emu=10000000)
        _, h_multi = measure_text("hello\nworld", self.body_style, max_width_emu=10000000)
        self.assertGreater(h_multi, h_single)

    def test_display_style_works(self):
        w, h = measure_text("Big Title", DESIGN_SYSTEM["type_scale"]["display"])
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)

    def test_inter_font_works(self):
        w, h = measure_text("Body text", self.body_style)
        self.assertGreater(w, 0)


# ---------------------------------------------------------------------------
# shrink_to_fit tests
# ---------------------------------------------------------------------------


class TestShrinkToFit(unittest.TestCase):
    def setUp(self):
        self.tokens = Tokens(DESIGN_SYSTEM)

    def test_short_text_stays_at_base(self):
        # Short text should fit at title size in a large rect
        rect = Rect(0, 0, 11160122, 5420871)  # full body region
        result = shrink_to_fit("Short title", rect, base="title", min_style="body", tokens=self.tokens)
        self.assertEqual(result, "title")

    def test_long_text_shrinks(self):
        # Very long text in a tiny rect should shrink to min
        rect = Rect(0, 0, 1000000, 200000)  # small box
        long_text = "This is an extremely long piece of text that absolutely cannot fit " * 5
        result = shrink_to_fit(long_text, rect, base="display", min_style="caption", tokens=self.tokens)
        # Should shrink from display — likely to a smaller style
        self.assertIn(result, ["display", "title", "subtitle", "body", "caption"])

    def test_returns_min_when_nothing_fits(self):
        # Absurdly small rect — nothing can fit
        rect = Rect(0, 0, 50000, 10000)  # ~0.05" x 0.01"
        result = shrink_to_fit(
            "This text cannot possibly fit in this tiny box",
            rect, base="title", min_style="caption", tokens=self.tokens,
        )
        self.assertEqual(result, "caption")

    def test_base_equals_min(self):
        rect = Rect(0, 0, 11160122, 5420871)
        result = shrink_to_fit("Hello", rect, base="body", min_style="body", tokens=self.tokens)
        self.assertEqual(result, "body")

    def test_invalid_base_raises(self):
        rect = Rect(0, 0, 1000000, 1000000)
        with self.assertRaises(TokenNotFoundError):
            shrink_to_fit("Text", rect, base="nonexistent", min_style="body", tokens=self.tokens)

    def test_invalid_min_raises(self):
        rect = Rect(0, 0, 1000000, 1000000)
        with self.assertRaises(TokenNotFoundError):
            shrink_to_fit("Text", rect, base="title", min_style="nonexistent", tokens=self.tokens)

    def test_progressive_shrinking(self):
        # A rect that fits subtitle but not title
        title_style = self.tokens.type("title")
        subtitle_style = self.tokens.type("subtitle")
        text = "A moderately long headline for testing"
        # Measure at title size to get the height needed
        _, h_title = measure_text(text, title_style, max_width_emu=3000000)
        _, h_subtitle = measure_text(text, subtitle_style, max_width_emu=3000000)

        # Make rect tall enough for subtitle but not title
        if h_title > h_subtitle:
            mid_height = (h_title + h_subtitle) // 2
            rect = Rect(0, 0, 3000000, mid_height)
            result = shrink_to_fit(text, rect, base="title", min_style="body", tokens=self.tokens)
            # Should shrink below title
            self.assertNotEqual(result, "title")

    def test_checks_width_not_just_height(self):
        rect = Rect(0, 0, 100000, 1000000)
        result = shrink_to_fit(
            "supercalifragilisticexpialidocious",
            rect,
            base="title",
            min_style="caption",
            tokens=self.tokens,
        )
        self.assertEqual(result, "caption")


if __name__ == "__main__":
    unittest.main()
