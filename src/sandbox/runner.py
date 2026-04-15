"""Sandbox subprocess runner for LLM-generated builder scripts.

Executes a `build_deck.py` in an isolated subprocess with:
- resource limits (CPU time, memory) via resource.setrlimit
- wall-clock timeout
- restricted environment variables
- restricted working directory (the attempt directory)
- stdout / stderr / exit-code / traceback capture

Produces a `build_exec_report.json` in the attempt directory.

Spec reference: SPEC-v3.md §2.5, §4.5
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from .ast_scanner import ScanResult, scan_ast

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT_S = 60        # wall-clock seconds
DEFAULT_CPU_LIMIT_S = 30      # CPU seconds (via RLIMIT_CPU)
DEFAULT_MEMORY_MB = 512       # resident memory cap in MB

# Minimal environment passed to the subprocess.
_BASE_ENV_KEYS = {"PATH", "HOME", "LANG", "LC_ALL", "VIRTUAL_ENV", "PYTHONPATH"}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class ExecResult:
    """Result of a single sandbox execution attempt."""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_s: float
    ast_scan_ok: bool
    ast_violations: list[str] = field(default_factory=list)
    pptx_path: Optional[str] = None
    error: Optional[str] = None
    traceback_str: Optional[str] = None

    def to_report(self) -> dict:
        """Convert to build_exec_report-compatible dict."""
        report: dict = {
            "success": self.success,
            "slides_built": 0,  # filled by caller if available
            "pptx_path": self.pptx_path or "",
            "build_time_seconds": round(self.duration_s, 3),
            "ast_scan_ok": self.ast_scan_ok,
        }
        if self.ast_violations:
            report["ast_violations"] = self.ast_violations
        if self.error:
            report["errors"] = [{
                "slide_index": -1,
                "error": self.error,
                "traceback": self.traceback_str or "",
            }]
        if self.stdout:
            report["stdout"] = self.stdout
        if self.stderr:
            report["stderr"] = self.stderr
        return report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_env(extra: Optional[dict[str, str]] = None) -> dict[str, str]:
    """Build a minimal environment for the sandbox subprocess."""
    env: dict[str, str] = {}
    for key in _BASE_ENV_KEYS:
        val = os.environ.get(key)
        if val is not None:
            env[key] = val
    if extra:
        env.update(extra)
    return env


def _rlimit_preexec(cpu_s: int, mem_mb: int):
    """Return a preexec_fn that sets resource limits (Unix only)."""
    def _set_limits():
        import resource
        # CPU time limit
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))
        # Address space limit (virtual memory)
        mem_bytes = mem_mb * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except (ValueError, OSError):
            # macOS may not support RLIMIT_AS; fall back to RLIMIT_RSS
            try:
                resource.setrlimit(resource.RLIMIT_RSS, (mem_bytes, mem_bytes))
            except (ValueError, OSError, AttributeError):
                pass  # best-effort on macOS
    return _set_limits


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_in_sandbox(
    script_path: Path,
    *,
    attempt_dir: Optional[Path] = None,
    python: Optional[str] = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    cpu_limit_s: int = DEFAULT_CPU_LIMIT_S,
    memory_mb: int = DEFAULT_MEMORY_MB,
    extra_env: Optional[dict[str, str]] = None,
    skip_ast_scan: bool = False,
    write_report: bool = True,
) -> ExecResult:
    """Execute a builder script in a sandboxed subprocess.

    Parameters
    ----------
    script_path : Path
        Path to the build_deck.py to execute.
    attempt_dir : Path, optional
        Working directory for the subprocess. Defaults to script_path.parent.
    python : str, optional
        Python interpreter path. Defaults to sys.executable.
    timeout_s : int
        Wall-clock timeout in seconds.
    cpu_limit_s : int
        CPU time limit in seconds (via RLIMIT_CPU on Unix).
    memory_mb : int
        Memory limit in MB (via RLIMIT_AS/RLIMIT_RSS on Unix).
    extra_env : dict, optional
        Extra environment variables to pass.
    skip_ast_scan : bool
        If True, skip the AST pre-scan (for testing only).
    write_report : bool
        If True, write build_exec_report.json to attempt_dir.

    Returns
    -------
    ExecResult
        Execution outcome with captured output and metadata.
    """
    script_path = Path(script_path).resolve()
    attempt_dir = Path(attempt_dir or script_path.parent).resolve()
    python = python or sys.executable

    # -----------------------------------------------------------------------
    # Step 1: AST pre-scan
    # -----------------------------------------------------------------------
    if not skip_ast_scan:
        scan: ScanResult = scan_ast(script_path)
        if not scan.ok:
            result = ExecResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                duration_s=0.0,
                ast_scan_ok=False,
                ast_violations=[str(v) for v in scan.violations],
                error=f"AST pre-scan rejected script: {len(scan.violations)} violation(s)",
            )
            if write_report:
                _write_report(result, attempt_dir)
            return result

    # -----------------------------------------------------------------------
    # Step 2: Launch subprocess
    # -----------------------------------------------------------------------
    env = _build_env(extra_env)

    # Build preexec_fn for resource limits (Unix only)
    preexec = None
    if platform.system() != "Windows":
        preexec = _rlimit_preexec(cpu_limit_s, memory_mb)

    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            [python, str(script_path)],
            cwd=str(attempt_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            preexec_fn=preexec,
        )
        duration = time.monotonic() - t0
        exit_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr

    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - t0
        result = ExecResult(
            success=False,
            exit_code=-1,
            stdout=exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            stderr=exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
            duration_s=duration,
            ast_scan_ok=True,
            error=f"Script timed out after {timeout_s}s",
        )
        if write_report:
            _write_report(result, attempt_dir)
        return result

    except Exception as exc:
        duration = time.monotonic() - t0
        result = ExecResult(
            success=False,
            exit_code=-1,
            stdout="",
            stderr="",
            duration_s=duration,
            ast_scan_ok=True,
            error=f"Subprocess launch failed: {exc}",
            traceback_str=traceback.format_exc(),
        )
        if write_report:
            _write_report(result, attempt_dir)
        return result

    # -----------------------------------------------------------------------
    # Step 3: Evaluate outcome
    # -----------------------------------------------------------------------
    success = exit_code == 0
    error_msg = None
    tb_str = None

    if not success:
        error_msg = f"Script exited with code {exit_code}"
        # Try to extract traceback from stderr
        if stderr:
            tb_lines = []
            in_tb = False
            for line in stderr.splitlines():
                if line.startswith("Traceback"):
                    in_tb = True
                if in_tb:
                    tb_lines.append(line)
            tb_str = "\n".join(tb_lines) if tb_lines else stderr[-2000:]

    # Check for expected output PPTX
    pptx_path = None
    for candidate in [
        attempt_dir / "deck.pptx",
        attempt_dir / "output.pptx",
    ]:
        if candidate.exists():
            pptx_path = str(candidate)
            break

    # Also scan attempt_dir for any .pptx file
    if pptx_path is None:
        pptx_files = list(attempt_dir.glob("*.pptx"))
        if pptx_files:
            pptx_path = str(pptx_files[0])

    # If script succeeded but no PPTX found, mark as failure
    if success and pptx_path is None:
        success = False
        error_msg = "Script exited successfully but no .pptx file was produced"

    result = ExecResult(
        success=success,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_s=duration,
        ast_scan_ok=True,
        pptx_path=pptx_path,
        error=error_msg,
        traceback_str=tb_str,
    )

    if write_report:
        _write_report(result, attempt_dir)
    return result


def _write_report(result: ExecResult, attempt_dir: Path) -> Path:
    """Write build_exec_report.json to the attempt directory."""
    report_path = attempt_dir / "build_exec_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = result.to_report()
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path
