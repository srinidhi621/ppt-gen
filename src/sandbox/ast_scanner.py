"""AST pre-scan for LLM-generated builder scripts.

Walks the module AST to reject disallowed imports and dangerous calls
before the script is executed in the sandbox subprocess.

Spec reference: SPEC-v3.md §2.5, §4.5
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

# ---------------------------------------------------------------------------
# Allowlists
# ---------------------------------------------------------------------------

# Top-level modules that builder scripts may import.
ALLOWED_MODULES: set[str] = {
    "ppt_runtime",
    "src.ppt_runtime",
    "pptx",
    "sys",
    "pathlib",
    "os.path",
    "json",
    "math",
    "dataclasses",
    "enum",
    "typing",
    "collections",
}

# Module prefixes — any import starting with one of these is allowed.
ALLOWED_PREFIXES: tuple[str, ...] = (
    "ppt_runtime.",
    "src.ppt_runtime.",
    "pptx.",
)

# Builtin names / attribute calls that are always blocked.
BLOCKED_BUILTINS: set[str] = {
    "__import__",
    "eval",
    "exec",
    "compile",
    "globals",
    "locals",
    "getattr",
    "setattr",
    "delattr",
    "breakpoint",
    "input",
}

# os.* attributes that ARE allowed (everything else under os is blocked).
ALLOWED_OS_ATTRS: set[str] = {
    "path",
}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class ScanViolation:
    """A single AST violation found in the script."""
    line: int
    col: int
    rule: str
    detail: str

    def __str__(self) -> str:
        return f"L{self.line}:{self.col} [{self.rule}] {self.detail}"


@dataclass
class ScanResult:
    """Outcome of an AST pre-scan."""
    ok: bool
    violations: list[ScanViolation] = field(default_factory=list)

    def summary(self) -> str:
        if self.ok:
            return "AST scan passed"
        lines = [f"AST scan failed with {len(self.violations)} violation(s):"]
        for v in self.violations:
            lines.append(f"  {v}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def _is_allowed_module(name: str) -> bool:
    """Check if a module name is on the allowlist."""
    if name in ALLOWED_MODULES:
        return True
    return any(name.startswith(p) for p in ALLOWED_PREFIXES)


class _ASTChecker(ast.NodeVisitor):
    """Visitor that collects violations from a parsed AST."""

    def __init__(self) -> None:
        self.violations: list[ScanViolation] = []

    def _add(self, node: ast.AST, rule: str, detail: str) -> None:
        self.violations.append(ScanViolation(
            line=getattr(node, "lineno", 0),
            col=getattr(node, "col_offset", 0),
            rule=rule,
            detail=detail,
        ))

    # -- Import statements ---------------------------------------------------

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if not _is_allowed_module(alias.name):
                self._add(node, "blocked-import",
                          f"import {alias.name!r} is not allowed")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if not _is_allowed_module(module):
            self._add(node, "blocked-import",
                      f"from {module!r} import ... is not allowed")
        self.generic_visit(node)

    # -- Dangerous builtins --------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func

        # Direct name call: eval(...), exec(...), __import__(...)
        if isinstance(func, ast.Name) and func.id in BLOCKED_BUILTINS:
            self._add(node, "blocked-builtin",
                      f"call to {func.id}() is not allowed")

        # open() — blocked (builder scripts should not open arbitrary files)
        if isinstance(func, ast.Name) and func.id == "open":
            self._add(node, "blocked-open",
                      "call to open() is not allowed in builder scripts")

        # os.<something>() where something is not in ALLOWED_OS_ATTRS
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name) and func.value.id == "os":
                if func.attr not in ALLOWED_OS_ATTRS:
                    self._add(node, "blocked-os",
                              f"os.{func.attr}() is not allowed; "
                              f"only os.path is permitted")

        self.generic_visit(node)

    # -- os.* attribute access (not just calls) ------------------------------

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name) and node.value.id == "os":
            if node.attr not in ALLOWED_OS_ATTRS:
                # Skip if this is already handled as a Call
                # (visit_Call catches os.xxx() calls)
                parent = getattr(node, "_parent", None)
                if not isinstance(parent, ast.Call) or parent.func is not node:
                    self._add(node, "blocked-os",
                              f"os.{node.attr} access is not allowed; "
                              f"only os.path is permitted")
        self.generic_visit(node)


def _annotate_parents(tree: ast.AST) -> None:
    """Add _parent attribute to every node in the tree."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child._parent = node  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_ast(source: Union[str, Path]) -> ScanResult:
    """Scan a Python source file or string for disallowed constructs.

    Parameters
    ----------
    source : str or Path
        If a Path (or string path to an existing file), the file is read
        and parsed. Otherwise the string is treated as Python source code.

    Returns
    -------
    ScanResult
        `.ok` is True if no violations found; `.violations` lists all issues.
    """
    # Determine if source is a file path or raw code
    if isinstance(source, Path):
        code = source.read_text(encoding="utf-8")
        filename = str(source)
    elif isinstance(source, str) and not source.strip().startswith(("#", "\"", "'", "import", "from", "def", "class", "\n")) and Path(source).is_file():
        code = Path(source).read_text(encoding="utf-8")
        filename = source
    else:
        code = source
        filename = "<string>"

    # Parse
    try:
        tree = ast.parse(code, filename=filename)
    except SyntaxError as exc:
        return ScanResult(ok=False, violations=[
            ScanViolation(
                line=exc.lineno or 0,
                col=exc.offset or 0,
                rule="syntax-error",
                detail=str(exc),
            )
        ])

    # Annotate parent pointers (for dedup in Attribute vs Call)
    _annotate_parents(tree)

    # Walk
    checker = _ASTChecker()
    checker.visit(tree)

    return ScanResult(
        ok=len(checker.violations) == 0,
        violations=checker.violations,
    )
