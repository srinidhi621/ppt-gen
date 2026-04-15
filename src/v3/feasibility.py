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


def _count_slide_items(slide: dict) -> int:
    """Count the number of content items on a slide.

    Returns the count of the primary content grouping for the slide's
    archetype: supports, cards, metrics, bullets, steps, etc.
    """
    # Check each possible collection field and return the largest
    counts = [
        len(slide.get("supports", [])),
        len(slide.get("cards", [])),
        len(slide.get("metrics", [])),
        len(slide.get("bullets", [])),
        len(slide.get("steps", [])),
    ]

    max_count = max(counts) if counts else 0

    # For archetypes with no collection fields, count direct content blocks
    if max_count == 0:
        items = 0
        if slide.get("headline"):
            items += 1
        if slide.get("body"):
            items += 1
        if slide.get("hero_text"):
            items += 1
        return items

    return max_count
