"""Run the V3 pipeline across the benchmark prompt set.

This script intentionally reads prompt fixtures from generator scripts via AST
so it does not require ``openpyxl`` just to consume the eval prompt lists.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROMPT_SOURCE = PROJECT_ROOT / "scripts" / "generate_benchmark_xlsx.py"
MULTISLIDE_PROMPT_SOURCE = PROJECT_ROOT / "scripts" / "generate_multislide_benchmark_xlsx.py"
DEFAULT_MANIFEST = PROJECT_ROOT / "runs" / "v3_eval_outputs.csv"
DEFAULT_MULTISLIDE_MANIFEST = PROJECT_ROOT / "runs" / "v3_multislide_eval_outputs.csv"

sys.path.insert(0, str(PROJECT_ROOT))

from src.v3.llm_client import ResponsesClient  # noqa: E402
from src.v3.pipeline import generate  # noqa: E402


def load_test_prompts() -> list[tuple[str, str, str, str, str, str, str]]:
    module = ast.parse(PROMPT_SOURCE.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "TEST_PROMPTS":
                    return ast.literal_eval(node.value)
    raise RuntimeError(f"TEST_PROMPTS not found in {PROMPT_SOURCE}")


def load_multislide_tests() -> list[dict[str, Any]]:
    module = ast.parse(MULTISLIDE_PROMPT_SOURCE.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "MULTISLIDE_TESTS":
                    return ast.literal_eval(node.value)
    raise RuntimeError(f"MULTISLIDE_TESTS not found in {MULTISLIDE_PROMPT_SOURCE}")


def compose_multislide_instruction(test: dict[str, Any]) -> str:
    """Compose one multi-slide harness row into a user-facing instruction."""
    lines = [
        f"# {test['category']}",
        "",
        f"Audience: {test['audience']}",
        f"Create {test['expected_slides']} slides.",
        "",
        "## Deck brief",
        test["deck_brief"],
        "",
        "## Visual direction",
        test["style_cues"],
        "",
        "## Slide-by-slide source content",
    ]
    for index, slide in enumerate(test["slides"], start=1):
        lines.extend([
            "",
            f"### Slide {index}: {slide['title']}",
            slide["content"],
            "",
            f"Visual cues: {slide['visual_cues']}",
        ])
    return "\n".join(lines)


def load_prompt_records(harness: str) -> list[dict[str, str]]:
    if harness == "standard":
        records = []
        for prompt in load_test_prompts():
            test_id, category, target_archetypes, user_instruction, _, expected_slides, notes = prompt
            records.append({
                "test_id": test_id,
                "category": category,
                "target_archetypes": target_archetypes,
                "user_instruction": user_instruction,
                "expected_slides": expected_slides,
                "notes": notes,
            })
        return records

    if harness == "multislide":
        return [
            {
                "test_id": test["test_id"],
                "category": test["category"],
                "target_archetypes": test["target_archetypes"],
                "user_instruction": compose_multislide_instruction(test),
                "expected_slides": test["expected_slides"],
                "notes": test["evaluation_focus"],
            }
            for test in load_multislide_tests()
        ]

    raise ValueError(f"Unknown harness: {harness}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--harness",
        choices=("standard", "multislide"),
        default="standard",
        help=(
            "Prompt harness to run. Use 'multislide' for deck-level tests with "
            "slide-by-slide source content."
        ),
    )
    parser.add_argument(
        "--run-prefix",
        default="eval_20260428",
        help="Prefix for run directories. Default: eval_20260428",
    )
    parser.add_argument(
        "--env-file",
        default=str(PROJECT_ROOT / ".env"),
        help="Path to .env containing Azure OpenAI settings.",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help=(
            "CSV manifest path for output PPTX paths. Defaults to "
            "runs/v3_eval_outputs.csv for standard and "
            "runs/v3_multislide_eval_outputs.csv for multislide."
        ),
    )
    parser.add_argument(
        "--only",
        nargs="*",
        help="Optional prompt IDs to run, e.g. TP-01 TP-02.",
    )
    parser.add_argument(
        "--max-build-attempts",
        type=int,
        default=3,
        help="Maximum builder attempts per prompt.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run prompts even if the manifest already has a successful row.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    prompts = load_prompt_records(args.harness)
    if args.only:
        wanted = set(args.only)
        prompts = [p for p in prompts if p["test_id"] in wanted]

    client = ResponsesClient.from_env(args.env_file)
    default_manifest = (
        DEFAULT_MULTISLIDE_MANIFEST
        if args.harness == "multislide"
        else DEFAULT_MANIFEST
    )
    manifest_path = Path(args.manifest or default_manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, dict[str, str]] = {}
    if manifest_path.exists():
        with manifest_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                existing[row["test_id"]] = row

    rows_by_id: dict[str, dict[str, str]] = dict(existing)
    for index, prompt in enumerate(prompts, start=1):
        test_id = prompt["test_id"]
        category = prompt["category"]
        target_archetypes = prompt["target_archetypes"]
        user_instruction = prompt["user_instruction"]
        expected_slides = prompt["expected_slides"]
        notes = prompt["notes"]
        run_id = f"{args.run_prefix}_{test_id.lower().replace('-', '')}"
        existing_row = existing.get(test_id)
        if (
            existing_row
            and existing_row.get("success") == "True"
            and not args.force
        ):
            print(f"[{index}/{len(prompts)}] {test_id}: already succeeded; skipping", flush=True)
            continue

        print(f"[{index}/{len(prompts)}] {test_id}: {category} -> {run_id}", flush=True)

        result = generate(
            user_instruction,
            client=client,
            run_id=run_id,
            max_build_attempts=args.max_build_attempts,
        )

        row = {
            "test_id": test_id,
            "harness": args.harness,
            "category": category,
            "target_archetypes": target_archetypes,
            "expected_slides": expected_slides,
            "run_id": result.run_id,
            "success": str(result.success),
            "stage": result.stage,
            "pptx_path": result.pptx_path,
            "run_dir": result.run_dir,
            "error": result.error.replace("\n", " | "),
            "notes": notes,
        }
        rows_by_id[test_id] = row
        print(json.dumps(row, ensure_ascii=True), flush=True)

        with manifest_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(row.keys()))
            writer.writeheader()
            writer.writerows(
                rows_by_id[p["test_id"]]
                for p in load_prompt_records(args.harness)
                if p["test_id"] in rows_by_id
            )

    print(f"Manifest: {manifest_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
