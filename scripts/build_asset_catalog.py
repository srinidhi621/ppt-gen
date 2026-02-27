"""Build a unified asset catalog for cue-to-asset matching.

Usage:
    python scripts/build_asset_catalog.py
"""

from __future__ import annotations

import json
from pathlib import Path

from src.assets import build_asset_catalog


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    assets_root = root / "assets"
    out_path = assets_root / "catalog" / "asset_catalog.json"
    payload = build_asset_catalog(assets_root)
    summary = dict(payload.get("summary", {}))
    summary["generated_by"] = "scripts/build_asset_catalog.py"
    payload["summary"] = summary

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote asset catalog: {out_path}")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
