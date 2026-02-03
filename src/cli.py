"""CLI entry point (scaffold)."""

from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .validate.drift import validate_template_catalog


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Path to project root (default: auto-detect)",
    )


def cmd_validate(args: argparse.Namespace) -> int:
    config = load_config(Path(args.project_root) if args.project_root else None)
    errors = validate_template_catalog(
        Path(config.template_path), Path(config.layout_catalog_path)
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Template/catalog validation passed.")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    _ = load_config(Path(args.project_root) if args.project_root else None)
    raise NotImplementedError("render command is not implemented yet")


def cmd_smoke(args: argparse.Namespace) -> int:
    _ = load_config(Path(args.project_root) if args.project_root else None)
    raise NotImplementedError("smoke command is not implemented yet")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PPT-Gen CLI (scaffold)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate catalog/template")
    _add_common_args(validate_parser)
    validate_parser.set_defaults(func=cmd_validate)

    render_parser = subparsers.add_parser("render", help="Render from DeckIR JSON")
    _add_common_args(render_parser)
    render_parser.add_argument("--deckir", type=str, required=True, help="DeckIR JSON path")
    render_parser.set_defaults(func=cmd_render)

    smoke_parser = subparsers.add_parser("smoke", help="Run deterministic smoke test")
    _add_common_args(smoke_parser)
    smoke_parser.set_defaults(func=cmd_smoke)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
