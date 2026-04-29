"""Select few-shot examples for the builder prompt.

Given a deck plan, picks 1–3 example ``build.py`` files from the
``examples/`` library to inject as context into the builder prompt.
Prefers one example per unique archetype; within an archetype, picks
the example whose ``metadata.json:style`` block best matches the
deck plan's ``style_contract``. Caps at ``max_examples`` to stay
within token budget.

Selection is style-aware: when an archetype has multiple examples,
the selector scores each candidate's style against the deck-level
style contract on four dimensions (tone, density,
illustrative_richness, accent_strategy). ``density`` is treated as
ordinal (low<medium<high) so a "medium" plan prefers a "medium"
example over a "high" one over a "low" one. The other three fields
score 1.0 for an exact match, 0.0 otherwise. Ties fall back to
alphabetical example name (deterministic).

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

# Density is the only ordinal style dimension; map to numeric for
# distance scoring. Unknown values get None and contribute 0.0.
_DENSITY_RANK = {"low": 0, "medium": 1, "high": 2}


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


def _load_style(example_dir: Path) -> dict:
    """Return the example's ``metadata.json:style`` block, or {} if absent."""
    try:
        meta = json.loads((example_dir / "metadata.json").read_text(encoding="utf-8"))
        style = meta.get("style") or {}
        return style if isinstance(style, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _score_style_match(plan_style: dict, ex_style: dict) -> float:
    """Score how well an example's style matches the plan's style contract.

    Maximum score is 4.0 (one point per dimension). ``density`` uses ordinal
    distance: exact match = 1.0, one step away = 0.5, two steps = 0.0. The
    other three dimensions (tone, illustrative_richness, accent_strategy)
    score 1.0 for an exact match, 0.0 otherwise. Missing fields on either
    side contribute 0.0.
    """
    if not plan_style or not ex_style:
        return 0.0

    score = 0.0

    # Density: ordinal, partial credit
    plan_d = _DENSITY_RANK.get(plan_style.get("density"))
    ex_d = _DENSITY_RANK.get(ex_style.get("density"))
    if plan_d is not None and ex_d is not None:
        diff = abs(plan_d - ex_d)
        if diff == 0:
            score += 1.0
        elif diff == 1:
            score += 0.5
        # diff == 2 contributes 0.0

    # Other dimensions: exact match only
    for field in ("tone", "illustrative_richness", "accent_strategy"):
        p = plan_style.get(field)
        e = ex_style.get(field)
        if p and e and p == e:
            score += 1.0

    return score


def _rank_candidates(candidates: list[Path], plan_style: dict) -> list[Path]:
    """Order candidates by style match (descending), name (ascending) as tiebreak."""
    if not plan_style:
        # No style guidance: preserve historic alphabetical order.
        return list(candidates)
    scored = [(_score_style_match(plan_style, _load_style(c)), c.name, c) for c in candidates]
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [c for _, _, c in scored]


def select_examples(
    deck_plan: dict,
    *,
    max_examples: int = 3,
    examples_dir: Path | None = None,
) -> list[ExampleSnippet]:
    """Select examples matching the archetypes in *deck_plan*.

    Strategy:
    1. Collect unique archetypes from the deck plan's slides.
    2. For each archetype, pick the example whose ``style`` block best
       matches the deck plan's ``style_contract`` (see
       :func:`_score_style_match`). Ties fall back to alphabetical
       example name (deterministic).
    3. Cap at *max_examples* (prefer archetype diversity over second
       examples of the same archetype).
    4. If fewer plan archetypes than *max_examples*, fill remaining
       slots with second-best examples from already-covered archetypes.

    Returns a list of ExampleSnippet with the source code.
    """
    library = _discover_examples(examples_dir)
    plan_style = deck_plan.get("style_contract") or {}

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

    # Phase 1: one style-best example per unique archetype
    for arch in plan_archetypes:
        if len(selected) >= max_examples:
            break
        ranked = _rank_candidates(library.get(arch, []), plan_style)
        for cdir in ranked:
            if cdir not in used_dirs:
                snippet = _load_snippet(cdir, arch)
                if snippet:
                    selected.append(snippet)
                    used_dirs.add(cdir)
                    break

    # Phase 2: fill remaining slots with second-best examples for the
    # same plan archetypes (still style-ranked, just skipping the one
    # already used).
    if len(selected) < max_examples:
        for arch in plan_archetypes:
            if len(selected) >= max_examples:
                break
            ranked = _rank_candidates(library.get(arch, []), plan_style)
            for cdir in ranked:
                if cdir not in used_dirs:
                    snippet = _load_snippet(cdir, arch)
                    if snippet:
                        selected.append(snippet)
                        used_dirs.add(cdir)
                        break

    # Phase 3: if still short (very rare), pick from any archetype.
    if len(selected) < max_examples:
        for arch, dirs in library.items():
            if len(selected) >= max_examples:
                break
            ranked = _rank_candidates(dirs, plan_style)
            for cdir in ranked:
                if cdir not in used_dirs:
                    snippet = _load_snippet(cdir, arch)
                    if snippet:
                        selected.append(snippet)
                        used_dirs.add(cdir)
                        break

    logger.info(
        "Selected %d examples for %d plan archetypes (style=%s): %s",
        len(selected),
        len(plan_archetypes),
        plan_style or "none",
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
