#!/usr/bin/env python3
"""Convert external SVG icon packs to PNG and merge into assets/icons/icons.json."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import cairosvg

RENDER_SIZE = 512
PACK_ORDER = ("tabler", "lucide", "fluent", "aws", "azure", "gcp")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Project root path",
    )
    parser.add_argument(
        "--packs",
        type=str,
        default="tabler,lucide,fluent,aws",
        help="Comma-separated pack names to ingest",
    )
    parser.add_argument(
        "--output-size",
        type=int,
        default=RENDER_SIZE,
        help="Square output size in pixels",
    )
    parser.add_argument(
        "--limit-per-pack",
        type=int,
        default=0,
        help="Optional deterministic cap per pack (0 = no limit)",
    )
    return parser.parse_args()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_filename(text: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9._-]+", "_", text).strip("_")
    return sanitized or "icon"


def _convert_svg(svg_path: Path, png_path: Path, output_size: int) -> None:
    cairosvg.svg2png(
        url=str(svg_path),
        write_to=str(png_path),
        output_width=output_size,
        output_height=output_size,
        background_color=None,
    )


def _existing_index(icons_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for icon in icons_payload.get("icons", []):
        icon_id = str(icon.get("icon_id", "")).strip()
        if icon_id:
            out[icon_id] = dict(icon)
    return out


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()

    icons_json_path = project_root / "assets" / "icons" / "icons.json"
    registry_path = project_root / "assets" / "external_assets" / "registry.manifest.json"
    png_root = project_root / "assets" / "icons" / "png" / "external"

    icons_payload = _read_json(icons_json_path)
    registry_payload = _read_json(registry_path)
    registry_icons = registry_payload.get("icons", [])
    by_id = _existing_index(icons_payload)

    requested_packs = [p.strip() for p in args.packs.split(",") if p.strip()]
    allowed = {p for p in PACK_ORDER if p in requested_packs}
    if not allowed:
        raise ValueError("No valid packs requested.")

    converted = 0
    reused = 0
    failed = 0
    ingested = 0

    per_pack_count = {pack: 0 for pack in allowed}

    for icon in registry_icons:
        pack = str(icon.get("pack", "")).strip()
        if pack not in allowed:
            continue
        if args.limit_per_pack > 0 and per_pack_count[pack] >= args.limit_per_pack:
            continue

        icon_id = str(icon.get("id", "")).strip()
        svg_rel = str(icon.get("svg_path", "")).strip()
        if not icon_id or not svg_rel:
            continue

        svg_path = project_root / "assets" / "external_assets" / pack / svg_rel
        if not svg_path.exists():
            failed += 1
            continue

        icon_name = icon_id.split(":", 1)[1] if ":" in icon_id else icon_id
        png_name = f"{_safe_filename(icon_name)}.png"
        png_rel = f"external/{pack}/{png_name}"
        png_path = png_root / pack / png_name
        png_path.parent.mkdir(parents=True, exist_ok=True)

        if png_path.exists():
            reused += 1
        else:
            try:
                _convert_svg(svg_path, png_path, args.output_size)
                converted += 1
            except Exception:
                failed += 1
                continue

        tags = [str(t).lower() for t in icon.get("tags", [])]
        categories = [str(c).lower() for c in icon.get("categories", [])]
        aliases = [str(a).lower() for a in icon.get("aliases", [])]
        tags_out = sorted(set(tags + categories))
        synonyms_out = sorted(set(aliases))

        by_id[icon_id] = {
            "icon_id": icon_id,
            "filename": png_rel,
            "source_pack": pack,
            "source_svg_path": f"{pack}/{svg_rel}",
            "tags": tags_out,
            "synonyms": synonyms_out,
        }
        ingested += 1
        per_pack_count[pack] += 1

    merged_icons = sorted(by_id.values(), key=lambda item: str(item["icon_id"]))
    out_payload = {
        "version": "2.0",
        "source": "local_png_plus_external_packs",
        "output_size_px": args.output_size,
        "icons": merged_icons,
        "total_count": len(merged_icons),
        "external_ingestion": {
            "packs": sorted(allowed),
            "registry_generated_at": registry_payload.get("generated_at"),
        },
    }

    icons_json_path.write_text(
        json.dumps(out_payload, ensure_ascii=True, sort_keys=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("External icon ingestion complete")
    print(f"  Packs: {', '.join(sorted(allowed))}")
    print(f"  Converted PNGs: {converted}")
    print(f"  Reused PNGs: {reused}")
    print(f"  Failed conversions: {failed}")
    print(f"  Icons ingested/updated: {ingested}")
    print(f"  Total icons in metadata: {len(merged_icons)}")
    print(f"  Icons metadata: {icons_json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
