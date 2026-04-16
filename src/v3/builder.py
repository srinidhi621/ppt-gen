"""V3 Builder: generates Python build scripts from deck plans via LLM.

Takes a validated deck plan, selects matching examples, assembles a builder
prompt, calls the code-generation LLM, and returns executable Python code.

The builder retry loop is:
  1. Generate code via LLM
  2. Validate syntax (ast.parse)
  3. Run AST pre-scan (import/call allowlist)
  4. Execute in sandbox
  5. Run deterministic scanner
  6. On failure at any step, fold error context into next attempt
  7. Up to ``max_attempts`` total tries

Usage::

    from src.v3.builder import build_deck
    from src.v3.llm_client import ResponsesClient

    client = ResponsesClient.from_env()
    result = build_deck(client, deck_plan)
    # result is a BuildResult with .code, .pptx_path, .exec_result, etc.
"""

from __future__ import annotations

import ast
import json
import logging
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from src.sandbox import run_in_sandbox
from src.scan.scanner import scan_pptx
from src.v3.example_selector import (
    ExampleSnippet,
    format_examples_for_prompt,
    select_examples,
)
from src.v3.llm_client import (
    LLMError,
    LLMResponse,
    ResponsesClient,
    get_model_for_role,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_SYSTEM_PROMPT_PATH = _PROMPTS_DIR / "builder_system.txt"
_DS_PATH = _PROJECT_ROOT / "assets" / "template" / "design_system.json"


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class BuildAttempt:
    """Record of a single build attempt."""
    attempt: int
    code: str
    syntax_ok: bool
    ast_scan_ok: bool
    exec_success: bool
    scanner_pass: bool
    error: str = ""
    exec_result: Optional[dict] = None
    scanner_report: Optional[dict] = None


@dataclass
class BuildResult:
    """Final result of the builder pipeline."""
    success: bool
    code: str = ""
    pptx_path: str = ""
    attempts: list[BuildAttempt] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    error: str = ""


# ---------------------------------------------------------------------------
# Code extraction
# ---------------------------------------------------------------------------

_PYTHON_FENCE_RE = re.compile(
    r"```python\s*\n(.*?)\n```",
    re.DOTALL,
)
_ANY_FENCE_RE = re.compile(
    r"```(?:\w*)?\s*\n(.*?)\n```",
    re.DOTALL,
)


def _is_valid_python(code: str) -> bool:
    """Quick syntax check for candidate extraction."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def extract_code(text: str) -> str:
    """Extract Python code from LLM response, stripping markdown fences.

    Strategy (deterministic, most-specific first):
    1. Python-tagged fences — pick the longest parseable one.
    2. Any fenced block — pick the longest parseable one.
    3. Raw text if it parses as Python.
    4. Longest raw fenced block (even if not parseable, for error reporting).
    """
    # 1. Prefer explicitly python-tagged fences
    py_matches = _PYTHON_FENCE_RE.findall(text)
    if py_matches:
        parseable = [m.strip() for m in py_matches if _is_valid_python(m.strip())]
        if parseable:
            return max(parseable, key=len)
        # All python-tagged blocks have syntax errors — return the longest
        # so the builder retry loop gets the real error
        return max(py_matches, key=len).strip()

    # 2. Any fenced block
    all_matches = _ANY_FENCE_RE.findall(text)
    if all_matches:
        parseable = [m.strip() for m in all_matches if _is_valid_python(m.strip())]
        if parseable:
            return max(parseable, key=len)
        return max(all_matches, key=len).strip()

    # 3. Raw text
    return text.strip()


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

def _load_system_prompt() -> str:
    """Load the builder system prompt."""
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def _load_design_system_summary() -> str:
    """Load a compact design system summary for the prompt."""
    ds = json.loads(_DS_PATH.read_text(encoding="utf-8"))

    parts = ["## Design system summary\n"]

    # Colors
    colors = ds.get("colors", {})
    parts.append("### Colors")
    for name, hex_val in colors.items():
        parts.append(f"- `{name}`: {hex_val}")
    parts.append("")

    # Type scale
    ts = ds.get("type_scale", {})
    parts.append("### Type scale")
    for name, props in ts.items():
        parts.append(f"- `{name}`: {props.get('font', '?')} {props.get('size_pt', '?')}pt"
                     f"{' bold' if props.get('bold') else ''}")
    parts.append("")

    # Spacing
    sp = ds.get("spacing_scale", {})
    parts.append("### Spacing (EMU values)")
    for name, val in sp.items():
        clean_name = name.replace("_emu", "")
        parts.append(f"- `{clean_name}`: {val}")
    parts.append("")

    # Canvases
    canvases = ds.get("canvases", {})
    parts.append("### Canvases")
    for name, cfg in canvases.items():
        br = cfg.get("body_region", {})
        parts.append(f"- `{name}` (theme: {cfg.get('theme', '?')}): "
                     f"body_region top={br.get('top_emu', '?')}, "
                     f"left={br.get('left_emu', '?')}, "
                     f"w={br.get('width_emu', '?')}, "
                     f"h={br.get('height_emu', '?')}")
    parts.append("")

    return "\n".join(parts)


def assemble_user_message(
    deck_plan: dict,
    examples: list[ExampleSnippet],
    *,
    prior_code: str = "",
    error_context: str = "",
) -> str:
    """Assemble the builder user message from deck plan + examples + retry context."""
    parts: list[str] = []

    # Deck plan
    parts.append("## Deck plan\n")
    parts.append("```json")
    parts.append(json.dumps(deck_plan, indent=2))
    parts.append("```\n")

    # Design system summary
    parts.append(_load_design_system_summary())

    # Examples
    examples_text = format_examples_for_prompt(examples)
    if examples_text:
        parts.append(examples_text)

    # Instructions
    parts.append("## Instructions\n")
    parts.append(
        "Generate a complete `build_deck.py` that builds all slides in the deck plan. "
        "Use the exact text content from the plan — do not invent or modify wording. "
        "Follow the hard rules in the system prompt. "
        "The script will be executed with `sys.argv[1]` as the output path.\n"
    )
    parts.append(
        "IMPORTANT: The script runs from a temporary directory, so "
        "Path(__file__) will NOT point to the repo. Derive PROJECT_ROOT "
        "from an imported package (PYTHONPATH is pre-configured):\n"
        "```\n"
        "import src.ppt_runtime as _rt\n"
        "PROJECT_ROOT = Path(_rt.__file__).resolve().parents[2]\n"
        "```\n"
    )

    # Retry context
    if prior_code and error_context:
        parts.append("---\n")
        parts.append("## RETRY — your previous code failed\n")
        parts.append("### Your previous code:\n")
        parts.append(f"```python\n{prior_code}\n```\n")
        parts.append(f"### Error:\n{error_context}\n")
        parts.append(
            "Fix the errors above and return the complete corrected script. "
            "Do not apologize — just output the fixed code.\n"
        )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def check_syntax(code: str) -> tuple[bool, str]:
    """Parse code as Python AST. Returns (ok, error_message)."""
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as exc:
        return False, f"SyntaxError at line {exc.lineno}: {exc.msg}"


# ---------------------------------------------------------------------------
# Build pipeline
# ---------------------------------------------------------------------------

def build_deck(
    client: ResponsesClient,
    deck_plan: dict,
    *,
    max_attempts: int = 3,
    examples_dir: Path | None = None,
    work_dir: Path | None = None,
    cleanup: bool = True,
) -> BuildResult:
    """Generate and execute a build script from a deck plan.

    This is the main builder entry point. It:
    1. Selects matching examples
    2. Assembles the prompt
    3. Calls the LLM to generate code
    4. Validates, executes in sandbox, and scans
    5. Retries on failure with error context

    Parameters
    ----------
    client : ResponsesClient
        The LLM client.
    deck_plan : dict
        Validated deck plan from the planner.
    max_attempts : int
        Total attempts (including initial).
    examples_dir : Path, optional
        Override examples directory (for testing).
    work_dir : Path, optional
        Working directory for build artifacts. Created if None.
    cleanup : bool
        Whether to clean up the work directory on success.

    Returns
    -------
    BuildResult
        Contains the final code, PPTX path, and attempt history.
    """
    model = get_model_for_role("builder")
    system_prompt = _load_system_prompt()
    examples = select_examples(deck_plan, max_examples=3, examples_dir=examples_dir)

    result = BuildResult(success=False)

    # Create working directory
    managed_work_dir = work_dir is None
    if managed_work_dir:
        work_dir = Path(tempfile.mkdtemp(prefix="ppt_build_"))
    work_dir.mkdir(parents=True, exist_ok=True)

    prior_code = ""
    error_context = ""

    for attempt_num in range(1, max_attempts + 1):
        logger.info("Builder attempt %d/%d", attempt_num, max_attempts)

        # Assemble prompt
        user_msg = assemble_user_message(
            deck_plan, examples,
            prior_code=prior_code,
            error_context=error_context,
        )

        # Call LLM
        try:
            llm_result: LLMResponse = client.generate_code(
                model,
                system_prompt,
                user_msg,
                caller="builder",
                temperature=0.2,
                max_output_tokens=16384,
            )
        except (LLMError, ValueError) as exc:
            logger.error("LLM call failed: %s", exc)
            result.error = f"LLM call failed: {exc}"
            break

        result.total_input_tokens += llm_result.usage.input_tokens
        result.total_output_tokens += llm_result.usage.output_tokens

        code = extract_code(llm_result.text)
        attempt = BuildAttempt(
            attempt=attempt_num,
            code=code,
            syntax_ok=False,
            ast_scan_ok=False,
            exec_success=False,
            scanner_pass=False,
        )

        # Step 1: Syntax check
        syntax_ok, syntax_err = check_syntax(code)
        attempt.syntax_ok = syntax_ok
        if not syntax_ok:
            attempt.error = syntax_err
            result.attempts.append(attempt)
            prior_code = code
            error_context = f"Python syntax error:\n{syntax_err}"
            logger.warning("Attempt %d: syntax error: %s", attempt_num, syntax_err)
            continue

        # Step 2: Write script and execute in sandbox
        attempt_dir = work_dir / f"attempt_{attempt_num:02d}"
        # Clean any stale attempt dir to prevent misclassifying old output
        if attempt_dir.exists():
            shutil.rmtree(attempt_dir)
        attempt_dir.mkdir(parents=True, exist_ok=True)
        script_path = attempt_dir / "build_deck.py"
        expected_output = attempt_dir / "deck.pptx"
        script_path.write_text(code, encoding="utf-8")

        # Set up environment so the script can import from the project.
        # NOTE: This broadens the sandbox execution context (the subprocess
        # can traverse PROJECT_ROOT via PYTHONPATH imports). The AST scanner
        # blocks os.environ access and dangerous imports, but path-write
        # restriction remains best-effort until OS-level isolation (SLICE-015+).
        extra_env = {
            "PYTHONPATH": str(_PROJECT_ROOT),
        }

        exec_result = run_in_sandbox(
            script_path,
            script_args=[str(expected_output)],
            attempt_dir=attempt_dir,
            extra_env=extra_env,
            write_report=True,
        )
        attempt.ast_scan_ok = exec_result.ast_scan_ok
        attempt.exec_success = exec_result.success
        attempt.exec_result = exec_result.to_report()

        if not exec_result.ast_scan_ok:
            attempt.error = f"AST pre-scan rejected: {exec_result.ast_violations}"
            result.attempts.append(attempt)
            prior_code = code
            violations = "\n".join(f"- {v}" for v in exec_result.ast_violations)
            error_context = (
                f"AST pre-scan rejected the script with these violations:\n{violations}\n\n"
                "Fix the disallowed imports/calls and try again."
            )
            logger.warning("Attempt %d: AST scan failed", attempt_num)
            continue

        if not exec_result.success:
            err = exec_result.error or "Unknown execution error"
            tb = exec_result.traceback_str or exec_result.stderr or ""
            attempt.error = err
            result.attempts.append(attempt)
            prior_code = code
            error_context = f"Execution failed:\n{err}"
            if tb:
                # Trim traceback to last 2000 chars
                error_context += f"\n\nTraceback:\n{tb[-2000:]}"
            logger.warning("Attempt %d: execution failed: %s", attempt_num, err)
            continue

        # Validate the exact expected output path — not just any .pptx
        if not expected_output.exists():
            attempt.exec_success = False
            attempt.error = (
                "Script exited successfully but did not write to the expected "
                f"output path: {expected_output.name}"
            )
            result.attempts.append(attempt)
            prior_code = code
            error_context = (
                f"The script exited successfully but did not produce the expected "
                f"output file at sys.argv[1] ({expected_output.name}). "
                f"Make sure the script writes to Path(sys.argv[1])."
            )
            logger.warning("Attempt %d: expected output missing", attempt_num)
            continue

        pptx_path = str(expected_output)

        # Step 3: Run scanner on output PPTX
        try:
            scanner_report = scan_pptx(
                pptx_path, str(_DS_PATH), deck_plan=deck_plan,
            )
            attempt.scanner_report = scanner_report
            blocking = scanner_report.get("blocking_count", 0)
            if blocking > 0:
                attempt.error = f"Scanner found {blocking} BLOCKING finding(s)"
                result.attempts.append(attempt)
                prior_code = code
                findings_text = _format_scanner_findings(scanner_report)
                error_context = (
                    f"The PPTX was built successfully but the scanner found "
                    f"{blocking} BLOCKING finding(s):\n{findings_text}\n\n"
                    "Fix the issues and regenerate the complete script."
                )
                logger.warning("Attempt %d: scanner found %d blocking", attempt_num, blocking)
                continue
            attempt.scanner_pass = True
        except Exception as exc:
            attempt.error = f"Scanner crashed: {exc}"
            result.attempts.append(attempt)
            prior_code = code
            error_context = (
                f"The post-build scanner crashed while analyzing the PPTX:\n"
                f"{type(exc).__name__}: {exc}\n\n"
                "This likely indicates a malformed PPTX. Regenerate the script."
            )
            logger.warning("Attempt %d: scanner exception: %s", attempt_num, exc)
            continue

        # SUCCESS
        result.success = True
        result.code = code
        result.pptx_path = pptx_path
        result.attempts.append(attempt)
        logger.info(
            "Builder succeeded on attempt %d/%d (%d in, %d out tokens)",
            attempt_num, max_attempts,
            result.total_input_tokens, result.total_output_tokens,
        )
        break
    else:
        # All attempts exhausted — include last error for diagnostics
        last_err = result.attempts[-1].error if result.attempts else "unknown"
        result.error = f"All {max_attempts} build attempts failed; last error: {last_err}"
        logger.error("Builder exhausted %d attempts", max_attempts)

    return result


def _format_scanner_findings(report: dict) -> str:
    """Format scanner findings for the retry prompt."""
    findings = report.get("findings", [])
    blocking = [f for f in findings if f.get("severity") == "BLOCKING"]
    if not blocking:
        return "No details available."
    lines = []
    for f in blocking[:10]:  # Cap at 10 findings
        lines.append(
            f"- [{f.get('check_id', '?')}] {f.get('message', 'No message')} "
            f"(slide {f.get('slide_index', '?')})"
        )
    if len(blocking) > 10:
        lines.append(f"... and {len(blocking) - 10} more")
    return "\n".join(lines)
