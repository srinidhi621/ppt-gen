"""Worker process for sandboxed builder code execution."""

from __future__ import annotations

import argparse
import builtins
import json
import os
import socket
import sys
import traceback
from pathlib import Path
from typing import Any, Dict


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _disable_network() -> None:
    def _blocked(*args, **kwargs):
        raise RuntimeError("Network access is disabled in builder sandbox.")

    socket.create_connection = _blocked  # type: ignore[assignment]
    socket.getaddrinfo = _blocked  # type: ignore[assignment]
    socket.socket.connect = _blocked  # type: ignore[assignment]
    socket.socket.connect_ex = _blocked  # type: ignore[assignment]


def _install_write_guard(writable_root: Path) -> None:
    writable_root = writable_root.resolve()
    original_open = builtins.open

    def _guarded_open(file, mode="r", *args, **kwargs):
        path_obj = Path(file)
        resolved = (Path.cwd() / path_obj).resolve() if not path_obj.is_absolute() else path_obj.resolve()
        writes = any(flag in mode for flag in ("w", "a", "x", "+"))
        if writes and writable_root not in resolved.parents and resolved != writable_root:
            raise PermissionError(f"Write denied outside sandbox root: {resolved}")
        return original_open(file, mode, *args, **kwargs)

    builtins.open = _guarded_open  # type: ignore[assignment]


def run_worker(code_path: Path, builder_input_path: Path, writable_root: Path, report_path: Path) -> int:
    builder_input = json.loads(builder_input_path.read_text(encoding="utf-8"))

    _disable_network()
    _install_write_guard(writable_root)

    exec_globals: Dict[str, Any] = {
        "__name__": "__main__",
        "__file__": str(code_path),
        "BUILDER_INPUT": builder_input,
    }
    sys.argv = [str(code_path), str(builder_input.get("output_pptx", ""))]

    try:
        code = code_path.read_text(encoding="utf-8")
        compiled = compile(code, str(code_path), "exec")
        exec(compiled, exec_globals, exec_globals)
    except Exception as exc:  # pragma: no cover - exercised via runtime tests
        _write_json(
            report_path,
            {
                "status": "failed",
                "failure_type": "runtime_error",
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        return 1

    output_pptx = Path(builder_input.get("output_pptx", "")).expanduser()
    if not output_pptx.exists():
        _write_json(
            report_path,
            {
                "status": "failed",
                "failure_type": "missing_output",
                "message": f"Expected output_pptx was not created: {output_pptx}",
                "traceback": "",
            },
        )
        return 2

    _write_json(
        report_path,
        {
            "status": "success",
            "failure_type": None,
            "message": "Builder execution completed.",
            "traceback": "",
        },
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run disposable builder code in guarded worker")
    parser.add_argument("--code", required=True, type=str)
    parser.add_argument("--builder-input", required=True, type=str)
    parser.add_argument("--writable-root", required=True, type=str)
    parser.add_argument("--report-path", required=True, type=str)
    args = parser.parse_args()

    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"

    return run_worker(
        code_path=Path(args.code),
        builder_input_path=Path(args.builder_input),
        writable_root=Path(args.writable_root),
        report_path=Path(args.report_path),
    )


if __name__ == "__main__":
    raise SystemExit(main())
