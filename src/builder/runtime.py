"""Sandboxed execution harness for disposable builder code."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from ..logging_utils import log_event

DEFAULT_IMPORT_ALLOWLIST = {
    "dataclasses",
    "json",
    "math",
    "pathlib",
    "pptx",
    "sys",
    "typing",
}

RETRYABLE_FAILURE_TYPES = {"syntax_error", "import_error", "runtime_error", "timeout"}


@dataclass
class AttemptPreparation:
    attempt_dir: Path
    code_path: Path
    output_pptx: Path
    worker_input_path: Path


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _extract_import_roots(code: str) -> List[str]:
    tree = ast.parse(code)
    roots: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.append(node.module.split(".")[0])
    return sorted(set(roots))


def _prepare_attempt(
    *,
    run_dir: Path,
    attempt_index: int,
    code: str,
    builder_input: Dict[str, Any],
    code_filename: str,
) -> AttemptPreparation:
    attempt_dir = run_dir / "build_attempts" / f"attempt_{attempt_index:02d}"
    attempt_dir.mkdir(parents=True, exist_ok=True)

    code_path = attempt_dir / code_filename
    code_path.write_text(code, encoding="utf-8")

    output_pptx = attempt_dir / "deck_attempt.pptx"
    worker_input = dict(builder_input)
    worker_input["output_pptx"] = str(output_pptx)
    worker_input_path = attempt_dir / "builder_input_v1.json"
    _write_json(worker_input_path, worker_input)

    return AttemptPreparation(
        attempt_dir=attempt_dir,
        code_path=code_path,
        output_pptx=output_pptx,
        worker_input_path=worker_input_path,
    )


def execute_builder_harness(
    *,
    run_dir: Path,
    builder_input: Dict[str, Any],
    candidate_codes: List[str],
    import_allowlist: set[str] | None = None,
    timeout_seconds: int = 60,
    max_attempts: int = 3,
    log_path: Path | None = None,
) -> Dict[str, Any]:
    """Execute disposable builder code with deterministic retries and artifacts."""
    run_dir.mkdir(parents=True, exist_ok=True)
    allowlist = set(import_allowlist or DEFAULT_IMPORT_ALLOWLIST)
    attempts_payload: List[Dict[str, Any]] = []
    failure_reason = "unknown"

    for idx in range(1, max_attempts + 1):
        code = candidate_codes[min(idx - 1, len(candidate_codes) - 1)]
        preparation = _prepare_attempt(
            run_dir=run_dir,
            attempt_index=idx,
            code=code,
            builder_input=builder_input,
            code_filename=f"build_deck_v{idx}.py",
        )

        attempt_payload: Dict[str, Any] = {
            "attempt": idx,
            "attempt_dir": str(preparation.attempt_dir),
            "code_path": str(preparation.code_path),
            "worker_input_path": str(preparation.worker_input_path),
            "output_pptx": str(preparation.output_pptx),
        }

        try:
            imports = _extract_import_roots(code)
            forbidden = sorted(root for root in imports if root not in allowlist)
            attempt_payload["imports"] = imports
            if forbidden:
                failure_reason = "import_error"
                attempt_payload.update(
                    {
                        "status": "failed",
                        "failure_type": "import_error",
                        "forbidden_imports": forbidden,
                        "message": f"Forbidden imports: {', '.join(forbidden)}",
                    }
                )
                _write_json(preparation.attempt_dir / "build_exec_report_v1.json", attempt_payload)
                attempts_payload.append(attempt_payload)
                if log_path:
                    log_event(log_path, "BUILD_EXEC_ATTEMPT_FAILED", attempt_payload)
                if idx >= max_attempts:
                    break
                continue
        except SyntaxError as exc:
            failure_reason = "syntax_error"
            attempt_payload.update(
                {
                    "status": "failed",
                    "failure_type": "syntax_error",
                    "message": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
            _write_json(preparation.attempt_dir / "build_exec_report_v1.json", attempt_payload)
            attempts_payload.append(attempt_payload)
            if log_path:
                log_event(log_path, "BUILD_EXEC_ATTEMPT_FAILED", attempt_payload)
            if idx >= max_attempts:
                break
            continue

        cmd = [
            sys.executable,
            "-m",
            "src.builder.sandbox_worker",
            "--code",
            str(preparation.code_path),
            "--builder-input",
            str(preparation.worker_input_path),
            "--writable-root",
            str(preparation.attempt_dir),
            "--report-path",
            str(preparation.attempt_dir / "worker_exec_report.json"),
        ]
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(Path(__file__).resolve().parents[2]),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            failure_reason = "timeout"
            timeout_payload = {
                **attempt_payload,
                "status": "failed",
                "failure_type": "timeout",
                "message": f"Builder execution exceeded {timeout_seconds} seconds.",
                "stdout_path": "",
                "stderr_path": "",
                "traceback": str(exc),
            }
            _write_json(preparation.attempt_dir / "build_exec_report_v1.json", timeout_payload)
            attempts_payload.append(timeout_payload)
            if log_path:
                log_event(log_path, "BUILD_EXEC_ATTEMPT_FAILED", timeout_payload)
            if idx >= max_attempts:
                break
            continue

        stdout_path = preparation.attempt_dir / "stdout.txt"
        stderr_path = preparation.attempt_dir / "stderr.txt"
        stdout_path.write_text(proc.stdout or "", encoding="utf-8")
        stderr_path.write_text(proc.stderr or "", encoding="utf-8")

        worker_report_path = preparation.attempt_dir / "worker_exec_report.json"
        worker_report = json.loads(worker_report_path.read_text(encoding="utf-8"))
        attempt_payload.update(
            {
                "status": worker_report.get("status", "failed"),
                "failure_type": worker_report.get("failure_type"),
                "message": worker_report.get("message"),
                "traceback": worker_report.get("traceback"),
                "stdout_path": str(stdout_path),
                "stderr_path": str(stderr_path),
                "exit_code": proc.returncode,
                "output_exists": preparation.output_pptx.exists(),
            }
        )

        _write_json(preparation.attempt_dir / "build_exec_report_v1.json", attempt_payload)
        attempts_payload.append(attempt_payload)

        if attempt_payload["status"] == "success" and preparation.output_pptx.exists():
            summary = {
                "status": "success",
                "attempt_count": idx,
                "output_pptx": str(preparation.output_pptx),
                "attempts": attempts_payload,
            }
            _write_json(run_dir / "build_exec_report_v1.json", summary)
            if log_path:
                log_event(log_path, "BUILD_EXEC_V1_DONE", summary)
            return summary

        failure_reason = attempt_payload.get("failure_type") or "runtime_error"
        if log_path:
            log_event(log_path, "BUILD_EXEC_ATTEMPT_FAILED", attempt_payload)
        if idx >= max_attempts or failure_reason not in RETRYABLE_FAILURE_TYPES:
            break

    summary = {
        "status": "failed",
        "attempt_count": len(attempts_payload),
        "failure_type": failure_reason,
        "attempts": attempts_payload,
    }
    _write_json(run_dir / "build_exec_report_v1.json", summary)
    if log_path:
        log_event(log_path, "RUN_FAILED_BUILD", summary)
    return summary
