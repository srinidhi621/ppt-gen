"""V3 Planner: converts normalized content into a deck plan via LLM.

Usage::

    from src.v3.planner import plan_deck
    from src.v3.llm_client import ResponsesClient

    client = ResponsesClient.from_env()
    plan = plan_deck(client, normalized_content)
    # plan is a validated dict matching deck_plan.schema.json
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from src.contracts.validator import validate
from src.v3.llm_client import LLMResponse, ResponsesClient, get_model_for_role
from src.v3.llm_retry import retry_generate_json

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_SYSTEM_PROMPT_PATH = _PROMPTS_DIR / "planner_system.txt"

# ---------------------------------------------------------------------------
# Archetype vocabulary (from SPEC-v3.md §5)
# ---------------------------------------------------------------------------

ARCHETYPE_VOCABULARY = {
    "hero_title":                          {"max_items": 2,  "max_words": 30,  "canvas_pref": "header_dark"},
    "section_break":                       {"max_items": 2,  "max_words": 20,  "canvas_pref": "header_dark"},
    "hero_statement_with_support_columns": {"max_items": 4,  "max_words": 85,  "canvas_pref": "header_light"},
    "three_cards":                         {"max_items": 3,  "max_words": 90,  "canvas_pref": "blank"},
    "comparison_split":                    {"max_items": 8,  "max_words": 80,  "canvas_pref": "blank"},
    "kpi_grid":                            {"max_items": 6,  "max_words": 60,  "canvas_pref": "blank"},
    "stat_list_with_icons":                {"max_items": 5,  "max_words": 75,  "canvas_pref": "header_light"},
    "process_flow":                        {"max_items": 6,  "max_words": 90,  "canvas_pref": "blank"},
    "quote_callout":                       {"max_items": 1,  "max_words": 50,  "canvas_pref": "header_dark"},
    "content_with_visual":                 {"max_items": 2,  "max_words": 60,  "canvas_pref": "blank"},
    "closing_cta":                         {"max_items": 3,  "max_words": 50,  "canvas_pref": "header_light"},
    "matrix_grid":                         {"max_items": 12, "max_words": 150, "canvas_pref": "blank"},
    "timeline_roadmap":                    {"max_items": 5,  "max_words": 100, "canvas_pref": "blank"},
}

# Fields that are forbidden in deck plans (geometry/styling)
_FORBIDDEN_FIELD_PATTERNS = re.compile(
    r"(left|top|width|height|^x$|^y$|emu|inch|hex|rgb|size_pt|font_size|font_name|color_code)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_deck_plan(plan: dict) -> list[str]:
    """Validate a deck plan dict. Returns list of error strings (empty = valid)."""
    errors: list[str] = []

    # JSON Schema validation
    ok, schema_errors = validate(plan, "deck_plan")
    if not ok:
        errors.extend(schema_errors)
        return errors  # Don't run semantic checks on schema-invalid plans

    # Semantic checks
    slides = plan.get("slides", [])

    for i, slide in enumerate(slides):
        prefix = f"slides[{i}]"

        # Archetype must be in vocabulary
        archetype = slide.get("archetype", "")
        if archetype not in ARCHETYPE_VOCABULARY:
            errors.append(
                f"{prefix}: archetype '{archetype}' not in vocabulary. "
                f"Valid: {sorted(ARCHETYPE_VOCABULARY.keys())}"
            )

        # Forbidden fields
        for key in slide:
            if _FORBIDDEN_FIELD_PATTERNS.search(key):
                errors.append(
                    f"{prefix}: forbidden field '{key}' — "
                    f"geometry/styling fields are not allowed in deck plans"
                )

        # Required fields
        if not slide.get("purpose"):
            errors.append(f"{prefix}: missing 'purpose'")
        if not slide.get("audience_takeaway"):
            errors.append(f"{prefix}: missing 'audience_takeaway'")
        if not slide.get("headline"):
            errors.append(f"{prefix}: missing 'headline'")

    return errors


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

def _load_system_prompt() -> str:
    """Load the planner system prompt from file."""
    return _SYSTEM_PROMPT_PATH.read_text()


def _build_user_message(normalized_content: dict) -> str:
    """Build the user message from normalized content."""
    parts = []

    # Title and audience
    title = normalized_content.get("title", "Untitled")
    parts.append(f"# Presentation request: {title}")

    audience = normalized_content.get("audience")
    if audience:
        parts.append(f"\nAudience: {audience}")

    # Metadata hints
    meta = normalized_content.get("metadata", {})
    slide_hint = meta.get("slide_count_hint")
    if slide_hint:
        parts.append(f"Requested slide count: {slide_hint}")

    density_pref = meta.get("density_preference")
    if density_pref:
        parts.append(f"Density preference: {density_pref}")

    # Sections
    parts.append("\n## Content\n")
    for section in normalized_content.get("sections", []):
        parts.append(f"### {section['heading']}")
        if section.get("body"):
            parts.append(section["body"])
        if section.get("bullets"):
            for bullet in section["bullets"]:
                parts.append(f"- {bullet}")
        parts.append("")

    # Available archetypes
    parts.append("\n## Available archetypes")
    parts.append("Use only these archetype labels:")
    for name in sorted(ARCHETYPE_VOCABULARY.keys()):
        cap = ARCHETYPE_VOCABULARY[name]
        parts.append(f"- {name} (max {cap['max_items']} items, {cap['max_words']} words)")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def plan_deck(
    client: ResponsesClient,
    normalized_content: dict,
    *,
    max_retries: int = 2,
) -> dict:
    """Generate a deck plan from normalized content.

    Args:
        client: The Responses API client.
        normalized_content: Dict matching normalized_content.schema.json.
        max_retries: Number of retries on validation failure.

    Returns:
        Validated deck plan dict matching deck_plan.schema.json.

    Raises:
        LLMInfraError: On infrastructure failure.
        LLMBudgetExhausted: When all retries fail.
    """
    model = get_model_for_role("planner")
    instructions = _load_system_prompt()
    user_message = _build_user_message(normalized_content)

    logger.info("Planning deck with model=%s, content_words=%d",
                model, normalized_content.get("metadata", {}).get("word_count", 0))

    result: LLMResponse = retry_generate_json(
        client,
        model=model,
        instructions=instructions,
        input_text=user_message,
        validator=validate_deck_plan,
        max_retries=max_retries,
    )

    logger.info(
        "Deck plan generated: %d slides, %d input tokens, %d output tokens",
        len(result.parsed.get("slides", [])),
        result.usage.input_tokens,
        result.usage.output_tokens,
    )

    return result.parsed
