"""CLI entry point for PPT-Gen pipeline."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List

from .config import load_config
from .compose import build_composition_spec
from .generate_pipeline import (
    CombinedInputError,
    build_deckir_from_content,
    split_combined_markdown,
)
from .logging_utils import log_event
from .llm import (
    LLMClientError,
    PlannerError,
    ReviewerError,
    create_llm_client,
    load_dotenv,
    plan_deck_with_llm,
    review_rendered_deck_with_llm,
)
from .models.deck_ir import DeckIR
from .normalize.parser import parse_markdown
from .render.renderer import Renderer
from .review import ReviewAutomationError, collect_review_images, export_slides_to_images
from .validate.drift import validate_template_catalog
from .validate.preflight import validate_and_remediate, validate_deck


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


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _to_payload(deck: DeckIR) -> Dict[str, Any]:
    return json.loads(deck.to_json())


def _build_capability_manifest(config, cues_data: Dict[str, Any]) -> Dict[str, Any]:
    layout_catalog = json.loads(Path(config.layout_catalog_path).read_text(encoding="utf-8"))
    icons_catalog = json.loads(Path(config.icons_json_path).read_text(encoding="utf-8"))
    branded_catalog_path = Path(config.assets_dir) / "catalog" / "branded_images.json"
    branded_catalog = (
        json.loads(branded_catalog_path.read_text(encoding="utf-8"))
        if branded_catalog_path.exists()
        else {"images": {}}
    )
    image_capable_layouts: List[str] = []
    for entry in layout_catalog.get("layouts", []):
        fields = [f.get("field_key", "") for f in entry.get("fields", [])]
        if any(key.startswith("ph_image") for key in fields):
            image_capable_layouts.append(str(entry.get("layout_id", "")))
    return {
        "image_capable_layouts": sorted([lid for lid in image_capable_layouts if lid]),
        "layout_count": len(layout_catalog.get("layouts", [])),
        "icon_count": len(icons_catalog.get("icons", [])),
        "branded_image_count": len(branded_catalog.get("images", {})),
        "cues_count": len(cues_data.get("cues", [])),
    }


def _run_diagnose_json(
    *,
    project_root: Path,
    run_dir: Path,
    pptx_filename: str,
    json_out_path: Path,
) -> Dict[str, Any]:
    diagnose_script = project_root / "scripts" / "diagnose_pptx.py"
    cmd = [
        sys.executable,
        str(diagnose_script),
        str(run_dir),
        "--pptx",
        pptx_filename,
        "--json-out",
        str(json_out_path),
    ]
    result = subprocess.run(
        cmd,
        cwd=str(project_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        detail = stderr or stdout or "diagnose_pptx.py failed"
        raise RuntimeError(detail)
    return json.loads(json_out_path.read_text(encoding="utf-8"))


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


def cmd_generate_auto(args: argparse.Namespace) -> int:
    """Fully automated one-loop pipeline with multimodal review and planner rework."""
    total_start = time.perf_counter()
    config = load_config(Path(args.project_root) if args.project_root else None)
    project_root = Path(config.project_root)

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
    _write_json(cues_path, cues_data)
    if args.write_inputs:
        inputs_dir = Path(config.inputs_dir)
        inputs_dir.mkdir(parents=True, exist_ok=True)
        (inputs_dir / "content.md").write_text(content_text + "\n", encoding="utf-8")
        _write_json(inputs_dir / "cues.json", cues_data)

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

    load_dotenv(project_root / ".env")
    usd_inr_rate = _resolve_usd_inr_rate()
    deck_id = combined_input_path.stem
    capability_manifest = _build_capability_manifest(config, cues_data)
    _write_json(run_dir / "planner_context.json", capability_manifest)
    log_event(log_path, "PLANNER_CONTEXT_DONE", capability_manifest)

    planner_model = args.llm_model or args.gemini_model
    try:
        planner_client = create_llm_client(
            provider=args.llm_provider,
            model=planner_model,
            timeout_seconds=args.planner_timeout_seconds,
        )
    except LLMClientError as exc:
        print(f"ERROR: Failed to initialize planner LLM client: {exc}")
        return 1

    # Planner V1
    try:
        plan_v1_start = time.perf_counter()
        planner_deck_v1, plan_stats_v1 = plan_deck_with_llm(
            client=planner_client,
            content_model=content_model,
            cues_data=cues_data,
            layout_catalog_path=Path(config.layout_catalog_path),
            icons_json_path=Path(config.icons_json_path),
            run_id=run_id,
            deck_id=deck_id,
            max_retries=args.planner_retries,
        )
        plan_v1_latency = round(time.perf_counter() - plan_v1_start, 3)
    except PlannerError as exc:
        print(f"ERROR: Planner V1 failed: {exc}")
        return 1

    planner_deck_v1_payload = _to_payload(planner_deck_v1)
    _write_json(run_dir / "planner_deckir_v1.json", planner_deck_v1_payload)
    _write_json(run_dir / "deckir_v1.json", planner_deck_v1_payload)
    plan_v1_usage_payload = plan_stats_v1.to_dict()
    plan_v1_usage_payload["usd_inr_rate"] = usd_inr_rate
    plan_v1_usage_payload["estimated_cost_inr"] = _cost_inr(
        plan_stats_v1.estimated_cost_usd, usd_inr_rate
    )
    _write_json(run_dir / "llm_usage_plan_v1.json", plan_v1_usage_payload)
    log_event(
        log_path,
        "PLAN_V1_DONE",
        {
            "slides_count": len(planner_deck_v1.slides),
            "provider": plan_stats_v1.provider,
            "model": plan_stats_v1.model,
            "attempts": plan_stats_v1.attempts,
            "total_tokens": plan_stats_v1.total_tokens,
            "planner_latency_seconds": plan_v1_latency,
            "llm_usage_path": str(run_dir / "llm_usage_plan_v1.json"),
        },
    )

    # Compose+Validate+Render V1 (deterministic path)
    deck_v1_1, validation_v1 = validate_and_remediate(
        planner_deck_v1, Path(config.layout_catalog_path)
    )
    validation_v1_post = validate_deck(deck_v1_1, Path(config.layout_catalog_path))
    _write_json(run_dir / "deckir_v1_1.json", _to_payload(deck_v1_1))
    _write_json(run_dir / "validation_report_v1.json", json.loads(validation_v1.to_json()))
    _write_json(
        run_dir / "validation_report_v1_post.json",
        json.loads(validation_v1_post.to_json()),
    )
    composition_spec_v1 = build_composition_spec(
        deck_before=planner_deck_v1,
        deck_after=deck_v1_1,
        before_report=validation_v1,
        after_report=validation_v1_post,
        stage="v1",
    ).to_dict()
    _write_json(run_dir / "composition_spec_v1.json", composition_spec_v1)
    log_event(
        log_path,
        "VALIDATE_V1_DONE",
        {
            "violations_count": len(validation_v1.violations),
            "blocking_count": sum(
                1 for violation in validation_v1.violations if violation.severity == "BLOCKING"
            ),
        },
    )

    renderer = Renderer(
        Path(config.template_path),
        Path(config.layout_catalog_path),
        Path(config.icons_json_path),
    )
    output_v1 = run_dir / "deck_v1.pptx"
    render_map_v1 = renderer.render(deck_v1_1, output_v1)
    _write_json(run_dir / "render_map_v1.json", json.loads(render_map_v1.to_json()))
    # Backward-compatible artifact name
    _write_json(run_dir / "render_map.json", json.loads(render_map_v1.to_json()))
    log_event(
        log_path,
        "RENDER_V1_DONE",
        {"output_path": str(output_v1), "slides_rendered": len(render_map_v1.entries)},
    )

    # Auto export slide images for multimodal review
    review_images_dir = run_dir / "review_images" / "v1"
    try:
        export_slides_to_images(
            output_v1,
            review_images_dir,
            timeout_seconds=args.export_timeout_seconds,
            dpi=args.review_export_dpi,
        )
        image_paths = collect_review_images(
            review_images_dir,
            expected_count=len(render_map_v1.entries),
            min_width=args.review_min_width,
        )
    except ReviewAutomationError as exc:
        print(f"ERROR: Review image export failed: {exc}")
        return 1
    log_event(
        log_path,
        "REVIEW_IMAGES_INGESTED",
        {
            "count": len(image_paths),
            "directory": str(review_images_dir),
        },
    )

    # Diagnose V1 for machine-readable review context
    diagnose_report_v1_path = run_dir / "diagnose_report_v1.json"
    try:
        diagnose_report_v1 = _run_diagnose_json(
            project_root=project_root,
            run_dir=run_dir,
            pptx_filename="deck_v1.pptx",
            json_out_path=diagnose_report_v1_path,
        )
    except RuntimeError as exc:
        print(f"ERROR: Diagnose V1 failed: {exc}")
        return 1
    log_event(
        log_path,
        "DIAGNOSE_V1_DONE",
        diagnose_report_v1.get("summary", {}),
    )

    # Multimodal review call
    review_model = args.review_model or planner_model
    review_provider = args.review_provider or args.llm_provider
    try:
        review_client = create_llm_client(
            provider=review_provider,
            model=review_model,
            timeout_seconds=args.review_timeout_seconds,
        )
    except LLMClientError as exc:
        print(f"ERROR: Failed to initialize review LLM client: {exc}")
        return 1

    review_image_paths = image_paths[: args.review_max_images] if args.review_max_images > 0 else image_paths
    try:
        review_feedback, review_stats = review_rendered_deck_with_llm(
            client=review_client,
            run_id=run_id,
            deck_id=deck_id,
            content_markdown=content_text,
            cues_data=cues_data,
            planner_deck_v1=planner_deck_v1_payload,
            composition_spec_v1=composition_spec_v1,
            diagnose_report_v1=diagnose_report_v1,
            capability_manifest=capability_manifest,
            image_paths=review_image_paths,
            max_retries=args.review_retries,
        )
    except ReviewerError as exc:
        print(f"ERROR: Multimodal review failed: {exc}")
        return 1

    review_feedback_payload = review_feedback.to_dict()
    _write_json(run_dir / "review_feedback_v1.json", review_feedback_payload)
    review_usage_payload = review_stats.to_dict()
    review_usage_payload["usd_inr_rate"] = usd_inr_rate
    review_usage_payload["estimated_cost_inr"] = _cost_inr(
        review_stats.estimated_cost_usd, usd_inr_rate
    )
    _write_json(run_dir / "llm_usage_review_v1.json", review_usage_payload)
    log_event(
        log_path,
        "MULTIMODAL_REVIEW_DONE",
        {
            "attempts": review_stats.attempts,
            "total_tokens": review_stats.total_tokens,
            "findings_count": len(review_feedback.slide_findings),
            "change_requests_count": len(review_feedback.change_requests),
            "llm_usage_path": str(run_dir / "llm_usage_review_v1.json"),
        },
    )

    # Planner V2 rework with explicit feedback channel
    try:
        plan_v2_start = time.perf_counter()
        planner_deck_v2, plan_stats_v2 = plan_deck_with_llm(
            client=planner_client,
            content_model=content_model,
            cues_data=cues_data,
            layout_catalog_path=Path(config.layout_catalog_path),
            icons_json_path=Path(config.icons_json_path),
            run_id=run_id,
            deck_id=deck_id,
            max_retries=args.planner_retries,
            review_feedback=review_feedback_payload,
            prior_planner_output=planner_deck_v1_payload,
            diagnose_report=diagnose_report_v1,
            composition_spec=composition_spec_v1,
        )
        plan_v2_latency = round(time.perf_counter() - plan_v2_start, 3)
    except PlannerError as exc:
        print(f"ERROR: Planner V2 rework failed: {exc}")
        return 1

    planner_deck_v2_payload = _to_payload(planner_deck_v2)
    _write_json(run_dir / "planner_deckir_v2.json", planner_deck_v2_payload)
    _write_json(run_dir / "deckir_v2.json", planner_deck_v2_payload)
    plan_v2_usage_payload = plan_stats_v2.to_dict()
    plan_v2_usage_payload["usd_inr_rate"] = usd_inr_rate
    plan_v2_usage_payload["estimated_cost_inr"] = _cost_inr(
        plan_stats_v2.estimated_cost_usd, usd_inr_rate
    )
    _write_json(run_dir / "llm_usage_plan_v2.json", plan_v2_usage_payload)
    log_event(
        log_path,
        "PLAN_V2_DONE",
        {
            "slides_count": len(planner_deck_v2.slides),
            "provider": plan_stats_v2.provider,
            "model": plan_stats_v2.model,
            "attempts": plan_stats_v2.attempts,
            "total_tokens": plan_stats_v2.total_tokens,
            "planner_latency_seconds": plan_v2_latency,
            "llm_usage_path": str(run_dir / "llm_usage_plan_v2.json"),
        },
    )

    # Compose+Validate+Render V2
    deck_v2_1, validation_v2 = validate_and_remediate(
        planner_deck_v2, Path(config.layout_catalog_path)
    )
    validation_v2_post = validate_deck(deck_v2_1, Path(config.layout_catalog_path))
    _write_json(run_dir / "deckir_v2_1.json", _to_payload(deck_v2_1))
    _write_json(run_dir / "validation_report_v2.json", json.loads(validation_v2.to_json()))
    _write_json(
        run_dir / "validation_report_v2_post.json",
        json.loads(validation_v2_post.to_json()),
    )
    composition_spec_v2 = build_composition_spec(
        deck_before=planner_deck_v2,
        deck_after=deck_v2_1,
        before_report=validation_v2,
        after_report=validation_v2_post,
        stage="v2",
    ).to_dict()
    _write_json(run_dir / "composition_spec_v2.json", composition_spec_v2)
    log_event(
        log_path,
        "VALIDATE_V2_DONE",
        {
            "violations_count": len(validation_v2.violations),
            "blocking_count": sum(
                1 for violation in validation_v2.violations if violation.severity == "BLOCKING"
            ),
        },
    )

    output_v2 = run_dir / "deck_v2.pptx"
    render_map_v2 = renderer.render(deck_v2_1, output_v2)
    _write_json(run_dir / "render_map_v2.json", json.loads(render_map_v2.to_json()))
    log_event(
        log_path,
        "RENDER_V2_DONE",
        {"output_path": str(output_v2), "slides_rendered": len(render_map_v2.entries)},
    )

    diagnose_report_v2_path = run_dir / "diagnose_report_v2.json"
    try:
        diagnose_report_v2 = _run_diagnose_json(
            project_root=project_root,
            run_dir=run_dir,
            pptx_filename="deck_v2.pptx",
            json_out_path=diagnose_report_v2_path,
        )
    except RuntimeError as exc:
        print(f"ERROR: Diagnose V2 failed: {exc}")
        return 1
    log_event(
        log_path,
        "DIAGNOSE_V2_DONE",
        diagnose_report_v2.get("summary", {}),
    )

    summary_v1 = diagnose_report_v1.get("summary", {})
    summary_v2 = diagnose_report_v2.get("summary", {})
    run_summary = {
        "run_id": run_id,
        "v1": summary_v1,
        "v2": summary_v2,
        "delta": {
            "overflow_slides": int(summary_v2.get("slides_with_text_overflow", 0))
            - int(summary_v1.get("slides_with_text_overflow", 0)),
            "image_gap": int(summary_v2.get("total_image_gap", 0))
            - int(summary_v1.get("total_image_gap", 0)),
            "total_images_rendered": int(summary_v2.get("total_images_rendered", 0))
            - int(summary_v1.get("total_images_rendered", 0)),
        },
    }
    _write_json(run_dir / "run_summary.json", run_summary)
    log_event(log_path, "RUN_COMPLETE", run_summary)

    total_latency_seconds = round(time.perf_counter() - total_start, 3)
    metrics_path = _append_run_metrics(
        project_root=project_root,
        run_id=run_id,
        planner_mode="llm_auto_loop",
        provider=plan_stats_v2.provider,
        model=plan_stats_v2.model,
        prompt_tokens=(
            plan_stats_v1.prompt_tokens + review_stats.prompt_tokens + plan_stats_v2.prompt_tokens
        ),
        completion_tokens=(
            plan_stats_v1.completion_tokens
            + review_stats.completion_tokens
            + plan_stats_v2.completion_tokens
        ),
        total_tokens=(
            plan_stats_v1.total_tokens + review_stats.total_tokens + plan_stats_v2.total_tokens
        ),
        estimated_cost_usd=(
            (plan_stats_v1.estimated_cost_usd or 0.0)
            + (review_stats.estimated_cost_usd or 0.0)
            + (plan_stats_v2.estimated_cost_usd or 0.0)
        ),
        estimated_cost_inr=_cost_inr(
            (plan_stats_v1.estimated_cost_usd or 0.0)
            + (review_stats.estimated_cost_usd or 0.0)
            + (plan_stats_v2.estimated_cost_usd or 0.0),
            usd_inr_rate,
        ),
        planner_latency_seconds=None,
        total_latency_seconds=total_latency_seconds,
        output_pptx=output_v2,
    )

    print("Automated one-loop pipeline complete.")
    print(f"  Run ID: {run_id}")
    print(f"  Input: {combined_input_path}")
    print(f"  V1 PPTX: {output_v1}")
    print(f"  V2 PPTX: {output_v2}")
    print(f"  Review images: {review_images_dir}")
    print(f"  Artifacts directory: {run_dir}")
    print(f"  Total latency (s): {total_latency_seconds:.3f}")
    print(
        f"  Overflow slides V1->V2: "
        f"{summary_v1.get('slides_with_text_overflow', 'n/a')} -> "
        f"{summary_v2.get('slides_with_text_overflow', 'n/a')}"
    )
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

    # Fully automated one-loop command
    generate_auto_parser = subparsers.add_parser(
        "generate-auto",
        help="Automated one-loop pipeline: plan v1 -> render -> multimodal review -> replan v2 -> render",
    )
    _add_common_args(generate_auto_parser)
    generate_auto_parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to combined markdown input with '## Content' and '## Visualization Cues'",
    )
    generate_auto_parser.add_argument(
        "--run-id", type=str, default=None, help="Run ID (default: auto-generated timestamp)"
    )
    generate_auto_parser.add_argument(
        "--write-inputs",
        action="store_true",
        help="Also write split content.md/cues.json into inputs/",
    )
    generate_auto_parser.add_argument(
        "--llm-provider",
        choices=("gemini", "azure_openai"),
        default="azure_openai",
        help="LLM provider for planner calls (default: azure_openai)",
    )
    generate_auto_parser.add_argument(
        "--llm-model",
        type=str,
        default=None,
        help="Planner model/deployment hint; provider defaults apply when omitted",
    )
    generate_auto_parser.add_argument(
        "--gemini-model",
        type=str,
        default=None,
        help="Deprecated alias for --llm-model when using Gemini",
    )
    generate_auto_parser.add_argument(
        "--review-provider",
        choices=("gemini", "azure_openai"),
        default=None,
        help="Optional override provider for multimodal review (default: same as --llm-provider)",
    )
    generate_auto_parser.add_argument(
        "--review-model",
        type=str,
        default=None,
        help="Optional override model for multimodal review (default: same as planner model)",
    )
    generate_auto_parser.add_argument(
        "--planner-retries",
        type=int,
        default=2,
        help="Retries for each planner pass validation failures (default: 2)",
    )
    generate_auto_parser.add_argument(
        "--review-retries",
        type=int,
        default=1,
        help="Retries for multimodal review schema failures (default: 1)",
    )
    generate_auto_parser.add_argument(
        "--planner-timeout-seconds",
        type=int,
        default=120,
        help="Planner request timeout in seconds (default: 120)",
    )
    generate_auto_parser.add_argument(
        "--review-timeout-seconds",
        type=int,
        default=180,
        help="Multimodal review request timeout in seconds (default: 180)",
    )
    generate_auto_parser.add_argument(
        "--export-timeout-seconds",
        type=int,
        default=300,
        help="Slide image conversion timeout in seconds (default: 300)",
    )
    generate_auto_parser.add_argument(
        "--review-export-dpi",
        type=int,
        default=220,
        help="Slide image export DPI for review conversion (default: 220)",
    )
    generate_auto_parser.add_argument(
        "--review-max-images",
        type=int,
        default=20,
        help="Maximum number of slide images to attach to the review call (default: 20; <=0 means all)",
    )
    generate_auto_parser.add_argument(
        "--review-min-width",
        type=int,
        default=1600,
        help="Minimum review image width in px for ingestion validation (default: 1600)",
    )
    generate_auto_parser.set_defaults(func=cmd_generate_auto)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
