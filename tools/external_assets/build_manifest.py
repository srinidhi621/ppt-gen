#!/usr/bin/env python3
"""Build per-pack manifests and unified external asset registry."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

PACKS = ("tabler", "lucide", "fluent", "aws")
ICONIFY_PACKS = ("tabler", "lucide", "fluent")

ICONIFY_LICENSE_TYPE_MAP = {
    "mit": "MIT",
    "isc": "ISC",
}

PACK_LICENSE_NOTES = {
    "tabler": "Metadata derived from pinned Iconify package files.",
    "lucide": "Metadata derived from pinned Iconify package files.",
    "fluent": "Metadata derived from pinned Iconify package files.",
    "aws": "Treat as AWS brand/trademark-governed assets; avoid modifying logos/marks.",
}

AWS_ARCH_PAGE = "https://aws.amazon.com/architecture/icons/"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--assets-root", required=True)
    p.add_argument("--tabler-version", required=True)
    p.add_argument("--lucide-version", required=True)
    p.add_argument("--fluent-version", required=True)
    p.add_argument("--aws-zip-label", required=True)
    p.add_argument("--tabler-url", action="append", default=[])
    p.add_argument("--lucide-url", action="append", default=[])
    p.add_argument("--fluent-url", action="append", default=[])
    p.add_argument("--aws-url", action="append", default=[])
    return p.parse_args()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def tokenize(text: str) -> list[str]:
    parts = re.split(r"[^a-z0-9]+", text.lower())
    return [p for p in parts if p]


def merge_tokens(*groups: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for group in groups:
        for item in group:
            lowered = item.strip().lower()
            if lowered and lowered not in seen:
                seen.add(lowered)
                out.append(lowered)
    return out


def normalize_iconify_license(pack: str, info: dict[str, Any], urls: list[str], version: str) -> dict[str, Any]:
    license_info = info.get("license") if isinstance(info, dict) else None
    if isinstance(license_info, dict):
        title = str(license_info.get("title") or "").strip()
        spdx = str(license_info.get("spdx") or "").strip()
        license_type = ICONIFY_LICENSE_TYPE_MAP.get(spdx.lower(), title or spdx or "UNKNOWN")
        license_source = str(license_info.get("url") or urls[1] if len(urls) > 1 else urls[0])
    else:
        license_type = "UNKNOWN"
        license_source = urls[0] if urls else ""

    if pack == "fluent" and license_type.upper() == "MIT":
        license_type = "MIT (MS)"

    return {
        "type": license_type,
        "source": license_source,
        "notes": PACK_LICENSE_NOTES[pack],
    }


def write_iconify_license_txt(pack_dir: Path, pack: str, info: dict[str, Any], version: str, urls: list[str]) -> None:
    license_info = info.get("license") if isinstance(info, dict) else {}
    author = info.get("author") if isinstance(info, dict) else ""
    lines = [
        f"Pack: {info.get('name', pack)}",
        f"Author: {author if author else 'Unknown'}",
        f"License ID: {license_info.get('spdx', license_info.get('title', 'Unknown'))}",
        f"License URL: {license_info.get('url', 'N/A')}",
        f"Pinned version: {version}",
        "Download URLs:",
    ]
    lines.extend([f"- {u}" for u in urls])
    lines.append("")
    lines.append(PACK_LICENSE_NOTES[pack])
    (pack_dir / "LICENSE.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_iconify_manifest(
    assets_root: Path,
    pack: str,
    version: str,
    urls: list[str],
) -> dict[str, Any]:
    pack_dir = assets_root / pack
    raw_dir = pack_dir / "raw" / "iconify"
    icons_json = read_json(raw_dir / "icons.json")
    info_json = read_json(raw_dir / "info.json")
    metadata_json = read_json(raw_dir / "metadata.json")

    icons_payload = icons_json.get("icons", {})
    aliases_payload = icons_json.get("aliases", {})
    categories_payload = metadata_json.get("categories", {}) if isinstance(metadata_json, dict) else {}

    tags_by_icon: dict[str, list[str]] = {}
    if isinstance(categories_payload, dict):
        for category, icon_names in categories_payload.items():
            if not isinstance(icon_names, list):
                continue
            for icon_name in icon_names:
                tags_by_icon.setdefault(icon_name, []).append(str(category))

    aliases_by_icon: dict[str, list[str]] = {}
    if isinstance(aliases_payload, dict):
        for alias_name, alias_info in aliases_payload.items():
            if not isinstance(alias_info, dict):
                continue
            parent = alias_info.get("parent")
            if isinstance(parent, str):
                aliases_by_icon.setdefault(parent, []).append(str(alias_name))

    icons: list[dict[str, Any]] = []
    for name in sorted(icons_payload.keys()):
        icon_meta = icons_payload[name]
        if not isinstance(icon_meta, dict):
            continue

        meta_keywords = icon_meta.get("keywords", [])
        meta_tags = [str(t) for t in meta_keywords] if isinstance(meta_keywords, list) else []
        category_tags = [str(c) for c in tags_by_icon.get(name, [])]
        name_tokens = tokenize(name)
        aliases = sorted(set(aliases_by_icon.get(name, [])))

        tags = merge_tokens(meta_tags, category_tags, name_tokens, ["enterprise", "icon"])
        categories = merge_tokens(category_tags)

        svg_name = name.replace(":", "_") + ".svg"
        svg_path = f"svg/{svg_name}"

        search_tokens = merge_tokens([name], tags, categories, aliases)

        icons.append(
            {
                "id": f"{pack}:{name}",
                "name": name,
                "svg_path": svg_path,
                "tags": tags,
                "categories": categories,
                "aliases": aliases,
                "search_text": " ".join(search_tokens),
            }
        )

    manifest = {
        "pack": pack,
        "pack_version": version,
        "license": normalize_iconify_license(pack, info_json, urls, version),
        "source": {
            "download_urls": urls,
            "pinned": True,
        },
        "icons": icons,
    }

    write_iconify_license_txt(pack_dir, pack, info_json, version, urls)
    write_json(pack_dir / "manifest.json", manifest)
    return manifest


def write_aws_license_txt(pack_dir: Path, aws_url: str, aws_zip_label: str) -> None:
    lines = [
        "Pack: AWS Architecture Icons",
        f"Source page: {AWS_ARCH_PAGE}",
        f"Pinned ZIP URL: {aws_url}",
        f"Pinned ZIP label: {aws_zip_label}",
        "Warning: Treat as AWS brand/trademark-governed assets; avoid modifying logos/marks.",
    ]
    (pack_dir / "LICENSE.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_aws_manifest(assets_root: Path, aws_zip_label: str, aws_url: str) -> dict[str, Any]:
    pack = "aws"
    pack_dir = assets_root / pack
    svg_root = pack_dir / "svg"
    if not svg_root.exists():
        raise FileNotFoundError(f"AWS SVG directory not found: {svg_root}")

    icons: list[dict[str, Any]] = []
    for svg_file in sorted(svg_root.rglob("*.svg")):
        rel = svg_file.relative_to(pack_dir).as_posix()
        rel_path = svg_file.relative_to(svg_root).as_posix()

        base_name = svg_file.stem
        folder_tokens = tokenize(rel_path.replace("/", " "))
        name_tokens = tokenize(base_name)

        # Use folder hierarchy as categories to preserve original AWS grouping hints.
        categories = merge_tokens(tokenize(" ".join(svg_file.parent.relative_to(svg_root).parts)))
        tags = merge_tokens(
            folder_tokens,
            name_tokens,
            ["aws", "cloud", "architecture", "provider_icon"],
        )

        search_tokens = merge_tokens([base_name], tags, categories)

        icon_id_name = rel_path[:-4].replace("/", "_")
        icons.append(
            {
                "id": f"aws:{icon_id_name}",
                "name": base_name,
                "svg_path": rel,
                "tags": tags,
                "categories": categories,
                "aliases": [],
                "search_text": " ".join(search_tokens),
            }
        )

    manifest = {
        "pack": pack,
        "pack_version": aws_zip_label,
        "license": {
            "type": "AWS brand assets",
            "source": AWS_ARCH_PAGE,
            "notes": PACK_LICENSE_NOTES[pack],
        },
        "source": {
            "download_urls": [aws_url],
            "pinned": True,
        },
        "icons": icons,
    }

    write_aws_license_txt(pack_dir, aws_url, aws_zip_label)
    write_json(pack_dir / "manifest.json", manifest)
    return manifest


def build_registry(assets_root: Path, manifests: dict[str, dict[str, Any]]) -> dict[str, Any]:
    flattened: list[dict[str, Any]] = []
    for pack in PACKS:
        pack_manifest = manifests[pack]
        for icon in pack_manifest["icons"]:
            copied = dict(icon)
            copied["pack"] = pack
            copied["pack_version"] = pack_manifest["pack_version"]
            flattened.append(copied)

    flattened.sort(key=lambda item: item["id"])

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "packs": list(PACKS),
        "icons": flattened,
    }


def ensure_dirs_exist(assets_root: Path) -> None:
    for pack in PACKS:
        if not (assets_root / pack).exists():
            raise FileNotFoundError(f"Missing expected pack directory: {assets_root / pack}")


def main() -> int:
    args = parse_args()
    assets_root = Path(args.assets_root).resolve()

    try:
        ensure_dirs_exist(assets_root)

        manifests: dict[str, dict[str, Any]] = {}
        manifests["tabler"] = build_iconify_manifest(assets_root, "tabler", args.tabler_version, args.tabler_url)
        manifests["lucide"] = build_iconify_manifest(assets_root, "lucide", args.lucide_version, args.lucide_url)
        manifests["fluent"] = build_iconify_manifest(assets_root, "fluent", args.fluent_version, args.fluent_url)
        manifests["aws"] = build_aws_manifest(assets_root, args.aws_zip_label, args.aws_url[0] if args.aws_url else "")

        registry = build_registry(assets_root, manifests)
        write_json(assets_root / "registry.manifest.json", registry)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote manifests under {assets_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
