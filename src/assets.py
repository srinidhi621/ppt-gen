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
RENDERABLE_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


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
    icon_assets = _merge_icon_assets(
        _icon_entries(icons_json), _external_icon_entries(external_registry)
    )
    assets: List[Dict[str, Any]] = []
    assets.extend(icon_assets)
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


def _merge_icon_assets(
    primary_icons: List[Dict[str, Any]], fallback_icons: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Merge icon entries by asset_id, preferring renderable image paths from primary metadata.
    """
    merged: Dict[str, Dict[str, Any]] = {}
    for icon in fallback_icons:
        merged[str(icon.get("asset_id", ""))] = icon

    for icon in primary_icons:
        asset_id = str(icon.get("asset_id", ""))
        if not asset_id:
            continue
        existing = merged.get(asset_id)
        if existing is None:
            merged[asset_id] = icon
            continue

        new_path = str(icon.get("source_path", "")).lower()
        old_path = str(existing.get("source_path", "")).lower()
        if _is_renderable_path(new_path) and not _is_renderable_path(old_path):
            merged[asset_id] = icon
            continue
        if old_path and not new_path:
            continue
        merged[asset_id] = icon

    return sorted(merged.values(), key=lambda item: str(item.get("asset_id", "")))


def load_visual_vocabulary(assets_dir: Path) -> Dict[str, Any]:
    """Load the visual vocabulary catalog."""
    vocab_path = assets_dir / "catalog" / "visual_vocabulary.json"
    if not vocab_path.exists():
        return {"concepts": {}}
    return json.loads(vocab_path.read_text(encoding="utf-8"))


def load_component_catalog(assets_dir: Path) -> Dict[str, Any]:
    """Load component metadata used to guide planner visual choices."""
    catalog_path = assets_dir / "catalog" / "component_catalog_v1.json"
    if not catalog_path.exists():
        return {"components": [], "planner_hints": {}}
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def load_planner_policy(assets_dir: Path) -> Dict[str, Any]:
    """Load planner policy constraints for visual routing/diversity."""
    policy_path = assets_dir / "catalog" / "planner_policy_v1.json"
    if not policy_path.exists():
        return {
            "asset_diversity": {
                "min_unique_visual_assets_per_10_slides": 4,
                "max_reuse_per_branded_image": 2,
                "max_adjacent_reuse_same_icon_concept": 1,
                "target_visualized_slides_ratio": 0.7,
            },
            "routing_guidance": {
                "prefer_image_layout_when_cues_present": True,
                "force_image_on_section_break": True,
                "avoid_single_layout_streak_over": 3,
            },
            "prompt_directives": [],
        }
    return json.loads(policy_path.read_text(encoding="utf-8"))


def resolve_visual_concept(concept: str, vocabulary: Dict[str, Any]) -> str | None:
    """Resolve a concept name to the preferred icon_id, falling back to alternatives."""
    concepts = vocabulary.get("concepts", {})
    entry = concepts.get(concept.lower().strip())
    if not entry:
        return None
    return entry.get("preferred") or (entry.get("alt", [None])[0])


def resolve_visual_concepts_for_text(
    text: str, vocabulary: Dict[str, Any]
) -> str | None:
    """Tokenize text and match tokens against concept names and domain keywords.

    Returns the best icon_id or None.
    """
    tokens = _tokenize(text)
    if not tokens:
        return None

    concepts = vocabulary.get("concepts", {})

    # Build reverse index: domain keyword -> concept name
    domain_to_concept: Dict[str, str] = {}
    for concept_name, entry in concepts.items():
        for domain in entry.get("domains", []):
            domain_key = domain.lower().replace("-", "").replace("_", "")
            domain_to_concept.setdefault(domain_key, concept_name)

    # Direct concept name match (best)
    for token in tokens:
        normalized = token.lower().replace("-", "").replace("_", "")
        if normalized in concepts:
            return resolve_visual_concept(normalized, vocabulary)

    # Domain keyword match
    for token in tokens:
        normalized = token.lower().replace("-", "").replace("_", "")
        matched_concept = domain_to_concept.get(normalized)
        if matched_concept:
            return resolve_visual_concept(matched_concept, vocabulary)

    return None


def load_branded_images_catalog(assets_dir: Path) -> Dict[str, Any]:
    """Load the branded image catalog."""
    catalog_path = assets_dir / "catalog" / "branded_images.json"
    if not catalog_path.exists():
        return {"images": {}}
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def resolve_branded_image(
    context_text: str, catalog: Dict[str, Any], theme: str = "light"
) -> str | None:
    """Match context text against image themes and return the best image path."""
    tokens = _tokenize(context_text)
    if not tokens:
        return None

    images = catalog.get("images", {})
    best_id = None
    best_score = 0

    for image_id, entry in images.items():
        theme_text = str(entry.get("theme", ""))
        theme_tokens = _tokenize(theme_text)
        score = len(tokens & theme_tokens)
        if score > best_score:
            best_score = score
            best_id = image_id

    if best_id is None or best_score < 1:
        return None

    entry = images[best_id]
    color_pref = entry.get("color_preference", {})
    color = color_pref.get(f"{theme}_theme", "Teal")
    paths = entry.get("paths", {})
    return paths.get(color) or next(iter(paths.values()), None)


def _is_renderable_path(source_path: str) -> bool:
    return Path(source_path).suffix.lower() in RENDERABLE_IMAGE_SUFFIXES


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
