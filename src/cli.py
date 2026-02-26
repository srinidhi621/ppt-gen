"""CLI entry point for PPT-Gen pipeline."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from .config import load_config
from .generate_pipeline import (
    CombinedInputError,
    build_deckir_from_content,
    split_combined_markdown,
)
from .logging_utils import log_event
from .llm import LLMClientError, PlannerError, create_llm_client, load_dotenv, plan_deck_with_llm
from .models.deck_ir import DeckIR
from .normalize.parser import parse_markdown
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


def _resolve_usd_inr_rate() -> float:
    raw = os.environ.get("USD_INR_RATE", "").strip()
    if not raw:
        return 83.0
    try:
        parsed = float(raw)
    except ValueError:
        return 83.0
    return parsed if parsed > 0 else 83.0


def _cost_inr(usd_cost: float | None, usd_inr_rate: float) -> float | None:
    if usd_cost is None:
        return None
    return round(usd_cost * usd_inr_rate, 8)


def _append_run_metrics(
    *,
    project_root: Path,
    run_id: str,
    planner_mode: str,
    provider: str,
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
    estimated_cost_usd: float | None,
    estimated_cost_inr: float | None,
    planner_latency_seconds: float | None,
    total_latency_seconds: float,
    output_pptx: Path,
) -> Path:
    metrics_path = project_root / "run_metrics.csv"
    now_utc = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    headers = [
        "timestamp_utc",
        "run_id",
        "planner_mode",
        "provider",
        "model",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "estimated_cost_usd",
        "estimated_cost_inr",
        "planner_latency_seconds",
        "total_latency_seconds",
        "output_pptx",
    ]
    usd_str = f"{estimated_cost_usd:.2f}" if estimated_cost_usd is not None else "n/a"
    inr_str = f"{estimated_cost_inr:.2f}" if estimated_cost_inr is not None else "n/a"
    row = [
        now_utc,
        run_id,
        planner_mode,
        provider,
        model,
        str(prompt_tokens) if prompt_tokens is not None else "n/a",
        str(completion_tokens) if completion_tokens is not None else "n/a",
        str(total_tokens) if total_tokens is not None else "n/a",
        usd_str,
        inr_str,
        str(planner_latency_seconds) if planner_latency_seconds is not None else "n/a",
        str(round(total_latency_seconds, 3)),
        str(output_pptx),
    ]

    header_line = ",".join(headers)
    row_line = ",".join(_csv_cell(value) for value in row)
    should_write_header = True
    if metrics_path.exists():
        first_line = metrics_path.read_text(encoding="utf-8").splitlines()
        should_write_header = not first_line or first_line[0] != header_line

    mode = "w" if should_write_header else "a"
    with metrics_path.open(mode, encoding="utf-8") as handle:
        if should_write_header:
            handle.write(header_line + "\n")
        handle.write(row_line + "\n")
    return metrics_path


def _csv_cell(value: str) -> str:
    cleaned = value.replace("\n", " ").strip()
    if "," in cleaned or '"' in cleaned:
        return '"' + cleaned.replace('"', '""') + '"'
    return cleaned


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


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate deck from a combined markdown input and run pipeline."""
    total_start = time.perf_counter()
    config = load_config(Path(args.project_root) if args.project_root else None)

    errors = validate_template_catalog(
        Path(config.template_path), Path(config.layout_catalog_path)
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    combined_input_path = Path(args.input)
    if not combined_input_path.exists():
        print(f"ERROR: Combined input file not found: {combined_input_path}")
        return 1

    run_id = args.run_id if args.run_id else _generate_run_id()
    run_dir = Path(config.runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "run_log.jsonl"

    combined_text = combined_input_path.read_text(encoding="utf-8")
    try:
        content_text, cues_data = split_combined_markdown(combined_text)
    except CombinedInputError as exc:
        print(f"ERROR: {exc}")
        return 1

    content_path = run_dir / "content.md"
    cues_path = run_dir / "cues.json"
    content_path.write_text(content_text + "\n", encoding="utf-8")
    with cues_path.open("w", encoding="utf-8") as handle:
        json.dump(cues_data, handle, sort_keys=True, ensure_ascii=True, indent=2)
        handle.write("\n")

    if args.write_inputs:
        inputs_dir = Path(config.inputs_dir)
        inputs_dir.mkdir(parents=True, exist_ok=True)
        (inputs_dir / "content.md").write_text(content_text + "\n", encoding="utf-8")
        with (inputs_dir / "cues.json").open("w", encoding="utf-8") as handle:
            json.dump(cues_data, handle, sort_keys=True, ensure_ascii=True, indent=2)
            handle.write("\n")

    content_model = parse_markdown(content_path, cues_path)
    log_event(
        log_path,
        "NORMALIZE_DONE",
        {
            "sections_count": len(content_model.sections),
            "cues_count": len(content_model.cues),
            "source_hash": content_model.source_hash,
        },
    )

    planner_mode = "llm" if args.planner == "gemini" else args.planner
    project_root = Path(config.project_root)
    load_dotenv(project_root / ".env")
    usd_inr_rate = _resolve_usd_inr_rate()
    llm_usage_payload = None
    planner_latency_seconds: float | None = None
    if planner_mode == "llm":
        llm_provider = args.llm_provider
        model_name = args.llm_model or args.gemini_model
        try:
            client = create_llm_client(
                provider=llm_provider,
                model=model_name,
                timeout_seconds=args.planner_timeout_seconds,
            )
            planner_start = time.perf_counter()
            deckir_v1, planning_stats = plan_deck_with_llm(
                client=client,
                content_model=content_model,
                cues_data=cues_data,
                layout_catalog_path=Path(config.layout_catalog_path),
                icons_json_path=Path(config.icons_json_path),
                run_id=run_id,
                deck_id=combined_input_path.stem,
                max_retries=args.planner_retries,
            )
            planner_latency_seconds = round(time.perf_counter() - planner_start, 3)
        except LLMClientError as exc:
            print(f"ERROR: Failed to initialize LLM client: {exc}")
            return 1
        except PlannerError as exc:
            print(f"ERROR: LLM planning failed: {exc}")
            return 1

        llm_usage_payload = planning_stats.to_dict()
        llm_usage_payload["usd_inr_rate"] = usd_inr_rate
        llm_usage_payload["estimated_cost_inr"] = _cost_inr(
            planning_stats.estimated_cost_usd,
            usd_inr_rate,
        )
        llm_usage_path = run_dir / "llm_usage.json"
        llm_usage_path.write_text(
            json.dumps(llm_usage_payload, sort_keys=True, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )
        log_event(
            log_path,
            "PLAN_DONE",
            {
                "slides_count": len(deckir_v1.slides),
                "planner": "llm",
                "provider": planning_stats.provider,
                "model": planning_stats.model,
                "attempts": planning_stats.attempts,
                "prompt_tokens": planning_stats.prompt_tokens,
                "completion_tokens": planning_stats.completion_tokens,
                "total_tokens": planning_stats.total_tokens,
                "estimated_cost_usd": planning_stats.estimated_cost_usd,
                "estimated_cost_inr": llm_usage_payload["estimated_cost_inr"],
                "usd_inr_rate": usd_inr_rate,
                "planner_latency_seconds": planner_latency_seconds,
                "llm_usage_path": str(llm_usage_path),
            },
        )
    else:
        deckir_v1 = build_deckir_from_content(
            content_model=content_model,
            cues_data=cues_data,
            layout_catalog_path=Path(config.layout_catalog_path),
            run_id=run_id,
            deck_id=combined_input_path.stem,
        )
        log_event(
            log_path,
            "PLAN_DONE",
            {
                "slides_count": len(deckir_v1.slides),
                "planner": "deterministic",
            },
        )

    deckir_v1_path = run_dir / "deckir_v1.json"
    deckir_v1_path.write_text(deckir_v1.to_json(), encoding="utf-8")

    deck_v1_1, validation_report = validate_and_remediate(
        deckir_v1, Path(config.layout_catalog_path)
    )
    validation_report_path = run_dir / "validation_report.json"
    validation_report_path.write_text(validation_report.to_json(), encoding="utf-8")
    deckir_v1_1_path = run_dir / "deckir_v1_1.json"
    deckir_v1_1_path.write_text(deck_v1_1.to_json(), encoding="utf-8")

    log_event(
        log_path,
        "VALIDATE_DONE",
        {
            "violations_count": len(validation_report.violations),
            "blocking_count": sum(
                1 for violation in validation_report.violations if violation.severity == "BLOCKING"
            ),
        },
    )

    renderer = Renderer(
        Path(config.template_path),
        Path(config.layout_catalog_path),
        Path(config.icons_json_path),
    )
    output_path = run_dir / "deck_v1.pptx"
    render_map = renderer.render(deck_v1_1, output_path)
    render_map_path = run_dir / "render_map.json"
    render_map_path.write_text(render_map.to_json(), encoding="utf-8")

    log_event(
        log_path,
        "RENDER_DONE",
        {"output_path": str(output_path), "slides_rendered": len(render_map.entries)},
    )

    total_latency_seconds = round(time.perf_counter() - total_start, 3)
    provider = llm_usage_payload["provider"] if llm_usage_payload is not None else "deterministic"
    model = llm_usage_payload["model"] if llm_usage_payload is not None else "n/a"
    metrics_path = _append_run_metrics(
        project_root=project_root,
        run_id=run_id,
        planner_mode=planner_mode,
        provider=provider,
        model=model,
        prompt_tokens=llm_usage_payload["prompt_tokens"] if llm_usage_payload is not None else None,
        completion_tokens=llm_usage_payload["completion_tokens"] if llm_usage_payload is not None else None,
        total_tokens=llm_usage_payload["total_tokens"] if llm_usage_payload is not None else None,
        estimated_cost_usd=llm_usage_payload["estimated_cost_usd"] if llm_usage_payload is not None else None,
        estimated_cost_inr=llm_usage_payload["estimated_cost_inr"] if llm_usage_payload is not None else None,
        planner_latency_seconds=planner_latency_seconds,
        total_latency_seconds=total_latency_seconds,
        output_pptx=output_path,
    )

    print("Generate pipeline complete.")
    print(f"  Run ID: {run_id}")
    print(f"  Combined input: {combined_input_path}")
    print(f"  Split content: {content_path}")
    print(f"  Split cues: {cues_path}")
    print(f"  Output PPTX: {output_path}")
    print(f"  Artifacts directory: {run_dir}")
    print(f"  Total latency (s): {total_latency_seconds:.3f}")
    if llm_usage_payload is not None:
        print("  LLM usage:")
        print(f"    Provider: {llm_usage_payload['provider']}")
        print(f"    Model: {llm_usage_payload['model']}")
        print(f"    Prompt tokens: {llm_usage_payload['prompt_tokens']}")
        print(f"    Completion tokens: {llm_usage_payload['completion_tokens']}")
        print(f"    Total tokens: {llm_usage_payload['total_tokens']}")
        if planner_latency_seconds is not None:
            print(f"    Planner latency (s): {planner_latency_seconds:.3f}")
        if llm_usage_payload["estimated_cost_usd"] is not None:
            print(f"    Estimated cost (USD): ${llm_usage_payload['estimated_cost_usd']:.6f}")
            print(f"    Estimated cost (INR): INR {llm_usage_payload['estimated_cost_inr']:.6f}")
            print(f"    USD/INR rate: {llm_usage_payload['usd_inr_rate']:.4f}")
        else:
            print("    Estimated cost (USD): unavailable (no pricing profile configured)")
            print("    Estimated cost (INR): unavailable (USD estimate missing)")
        print(f"    Usage artifact: {run_dir / 'llm_usage.json'}")
    print(f"  Run metrics file: {metrics_path}")
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

    # Generate command
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate from combined markdown (content + cues) and run pipeline",
    )
    _add_common_args(generate_parser)
    generate_parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to combined markdown input with '## Content' and '## Visualization Cues'",
    )
    generate_parser.add_argument(
        "--run-id", type=str, default=None, help="Run ID (default: auto-generated timestamp)"
    )
    generate_parser.add_argument(
        "--write-inputs",
        action="store_true",
        help="Also write split content.md/cues.json into inputs/",
    )
    generate_parser.add_argument(
        "--planner",
        choices=("deterministic", "llm", "gemini"),
        default="deterministic",
        help="Planning mode (default: deterministic). 'gemini' is kept as a legacy alias.",
    )
    generate_parser.add_argument(
        "--llm-provider",
        choices=("gemini", "azure_openai"),
        default="azure_openai",
        help="LLM provider when planner=llm (default: azure_openai)",
    )
    generate_parser.add_argument(
        "--llm-model",
        type=str,
        default=None,
        help="LLM model/deployment hint; provider-specific defaults apply when omitted",
    )
    generate_parser.add_argument(
        "--gemini-model",
        type=str,
        default=None,
        help="Deprecated alias for --llm-model when using Gemini",
    )
    generate_parser.add_argument(
        "--planner-retries",
        type=int,
        default=2,
        help="Number of retries for planner validation failures (default: 2)",
    )
    generate_parser.add_argument(
        "--planner-timeout-seconds",
        type=int,
        default=120,
        help="LLM planner request timeout in seconds (default: 120)",
    )
    generate_parser.set_defaults(func=cmd_generate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
