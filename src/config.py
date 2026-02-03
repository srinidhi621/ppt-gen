"""Runtime configuration loader."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .models.config import Config


def _require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")


def load_config(project_root: Optional[Path] = None) -> Config:
    """Load configuration with canonical defaults and validate paths."""
    root = project_root or Path(__file__).resolve().parents[1]
    assets_dir = root / "assets"
    template_path = assets_dir / "template" / "template.pptx"
    layout_catalog_path = assets_dir / "layout" / "layout_catalog.json"
    icons_json_path = assets_dir / "icons" / "icons.json"

    _require_file(template_path, "template_pptx")
    _require_file(layout_catalog_path, "layout_catalog")
    _require_file(icons_json_path, "icons_json")

    return Config(
        project_root=str(root),
        assets_dir=str(assets_dir),
        template_path=str(template_path),
        layout_catalog_path=str(layout_catalog_path),
        icons_json_path=str(icons_json_path),
        inputs_dir=str(root / "inputs"),
        runs_dir=str(root / "runs"),
    )
