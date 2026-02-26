"""Asset catalog loading and cue matching utilities."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence


STOP_WORDS = {
    "and",
    "the",
    "to",
    "of",
    "in",
    "with",
    "for",
    "a",
    "an",
}


def load_asset_catalog(catalog_path: Path) -> Dict[str, Any]:
    if not catalog_path.exists():
        return {"assets": []}
    with catalog_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_asset_catalog(assets_dir: Path) -> Dict[str, Any]:
    catalog_path = assets_dir / "catalog" / "asset_catalog.json"
    payload = build_asset_catalog(assets_dir)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def match_asset(
    hint_text: str | None,
    assets: Sequence[Dict[str, Any]],
    *,
    allowed_types: Sequence[str],
    min_score: int = 2,
) -> Dict[str, Any] | None:
    """Match an asset using deterministic token-overlap scoring."""
    tokens = _tokenize(hint_text or "")
    if not tokens:
        return None

    best_asset: Dict[str, Any] | None = None
    best_score = 0
    allowed = set(allowed_types)

    for asset in assets:
        asset_type = str(asset.get("asset_type", ""))
        if allowed and asset_type not in allowed:
            continue

        asset_tokens = set()
        asset_tokens.update(_tokenize(str(asset.get("asset_id", ""))))
        for tag in asset.get("tags", []):
            asset_tokens.update(_tokenize(str(tag)))
        for synonym in asset.get("synonyms", []):
            asset_tokens.update(_tokenize(str(synonym)))

        score = len(tokens & asset_tokens)
        if score > best_score:
            best_score = score
            best_asset = asset

    if best_asset is None or best_score < min_score:
        return None
    return best_asset


def build_asset_catalog(assets_dir: Path) -> Dict[str, Any]:
    icons_json = assets_dir / "icons" / "icons.json"
    external_registry = assets_dir / "external_assets" / "registry.manifest.json"
    assets: List[Dict[str, Any]] = []
    assets.extend(_icon_entries(icons_json))
    assets.extend(_external_icon_entries(external_registry))
    assets.extend(_image_entries(assets_dir))
    return {
        "summary": {
            "version": "1.0",
            "assets_count": len(assets),
            "icon_count": sum(1 for a in assets if a["asset_type"] == "icon"),
            "image_count": sum(1 for a in assets if a["asset_type"] == "image"),
            "low_quality_count": sum(1 for a in assets if a.get("quality") == "low"),
        },
        "assets": assets,
    }


def _tokenize(text: str) -> set[str]:
    raw_tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {tok for tok in raw_tokens if len(tok) > 1 and tok not in STOP_WORDS}


def _icon_entries(icons_json_path: Path) -> List[Dict[str, Any]]:
    if not icons_json_path.exists():
        return []
    payload = json.loads(icons_json_path.read_text(encoding="utf-8"))
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


def _external_icon_entries(registry_manifest_path: Path) -> List[Dict[str, Any]]:
    if not registry_manifest_path.exists():
        return []
    payload = json.loads(registry_manifest_path.read_text(encoding="utf-8"))
    out: List[Dict[str, Any]] = []
    for icon in payload.get("icons", []):
        pack = str(icon.get("pack", "")).strip()
        svg_path = str(icon.get("svg_path", "")).strip()
        icon_id = str(icon.get("id", "")).strip()
        if not pack or not svg_path or not icon_id:
            continue
        tags = [str(t).lower() for t in icon.get("tags", [])]
        categories = [str(c).lower() for c in icon.get("categories", [])]
        aliases = [str(a).lower() for a in icon.get("aliases", [])]
        out.append(
            {
                "asset_type": "icon",
                "asset_id": icon_id,
                "source_path": f"external_assets/{pack}/{svg_path}",
                "tags": sorted(set(tags + categories)),
                "synonyms": sorted(set(aliases)),
                "quality": "high",
            }
        )
    return out


def _image_entries(assets_dir: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    roots = [
        assets_dir / "Icons and Dimensional Keywords",
        assets_dir / "Ascendion Logos",
    ]
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            rel = str(path.relative_to(assets_dir))
            parent_tokens = _tokenize(path.parent.name)
            file_tokens = _tokenize(path.stem.replace("_", " ").replace("-", " "))
            tags = sorted(parent_tokens | file_tokens)
            out.append(
                {
                    "asset_type": "image",
                    "asset_id": rel,
                    "source_path": rel,
                    "tags": tags,
                    "synonyms": [],
                    "quality": "medium" if tags else "low",
                }
            )
    return out
