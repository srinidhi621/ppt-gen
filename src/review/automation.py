"""Automated slide image export and ingestion for review loops."""

from __future__ import annotations

import re
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple


class ReviewAutomationError(RuntimeError):
    """Raised when automated review artifact generation fails."""


def export_slides_to_images(
    pptx_path: Path,
    output_dir: Path,
    *,
    timeout_seconds: int = 300,
    dpi: int = 220,
) -> List[Path]:
    """Export all slides from a PPTX to PNGs using LibreOffice + pdftoppm."""
    if not pptx_path.exists():
        raise ReviewAutomationError(f"Missing PPTX for export: {pptx_path}")
    if dpi < 72:
        raise ReviewAutomationError(f"Invalid export DPI ({dpi}); expected >= 72.")

    soffice = shutil.which("soffice")
    if not soffice:
        raise ReviewAutomationError(
            "Missing `soffice` binary. Install LibreOffice and ensure `soffice` is on PATH."
        )
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise ReviewAutomationError(
            "Missing `pdftoppm` binary. Install poppler and ensure `pdftoppm` is on PATH."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    _clear_previous_outputs(output_dir)

    with tempfile.TemporaryDirectory(prefix="slide_export_", dir=str(output_dir)) as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        _convert_pptx_to_pdf(soffice, pptx_path, temp_dir, timeout_seconds)
        pdf_path = _resolve_exported_pdf(temp_dir, pptx_path)
        _convert_pdf_to_pngs(pdftoppm, pdf_path, temp_dir, dpi, timeout_seconds)

        raw_pngs = sorted(temp_dir.glob("slide-*.png"), key=_natural_sort_key)
        if not raw_pngs:
            raise ReviewAutomationError(
                "Slide export succeeded but produced no PNGs. Verify LibreOffice conversion output."
            )
        for idx, image in enumerate(raw_pngs, start=1):
            target = output_dir / f"raw_slide_{idx:03d}.png"
            if target.exists():
                target.unlink()
            shutil.move(str(image), str(target))

    return collect_review_images(output_dir)


def export_slides_to_images_powerpoint(
    pptx_path: Path,
    output_dir: Path,
    *,
    timeout_seconds: int = 300,
    dpi: int = 220,
) -> List[Path]:
    """Backward-compatible alias for the current default image exporter."""
    return export_slides_to_images(
        pptx_path,
        output_dir,
        timeout_seconds=timeout_seconds,
        dpi=dpi,
    )


def collect_review_images(
    output_dir: Path,
    *,
    expected_count: int | None = None,
    min_width: int = 1600,
) -> List[Path]:
    """Collect and normalize review images in deterministic slide order."""
    if not output_dir.exists():
        raise ReviewAutomationError(f"Review image directory not found: {output_dir}")

    raw_images = [
        p
        for p in output_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ]
    if not raw_images:
        raise ReviewAutomationError(f"No review images found in: {output_dir}")

    raw_images.sort(key=_natural_sort_key)

    # Normalize to deterministic names: slide_001.png, slide_002.png, ...
    temp_paths: List[Path] = []
    for idx, path in enumerate(raw_images, start=1):
        tmp = output_dir / f".tmp_slide_{idx:03d}{path.suffix.lower()}"
        path.rename(tmp)
        temp_paths.append(tmp)

    normalized_paths: List[Path] = []
    for idx, tmp in enumerate(temp_paths, start=1):
        target = output_dir / f"slide_{idx:03d}.png"
        if target.exists():
            target.unlink()
        tmp.rename(target)
        normalized_paths.append(target)

    if expected_count is not None and len(normalized_paths) != expected_count:
        raise ReviewAutomationError(
            f"Review image count mismatch: expected {expected_count}, got {len(normalized_paths)}"
        )

    # Basic quality gate: minimum width check.
    for image in normalized_paths:
        width, _ = get_image_dimensions(image)
        if width > 0 and width < min_width:
            raise ReviewAutomationError(
                f"Review image too small ({width}px): {image}. Minimum required: {min_width}px"
            )

    return normalized_paths


def get_image_dimensions(image_path: Path) -> Tuple[int, int]:
    """Get image width/height in pixels (PNG parser + macOS `sips` fallback)."""
    if image_path.suffix.lower() == ".png":
        width, height = _read_png_dimensions(image_path)
        if width > 0 and height > 0:
            return (width, height)

    sips = shutil.which("sips")
    if not sips:
        return (0, 0)
    result = subprocess.run(
        [sips, "-g", "pixelWidth", "-g", "pixelHeight", str(image_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return (0, 0)
    width = 0
    height = 0
    for line in result.stdout.splitlines():
        if "pixelWidth:" in line:
            try:
                width = int(line.split(":", 1)[1].strip())
            except ValueError:
                width = 0
        elif "pixelHeight:" in line:
            try:
                height = int(line.split(":", 1)[1].strip())
            except ValueError:
                height = 0
    return (width, height)


def _natural_sort_key(path: Path) -> Tuple[int, str]:
    match = re.search(r"(\d+)", path.stem)
    num = int(match.group(1)) if match else 10**9
    return (num, path.name.lower())


def _clear_previous_outputs(output_dir: Path) -> None:
    for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.pdf"):
        for path in output_dir.glob(pattern):
            if path.is_file():
                path.unlink()


def _convert_pptx_to_pdf(
    soffice: str,
    pptx_path: Path,
    output_dir: Path,
    timeout_seconds: int,
) -> None:
    result = subprocess.run(
        [
            soffice,
            "--headless",
            "--nologo",
            "--nodefault",
            "--nofirststartwizard",
            "--norestore",
            "--nolockcheck",
            "--invisible",
            "--convert-to",
            "pdf:impress_pdf_Export",
            "--outdir",
            str(output_dir),
            str(pptx_path),
        ],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "LibreOffice conversion failed").strip()
        raise ReviewAutomationError(f"PPTX->PDF conversion failed: {detail}")


def _resolve_exported_pdf(output_dir: Path, pptx_path: Path) -> Path:
    expected = output_dir / f"{pptx_path.stem}.pdf"
    if expected.exists():
        return expected
    candidates = sorted(output_dir.glob("*.pdf"), key=lambda p: p.name.lower())
    if not candidates:
        raise ReviewAutomationError("PPTX->PDF conversion reported success but no PDF was produced.")
    if len(candidates) == 1:
        return candidates[0]
    stem = pptx_path.stem.lower()
    for candidate in candidates:
        if stem in candidate.stem.lower():
            return candidate
    return candidates[0]


def _convert_pdf_to_pngs(
    pdftoppm: str,
    pdf_path: Path,
    output_dir: Path,
    dpi: int,
    timeout_seconds: int,
) -> None:
    prefix = output_dir / "slide"
    result = subprocess.run(
        [
            pdftoppm,
            "-png",
            "-r",
            str(dpi),
            str(pdf_path),
            str(prefix),
        ],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "pdftoppm conversion failed").strip()
        raise ReviewAutomationError(f"PDF->PNG conversion failed: {detail}")


def _read_png_dimensions(image_path: Path) -> Tuple[int, int]:
    try:
        header = image_path.read_bytes()[:24]
    except OSError:
        return (0, 0)
    if len(header) < 24:
        return (0, 0)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        return (0, 0)
    try:
        width, height = struct.unpack(">II", header[16:24])
    except struct.error:
        return (0, 0)
    return (int(width), int(height))
