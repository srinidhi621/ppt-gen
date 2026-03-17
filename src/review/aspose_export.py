"""PPTX-to-PDF and PPTX-to-PNG export using Aspose.Slides.

Higher-fidelity alternative to the LibreOffice + pdftoppm pipeline.
Evaluation mode leaves an Aspose watermark on outputs, which is acceptable
for review-stage artifacts — final deliverables remain the PPTX files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    import aspose.slides as asp_slides
    import aspose.pydrawing as drawing

    ASPOSE_AVAILABLE = True
except ImportError:
    ASPOSE_AVAILABLE = False


class AsposeExportError(RuntimeError):
    """Raised when Aspose.Slides export fails."""


def _require_aspose() -> None:
    if not ASPOSE_AVAILABLE:
        raise AsposeExportError(
            "aspose-slides is not installed. "
            "Install with: pip install aspose-slides"
        )


def convert_pptx_to_pdf(
    pptx_path: Path,
    output_path: Path,
    *,
    jpeg_quality: int = 95,
    image_dpi: int = 300,
    include_hidden_slides: bool = False,
) -> Path:
    """Convert a PPTX file to PDF using Aspose.Slides.

    Returns the path to the generated PDF.
    """
    _require_aspose()
    pptx_path = Path(pptx_path)
    output_path = Path(output_path)

    if not pptx_path.exists():
        raise AsposeExportError(f"PPTX file not found: {pptx_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with asp_slides.Presentation(str(pptx_path)) as pres:
            pdf_opts = asp_slides.export.PdfOptions()
            pdf_opts.jpeg_quality = jpeg_quality
            pdf_opts.sufficient_resolution = image_dpi
            pdf_opts.save_metafiles_as_png = True
            pdf_opts.text_compression = asp_slides.export.PdfTextCompression.FLATE
            pdf_opts.show_hidden_slides = include_hidden_slides
            pres.save(str(output_path), asp_slides.export.SaveFormat.PDF, pdf_opts)
    except Exception as exc:
        if isinstance(exc, AsposeExportError):
            raise
        raise AsposeExportError(f"PPTX->PDF conversion failed: {exc}") from exc

    if not output_path.exists():
        raise AsposeExportError(
            "Aspose.Slides reported success but no PDF was produced."
        )
    logger.info("Converted %s -> %s", pptx_path.name, output_path.name)
    return output_path


def convert_pptx_to_pngs(
    pptx_path: Path,
    output_dir: Path,
    *,
    scale: float = 2.0,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> List[Path]:
    """Export each slide of a PPTX to a PNG image using Aspose.Slides.

    If *width* and *height* are given they override *scale*.
    Output files are named ``slide_001.png``, ``slide_002.png``, etc.

    Returns a sorted list of PNG paths.
    """
    _require_aspose()
    pptx_path = Path(pptx_path)
    output_dir = Path(output_dir)

    if not pptx_path.exists():
        raise AsposeExportError(f"PPTX file not found: {pptx_path}")
    if scale <= 0:
        raise AsposeExportError(f"Invalid scale ({scale}); must be > 0.")

    output_dir.mkdir(parents=True, exist_ok=True)

    png_paths: List[Path] = []
    try:
        with asp_slides.Presentation(str(pptx_path)) as pres:
            for idx, slide in enumerate(pres.slides, start=1):
                if width and height:
                    size = drawing.Size(width, height)
                    img = slide.get_image(size)
                else:
                    img = slide.get_image(scale, scale)

                dest = output_dir / f"slide_{idx:03d}.png"
                with img:
                    img.save(str(dest), asp_slides.ImageFormat.PNG)
                png_paths.append(dest)
    except Exception as exc:
        if isinstance(exc, AsposeExportError):
            raise
        raise AsposeExportError(
            f"PPTX->PNG slide export failed: {exc}"
        ) from exc

    if not png_paths:
        raise AsposeExportError("Presentation contains no slides to export.")

    logger.info(
        "Exported %d slide images from %s to %s",
        len(png_paths),
        pptx_path.name,
        output_dir,
    )
    return png_paths


def export_slides_to_images_aspose(
    pptx_path: Path,
    output_dir: Path,
    *,
    scale: float = 2.0,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> List[Path]:
    """Drop-in replacement for *export_slides_to_images* using Aspose.Slides.

    Produces slide images directly (PPTX -> PNG) without an intermediate PDF,
    giving maximum fidelity for the visual review stage.
    """
    return convert_pptx_to_pngs(
        pptx_path,
        output_dir,
        scale=scale,
        width=width,
        height=height,
    )
