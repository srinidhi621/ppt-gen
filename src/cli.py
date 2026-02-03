"""CLI entry point for PPT-Gen pipeline."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from .config import load_config
from .logging_utils import log_event
from .models.deck_ir import DeckIR
from .render.renderer import Renderer
from .validate.drift import validate_template_catalog
from .validate.preflight import validate_and_remediate


def _generate_run_id() -> str:
    """Generate a timestamp-based run ID."""
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


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
    """Render a DeckIR JSON to PPTX."""
    config = load_config(Path(args.project_root) if args.project_root else None)
    
    # Validate template/catalog first
    errors = validate_template_catalog(
        Path(config.template_path), Path(config.layout_catalog_path)
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    
    # Load DeckIR from JSON
    deckir_path = Path(args.deckir)
    if not deckir_path.exists():
        print(f"ERROR: DeckIR file not found: {deckir_path}")
        return 1
    
    with open(deckir_path, "r", encoding="utf-8") as f:
        deckir_data = json.load(f)
    
    deck = DeckIR.model_validate(deckir_data)
    
    # Determine run directory
    run_id = args.run_id if args.run_id else deck.run_id
    run_dir = Path(config.runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    log_path = run_dir / "run_log.jsonl"
    
    # Initialize renderer
    renderer = Renderer(
        Path(config.template_path),
        Path(config.layout_catalog_path),
        Path(config.icons_json_path),
    )
    
    # Save input DeckIR as deckir_v1.json
    deckir_v1_path = run_dir / "deckir_v1.json"
    with open(deckir_v1_path, "w", encoding="utf-8") as f:
        f.write(deck.to_json())
    
    log_event(log_path, "DECKIR_LOADED", {"path": str(deckir_path), "slide_count": len(deck.slides)})
    
    # Render PPTX
    output_path = run_dir / "deck_v1.pptx"
    render_map = renderer.render(deck, output_path)
    
    # Save render map
    render_map_path = run_dir / "render_map.json"
    with open(render_map_path, "w", encoding="utf-8") as f:
        f.write(render_map.to_json())
    
    log_event(log_path, "RENDER_DONE", {
        "output_path": str(output_path),
        "slides_rendered": len(render_map.entries),
    })
    
    print(f"Rendered {len(render_map.entries)} slides to: {output_path}")
    print(f"Render map saved to: {render_map_path}")
    print(f"Run artifacts in: {run_dir}")
    return 0


def cmd_smoke(args: argparse.Namespace) -> int:
    """Run deterministic smoke test: validate → preflight → render → emit artifacts."""
    config = load_config(Path(args.project_root) if args.project_root else None)
    
    # Validate template/catalog first
    errors = validate_template_catalog(
        Path(config.template_path), Path(config.layout_catalog_path)
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    
    print("Template/catalog validation passed.")
    
    # Load DeckIR from JSON
    deckir_path = Path(args.deckir) if args.deckir else Path(config.inputs_dir) / "sample_deckir.json"
    if not deckir_path.exists():
        print(f"ERROR: DeckIR file not found: {deckir_path}")
        return 1
    
    with open(deckir_path, "r", encoding="utf-8") as f:
        deckir_data = json.load(f)
    
    deck = DeckIR.model_validate(deckir_data)
    
    # Generate run_id
    run_id = args.run_id if args.run_id else _generate_run_id()
    run_dir = Path(config.runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    log_path = run_dir / "run_log.jsonl"
    
    log_event(log_path, "SMOKE_START", {"run_id": run_id, "deckir_path": str(deckir_path)})
    
    # Save input DeckIR as deckir_v1.json
    deckir_v1_path = run_dir / "deckir_v1.json"
    with open(deckir_v1_path, "w", encoding="utf-8") as f:
        f.write(deck.to_json())
    
    log_event(log_path, "DECKIR_LOADED", {"path": str(deckir_path), "slide_count": len(deck.slides)})
    
    # Run preflight validation and remediation
    deck_v1_1, validation_report = validate_and_remediate(
        deck, Path(config.layout_catalog_path)
    )
    
    # Save validation report
    validation_report_path = run_dir / "validation_report.json"
    with open(validation_report_path, "w", encoding="utf-8") as f:
        f.write(validation_report.to_json())
    
    # Save remediated DeckIR as deckir_v1_1.json
    deckir_v1_1_path = run_dir / "deckir_v1_1.json"
    with open(deckir_v1_1_path, "w", encoding="utf-8") as f:
        f.write(deck_v1_1.to_json())
    
    log_event(log_path, "VALIDATE_DONE", {
        "violations_count": len(validation_report.violations),
        "blocking_count": sum(1 for v in validation_report.violations if v.severity == "BLOCKING"),
    })
    
    print(f"Preflight validation complete: {len(validation_report.violations)} violations found")
    
    # Initialize renderer
    renderer = Renderer(
        Path(config.template_path),
        Path(config.layout_catalog_path),
        Path(config.icons_json_path),
    )
    
    # Render PPTX from remediated DeckIR
    output_path = run_dir / "deck_v1.pptx"
    render_map = renderer.render(deck_v1_1, output_path)
    
    # Save render map
    render_map_path = run_dir / "render_map.json"
    with open(render_map_path, "w", encoding="utf-8") as f:
        f.write(render_map.to_json())
    
    log_event(log_path, "RENDER_DONE", {
        "output_path": str(output_path),
        "slides_rendered": len(render_map.entries),
    })
    
    log_event(log_path, "SMOKE_DONE", {"run_id": run_id, "success": True})
    
    print(f"\nSmoke test complete!")
    print(f"  Run ID: {run_id}")
    print(f"  Slides rendered: {len(render_map.entries)}")
    print(f"  Output PPTX: {output_path}")
    print(f"  Artifacts directory: {run_dir}")
    print(f"\nGenerated artifacts:")
    print(f"  - deckir_v1.json (input)")
    print(f"  - deckir_v1_1.json (after preflight)")
    print(f"  - validation_report.json")
    print(f"  - render_map.json")
    print(f"  - deck_v1.pptx")
    print(f"  - run_log.jsonl")
    
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PPT-Gen CLI - LLM-Assisted PPTX Generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate template against layout catalog"
    )
    _add_common_args(validate_parser)
    validate_parser.set_defaults(func=cmd_validate)

    # Render command
    render_parser = subparsers.add_parser(
        "render", help="Render a DeckIR JSON to PPTX"
    )
    _add_common_args(render_parser)
    render_parser.add_argument(
        "--deckir", type=str, required=True, help="Path to DeckIR JSON file"
    )
    render_parser.add_argument(
        "--run-id", type=str, default=None, help="Run ID (default: use run_id from DeckIR)"
    )
    render_parser.set_defaults(func=cmd_render)

    # Smoke command
    smoke_parser = subparsers.add_parser(
        "smoke", help="Run deterministic smoke test: validate → preflight → render"
    )
    _add_common_args(smoke_parser)
    smoke_parser.add_argument(
        "--deckir", type=str, default=None,
        help="Path to DeckIR JSON (default: inputs/sample_deckir.json)"
    )
    smoke_parser.add_argument(
        "--run-id", type=str, default=None, help="Run ID (default: auto-generated timestamp)"
    )
    smoke_parser.set_defaults(func=cmd_smoke)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
