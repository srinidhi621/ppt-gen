"""Select few-shot examples for the builder prompt.

Given a deck plan, picks 1–3 example ``build.py`` files from the
``examples/`` library to inject as context into the builder prompt.
Prefers one example per unique archetype; caps at ``max_examples``
to stay within token budget.

Usage::

    from src.v3.example_selector import select_examples

    snippets = select_examples(deck_plan, max_examples=3)
    # snippets is a list of ExampleSnippet(archetype, name, code)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_EXAMPLES_DIR = Path(__file__).resolve().parent.parent.parent / "examples"


@dataclass(frozen=True)
class ExampleSnippet:
    """A single example ready for prompt injection."""
    archetype: str
    name: str
    code: str


def _discover_examples(examples_dir: Path | None = None) -> dict[str, list[Path]]:
    """Scan the examples directory and return {archetype: [example_dirs]}.

    Each example directory must contain ``build.py`` and ``metadata.json``.
    """
    base = examples_dir or _EXAMPLES_DIR
    result: dict[str, list[Path]] = {}

    if not base.is_dir():
        logger.warning("Examples directory not found: %s", base)
        return result

    for archetype_dir in sorted(base.iterdir()):
        if not archetype_dir.is_dir() or archetype_dir.name.startswith(("_", ".")):
            continue
        for example_dir in sorted(archetype_dir.iterdir()):
            if not example_dir.is_dir():
                continue
            build_py = example_dir / "build.py"
            metadata = example_dir / "metadata.json"
            if build_py.exists() and metadata.exists():
                # Read archetype from metadata (authoritative)
                try:
                    meta = json.loads(metadata.read_text(encoding="utf-8"))
                    arch = meta.get("archetype", archetype_dir.name)
                except (json.JSONDecodeError, OSError):
                    arch = archetype_dir.name
                result.setdefault(arch, []).append(example_dir)

    return result


def select_examples(
    deck_plan: dict,
    *,
    max_examples: int = 3,
    examples_dir: Path | None = None,
) -> list[ExampleSnippet]:
    """Select examples matching the archetypes in *deck_plan*.

    Strategy:
    1. Collect unique archetypes from the deck plan's slides.
    2. For each archetype, pick the first available example.
    3. Cap at *max_examples* (prefer diversity over duplicates).
    4. If fewer archetypes than max_examples, fill with additional
       examples from archetypes that have multiple options.

    Returns a list of ExampleSnippet with the source code.
    """
    library = _discover_examples(examples_dir)

    # Collect unique archetypes in plan order
    seen: set[str] = set()
    plan_archetypes: list[str] = []
    for slide in deck_plan.get("slides", []):
        arch = slide.get("archetype", "")
        if arch and arch not in seen:
            seen.add(arch)
            plan_archetypes.append(arch)

    selected: list[ExampleSnippet] = []
    used_dirs: set[Path] = set()

    # Phase 1: one example per unique archetype
    for arch in plan_archetypes:
        if len(selected) >= max_examples:
            break
        candidates = library.get(arch, [])
        for cdir in candidates:
            if cdir not in used_dirs:
                snippet = _load_snippet(cdir, arch)
                if snippet:
                    selected.append(snippet)
                    used_dirs.add(cdir)
                    break

    # Phase 2: fill remaining slots with second examples (diversity)
    if len(selected) < max_examples:
        for arch in plan_archetypes:
            if len(selected) >= max_examples:
                break
            candidates = library.get(arch, [])
            for cdir in candidates:
                if cdir not in used_dirs:
                    snippet = _load_snippet(cdir, arch)
                    if snippet:
                        selected.append(snippet)
                        used_dirs.add(cdir)
                        break

    # Phase 3: if still short, pick from any available archetype
    if len(selected) < max_examples:
        for arch, dirs in library.items():
            if len(selected) >= max_examples:
                break
            for cdir in dirs:
                if cdir not in used_dirs:
                    snippet = _load_snippet(cdir, arch)
                    if snippet:
                        selected.append(snippet)
                        used_dirs.add(cdir)
                        break

    logger.info(
        "Selected %d examples for %d plan archetypes: %s",
        len(selected),
        len(plan_archetypes),
        [s.name for s in selected],
    )
    return selected


def _load_snippet(example_dir: Path, archetype: str) -> ExampleSnippet | None:
    """Load an ExampleSnippet from an example directory."""
    build_py = example_dir / "build.py"
    try:
        code = build_py.read_text(encoding="utf-8")
        name = f"{archetype}/{example_dir.name}"
        return ExampleSnippet(archetype=archetype, name=name, code=code)
    except OSError:
        logger.warning("Could not read %s", build_py)
        return None


def format_examples_for_prompt(snippets: list[ExampleSnippet]) -> str:
    """Format selected examples into a string for the builder prompt."""
    if not snippets:
        return ""

    parts = ["## Reference examples\n"]
    for i, s in enumerate(snippets, 1):
        parts.append(f"### Example {i}: {s.name} (archetype: {s.archetype})\n")
        parts.append(f"```python\n{s.code}\n```\n")
    return "\n".join(parts)
