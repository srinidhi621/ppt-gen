#!/usr/bin/env python3
"""Convert Iconify icons.json payloads into standalone SVG files."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--icons-json", required=True, help="Path to Iconify icons.json")
    parser.add_argument("--output-dir", required=True, help="Directory to write SVG files")
    return parser.parse_args()


def safe_icon_filename(icon_name: str) -> str:
    return icon_name.replace(":", "_")


def build_svg_text(width: int, height: int, body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}">{body}</svg>\n'
    )


def main() -> int:
    args = parse_args()
    icons_path = Path(args.icons_json)
    out_dir = Path(args.output_dir)

    if not icons_path.exists():
        print(f"ERROR: icons.json not found: {icons_path}", file=sys.stderr)
        return 2

    with icons_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    icons = payload.get("icons")
    if not isinstance(icons, dict):
        print(f"ERROR: invalid icons payload, expected object at 'icons': {icons_path}", file=sys.stderr)
        return 3

    default_width = int(payload.get("width", 24))
    default_height = int(payload.get("height", 24))

    out_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for name in sorted(icons):
        icon_data = icons[name]
        if not isinstance(icon_data, dict):
            print(f"WARN: skipping malformed icon '{name}'", file=sys.stderr)
            continue
        body = icon_data.get("body")
        if not isinstance(body, str) or not body:
            print(f"WARN: skipping icon without body '{name}'", file=sys.stderr)
            continue

        width = int(icon_data.get("width", default_width))
        height = int(icon_data.get("height", default_height))

        svg_text = build_svg_text(width, height, body)
        filename = safe_icon_filename(name) + ".svg"
        path = out_dir / filename
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(svg_text)
        written += 1

    print(f"Converted {written} icons from {icons_path} -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
