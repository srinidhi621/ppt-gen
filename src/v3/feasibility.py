"""Feasibility gate: checks deck plan against archetype capacity limits.

Runs after the planner, before the builder. Rejects slides that exceed
their archetype's max_items or max_words limits.

Usage::

    from src.v3.feasibility import check_feasibility

    result = check_feasibility(deck_plan)
    if not result["passed"]:
        # re-plan the failing slides
        for v in result["violations"]:
            print(v)
"""

from __future__ import annotations

import re

from src.v3.planner import ARCHETYPE_VOCABULARY


def check_feasibility(deck_plan: dict) -> dict:
    """Check a deck plan against archetype capacity limits.

    Args:
        deck_plan: Validated dict matching deck_plan.schema.json.

    Returns:
        A dict with:
        - passed (bool): True if all slides pass.
        - violations (list[dict]): One entry per failing slide with:
            - slide_index (int)
            - slide_id (str)
            - archetype (str)
            - issues (list[str]): specific capacity violations
        - passing_slides (list[int]): indices of slides that passed.
    """
    violations = []
    passing = []

    for i, slide in enumerate(deck_plan.get("slides", [])):
        archetype = slide.get("archetype", "")
        capacity = ARCHETYPE_VOCABULARY.get(archetype)

        if capacity is None:
            violations.append({
                "slide_index": i,
                "slide_id": slide.get("slide_id", f"slide_{i}"),
                "archetype": archetype,
                "issues": [f"Unknown archetype '{archetype}'"],
            })
            continue

        issues = []

        # Check max_words
        word_count = _count_slide_words(slide)
        max_words = capacity["max_words"]
        if word_count > max_words:
            issues.append(
                f"Word count {word_count} exceeds max_words {max_words} "
                f"for archetype '{archetype}'"
            )

        # Check max_items
        item_count = _count_slide_items(slide)
        max_items = capacity["max_items"]
        if item_count > max_items:
            issues.append(
                f"Item count {item_count} exceeds max_items {max_items} "
                f"for archetype '{archetype}'"
            )

        if issues:
            violations.append({
                "slide_index": i,
                "slide_id": slide.get("slide_id", f"slide_{i}"),
                "archetype": archetype,
                "issues": issues,
            })
        else:
            passing.append(i)

    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "passing_slides": passing,
    }


def _count_slide_words(slide: dict) -> int:
    """Count total words across all content fields of a slide."""
    word_count = 0

    # Direct text fields
    for field in ("headline", "kicker", "hero_text", "body"):
        text = slide.get(field, "")
        if text:
            word_count += len(text.split())

    # Bullets
    for bullet in slide.get("bullets", []):
        word_count += len(bullet.split())

    # Supports (hero_statement archetype)
    for support in slide.get("supports", []):
        word_count += len(support.get("label", "").split())
        word_count += len(support.get("body", "").split())

    # Cards
    for card in slide.get("cards", []):
        word_count += len(card.get("title", "").split())
        word_count += len(card.get("body", "").split())

    # Metrics
    for metric in slide.get("metrics", []):
        word_count += len(metric.get("value", "").split())
        word_count += len(metric.get("label", "").split())

    # Steps
    for step in slide.get("steps", []):
        word_count += len(step.get("label", "").split())
        word_count += len(step.get("body", "").split())

    return word_count


# ---------------------------------------------------------------------------
# Per-archetype item counting rules
# ---------------------------------------------------------------------------

# Maps archetype → function(slide) → int.
# Each function counts the items that the archetype's max_items cap applies to.
_ARCHETYPE_ITEM_COUNTERS: dict[str, object] = {}


def _register(name: str):
    """Decorator to register an item counter for an archetype."""
    def decorator(fn):
        _ARCHETYPE_ITEM_COUNTERS[name] = fn
        return fn
    return decorator


@_register("hero_title")
def _items_hero_title(slide: dict) -> int:
    """max_items=2: headline + optional body/subhead."""
    count = 0
    if slide.get("headline"):
        count += 1
    if slide.get("body"):
        count += 1
    return count


@_register("section_break")
def _items_section_break(slide: dict) -> int:
    """max_items=2: headline + optional body."""
    count = 0
    if slide.get("headline"):
        count += 1
    if slide.get("body"):
        count += 1
    return count


@_register("hero_statement_with_support_columns")
def _items_hero_statement(slide: dict) -> int:
    """max_items=4: count of support columns."""
    return len(slide.get("supports", []))


@_register("three_cards")
def _items_three_cards(slide: dict) -> int:
    """max_items=3: count of cards."""
    return len(slide.get("cards", []))


@_register("comparison_split")
def _items_comparison_split(slide: dict) -> int:
    """max_items=8: total bullet points across both sides.

    Each card's body may contain newline-separated points.
    Count cards * average points, or just total lines across all card bodies.
    """
    total = 0
    for card in slide.get("cards", []):
        body = card.get("body", "")
        # Count non-empty lines as individual comparison points
        lines = [ln for ln in body.split("\n") if ln.strip()]
        total += max(len(lines), 1)  # at least 1 per card
    return total


@_register("kpi_grid")
def _items_kpi_grid(slide: dict) -> int:
    """max_items=6: count of metrics."""
    return len(slide.get("metrics", []))


@_register("stat_list_with_icons")
def _items_stat_list(slide: dict) -> int:
    """max_items=5: count of metrics/stat rows."""
    return len(slide.get("metrics", []))


@_register("process_flow")
def _items_process_flow(slide: dict) -> int:
    """max_items=6: count of steps."""
    return len(slide.get("steps", []))


@_register("quote_callout")
def _items_quote_callout(slide: dict) -> int:
    """max_items=1: the quote itself is the single item."""
    # A quote_callout has exactly 1 logical item: the quote.
    # headline=quote text, body=attribution — together they are 1 item.
    return 1 if slide.get("headline") else 0


@_register("content_with_visual")
def _items_content_with_visual(slide: dict) -> int:
    """max_items=2: text block + visual block."""
    count = 0
    if slide.get("body"):
        count += 1
    if slide.get("visual_intent"):
        count += 1
    return count


@_register("closing_cta")
def _items_closing_cta(slide: dict) -> int:
    """max_items=3: count of bullet items (next steps)."""
    return len(slide.get("bullets", []))


@_register("matrix_grid")
def _items_matrix_grid(slide: dict) -> int:
    """max_items=12: count of grid cells (cards)."""
    return len(slide.get("cards", []))


@_register("timeline_roadmap")
def _items_timeline_roadmap(slide: dict) -> int:
    """max_items=5: count of phases (steps)."""
    return len(slide.get("steps", []))


def _count_slide_items(slide: dict) -> int:
    """Count items using the archetype-specific counter.

    Falls back to a generic count if the archetype has no registered counter.
    """
    archetype = slide.get("archetype", "")
    counter = _ARCHETYPE_ITEM_COUNTERS.get(archetype)
    if counter is not None:
        return counter(slide)

    # Fallback for unknown archetypes: count the largest collection field
    counts = [
        len(slide.get("supports", [])),
        len(slide.get("cards", [])),
        len(slide.get("metrics", [])),
        len(slide.get("bullets", [])),
        len(slide.get("steps", [])),
    ]
    return max(counts) if any(counts) else 0
