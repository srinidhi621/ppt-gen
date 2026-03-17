"""Tests for Aspose.Slides PPTX-to-PDF/PNG export module.

Unit tests (mocked) run unconditionally.
Integration tests that hit the real library are gated behind
``ASPOSE_INTEGRATION=1`` and the library being importable.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.review.aspose_export import (
    ASPOSE_AVAILABLE,
    AsposeExportError,
    convert_pptx_to_pdf,
    convert_pptx_to_pngs,
    export_slides_to_images_aspose,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

SAMPLE_PPTX_FILES = sorted(REPO_ROOT.glob("inputs/*.pptx"))

RUN_INTEGRATION = (
    os.environ.get("ASPOSE_INTEGRATION", "").strip() == "1" and ASPOSE_AVAILABLE
)


# ---------------------------------------------------------------------------
# Unit tests — always runnable (mock the library)
# ---------------------------------------------------------------------------
class TestGuardRails(unittest.TestCase):
    """Validate argument checks and error paths that don't need the library."""

    def test_missing_pptx_raises(self) -> None:
        if not ASPOSE_AVAILABLE:
            self.skipTest("aspose-slides not installed")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(AsposeExportError) as ctx:
                convert_pptx_to_pdf(
                    Path(tmp) / "nonexistent.pptx",
                    Path(tmp) / "out.pdf",
                )
            self.assertIn("not found", str(ctx.exception))

    def test_missing_pptx_raises_png(self) -> None:
        if not ASPOSE_AVAILABLE:
            self.skipTest("aspose-slides not installed")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(AsposeExportError):
                convert_pptx_to_pngs(
                    Path(tmp) / "nonexistent.pptx",
                    Path(tmp),
                )

    def test_invalid_scale_raises(self) -> None:
        if not ASPOSE_AVAILABLE:
            self.skipTest("aspose-slides not installed")
        with tempfile.TemporaryDirectory() as tmp:
            dummy = Path(tmp) / "dummy.pptx"
            dummy.write_bytes(b"PK")
            with self.assertRaises(AsposeExportError) as ctx:
                convert_pptx_to_pngs(dummy, Path(tmp), scale=-1)
            self.assertIn("Invalid scale", str(ctx.exception))


class TestImportGuard(unittest.TestCase):
    """Verify graceful behaviour when aspose-slides is not installed."""

    def test_require_aspose_raises_when_missing(self) -> None:
        import src.review.aspose_export as mod

        original = mod.ASPOSE_AVAILABLE
        try:
            mod.ASPOSE_AVAILABLE = False
            with self.assertRaises(AsposeExportError) as ctx:
                convert_pptx_to_pdf(Path("x.pptx"), Path("out.pdf"))
            self.assertIn("not installed", str(ctx.exception))
        finally:
            mod.ASPOSE_AVAILABLE = original


class TestExportAliasSignature(unittest.TestCase):
    """Ensure the drop-in alias delegates correctly."""

    @mock.patch("src.review.aspose_export.convert_pptx_to_pngs")
    def test_alias_delegates(self, mock_convert: mock.MagicMock) -> None:
        mock_convert.return_value = [Path("slide_001.png")]
        result = export_slides_to_images_aspose(
            Path("deck.pptx"), Path("out"), scale=1.5
        )
        mock_convert.assert_called_once_with(
            Path("deck.pptx"), Path("out"), scale=1.5, width=None, height=None
        )
        self.assertEqual(result, [Path("slide_001.png")])


# ---------------------------------------------------------------------------
# Integration tests — real Aspose.Slides on real PPTX files
# ---------------------------------------------------------------------------
@unittest.skipUnless(RUN_INTEGRATION, "Set ASPOSE_INTEGRATION=1 and install aspose-slides")
class TestPdfConversionIntegration(unittest.TestCase):
    """Convert real PPTX files in inputs/ to PDF."""

    def test_convert_each_pptx_to_pdf(self) -> None:
        self.assertTrue(
            len(SAMPLE_PPTX_FILES) > 0,
            "No .pptx files found under inputs/",
        )
        for pptx in SAMPLE_PPTX_FILES:
            with self.subTest(pptx=pptx.name):
                with tempfile.TemporaryDirectory() as tmp:
                    pdf_out = Path(tmp) / f"{pptx.stem}.pdf"
                    result = convert_pptx_to_pdf(pptx, pdf_out)
                    self.assertTrue(result.exists(), f"PDF not created for {pptx.name}")
                    self.assertGreater(
                        result.stat().st_size, 0, "PDF is empty"
                    )


@unittest.skipUnless(RUN_INTEGRATION, "Set ASPOSE_INTEGRATION=1 and install aspose-slides")
class TestPngConversionIntegration(unittest.TestCase):
    """Convert real PPTX files in inputs/ to slide PNGs."""

    def test_convert_each_pptx_to_pngs(self) -> None:
        self.assertTrue(
            len(SAMPLE_PPTX_FILES) > 0,
            "No .pptx files found under inputs/",
        )
        for pptx in SAMPLE_PPTX_FILES:
            with self.subTest(pptx=pptx.name):
                with tempfile.TemporaryDirectory() as tmp:
                    out_dir = Path(tmp) / "slides"
                    images = convert_pptx_to_pngs(pptx, out_dir, scale=1.0)
                    self.assertGreater(len(images), 0, "No slides exported")
                    for img in images:
                        self.assertTrue(img.exists())
                        self.assertTrue(img.name.startswith("slide_"))
                        self.assertTrue(img.suffix == ".png")
                        self.assertGreater(img.stat().st_size, 0)

    def test_custom_dimensions(self) -> None:
        if not SAMPLE_PPTX_FILES:
            self.skipTest("No sample PPTX")
        pptx = SAMPLE_PPTX_FILES[0]
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "slides"
            images = convert_pptx_to_pngs(
                pptx, out_dir, width=1920, height=1080
            )
            self.assertGreater(len(images), 0)


@unittest.skipUnless(RUN_INTEGRATION, "Set ASPOSE_INTEGRATION=1 and install aspose-slides")
class TestDropInReplacementIntegration(unittest.TestCase):
    """Verify the drop-in alias works end-to-end."""

    def test_export_slides_to_images_aspose(self) -> None:
        if not SAMPLE_PPTX_FILES:
            self.skipTest("No sample PPTX")
        pptx = SAMPLE_PPTX_FILES[0]
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "review_images"
            images = export_slides_to_images_aspose(pptx, out_dir)
            self.assertGreater(len(images), 0)
            for i, img in enumerate(images, start=1):
                self.assertEqual(img.name, f"slide_{i:03d}.png")


if __name__ == "__main__":
    unittest.main()
