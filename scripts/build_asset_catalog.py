"""Build a unified asset catalog for cue-to-asset matching.

Usage:
    python scripts/build_asset_catalog.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ICONS_JSON = ASSETS / "icons" / "icons.json"
OUT_PATH = ASSETS / "catalog" / "asset_catalog.json"

COLOR_STOP = {"pink", "purple", "teal", "white", "yellow", "black", "rgb", "transparent"}
GENERIC_STOP = {"pt", "artboard", "image", "logo", "logos", "and", "the", "to", "with"}


def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [tok for tok in tokens if len(tok) > 1 and tok not in COLOR_STOP and tok not in GENERIC_STOP]


def _icon_entries() -> List[Dict[str, Any]]:
    payload = json.loads(ICONS_JSON.read_text(encoding="utf-8"))
    out: List[Dict[str, Any]] = []
    for icon in payload.get("icons", []):
        tags = [str(t).lower() for t in icon.get("tags", [])]
        synonyms = [str(s).lower() for s in icon.get("synonyms", [])]
        out.append(
            {
                "asset_type": "icon",
                "asset_id": icon["icon_id"],
                "source_path": f"icons/png/{icon['filename']}",
                "tags": sorted(set(tags)),
                "synonyms": sorted(set(synonyms)),
                "quality": "high" if tags or synonyms else "low",
            }
        )
    return out


def _image_entries() -> List[Dict[str, Any]]:
    roots = [
        ASSETS / "Icons and Dimensional Keywords",
        ASSETS / "Ascendion Logos",
    ]
    out: List[Dict[str, Any]] = []

    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            rel_assets = str(path.relative_to(ASSETS))
            parent_tokens = _tokenize(path.parent.name)
            file_tokens = _tokenize(path.stem.replace("_", " ").replace("-", " "))
            tags = sorted(set(parent_tokens + file_tokens))
            out.append(
                {
                    "asset_type": "image",
                    "asset_id": rel_assets,
                    "source_path": rel_assets,
                    "tags": tags,
                    "synonyms": [],
                    "quality": "medium" if tags else "low",
                }
            )
    return out


def main() -> int:
    assets = _icon_entries() + _image_entries()
    summary = {
        "version": "1.0",
        "generated_by": "scripts/build_asset_catalog.py",
        "assets_count": len(assets),
        "icon_count": sum(1 for a in assets if a["asset_type"] == "icon"),
        "image_count": sum(1 for a in assets if a["asset_type"] == "image"),
        "low_quality_count": sum(1 for a in assets if a.get("quality") == "low"),
    }
    payload = {"summary": summary, "assets": assets}

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote asset catalog: {OUT_PATH}")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
