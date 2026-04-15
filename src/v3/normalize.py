"""Normalize user input into structured content for the planner.

Parses plain text or markdown into ``normalized_content.json`` format.
Extracts optional cues: slide count hint, density preference, audience.

Usage::

    from src.v3.normalize import normalize

    result = normalize("# My Deck\\n\\nSlide about revenue growth...")
    # result is a dict matching normalized_content.schema.json
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Cue extraction patterns
# ---------------------------------------------------------------------------

_SLIDE_COUNT_RE = re.compile(
    r"(?:(?:create|make|generate|want|need)\s+)?(\d{1,2})\s+slides?",
    re.IGNORECASE,
)

_AUDIENCE_RE = re.compile(
    r"(?:audience|for|presenting\s+to)[:\s]+([A-Za-z\s,/-]+?)(?:\.\s|\.\n|\n|$)",
    re.IGNORECASE,
)

_DENSITY_KEYWORDS = {
    "minimal": "low",
    "simple": "low",
    "brief": "low",
    "concise": "low",
    "low": "low",
    "detailed": "high",
    "comprehensive": "high",
    "thorough": "high",
    "dense": "high",
    "high": "high",
}


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------

def _split_markdown_sections(text: str) -> list[dict]:
    """Split markdown text into sections by headings."""
    lines = text.split("\n")
    sections: list[dict] = []
    current_heading = ""
    current_body_lines: list[str] = []
    current_bullets: list[str] = []

    def _flush():
        if current_heading or current_body_lines or current_bullets:
            body = "\n".join(current_body_lines).strip()
            sections.append({
                "heading": current_heading or "Introduction",
                "body": body,
                **({"bullets": current_bullets} if current_bullets else {}),
            })

    for line in lines:
        stripped = line.strip()

        # Heading detection (## or # )
        heading_match = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading_match:
            _flush()
            current_heading = heading_match.group(2).strip()
            current_body_lines = []
            current_bullets = []
            continue

        # Bullet detection
        bullet_match = re.match(r"^[-*+]\s+(.+)$", stripped)
        if bullet_match:
            current_bullets.append(bullet_match.group(1).strip())
            continue

        # Numbered list
        numbered_match = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if numbered_match:
            current_bullets.append(numbered_match.group(1).strip())
            continue

        # Regular text
        if stripped:
            current_body_lines.append(stripped)

    _flush()
    return sections


def _split_plain_text_sections(text: str) -> list[dict]:
    """Split plain text into sections by paragraph breaks."""
    paragraphs = re.split(r"\n\s*\n", text.strip())
    sections = []

    for i, para in enumerate(paragraphs):
        para = para.strip()
        if not para:
            continue

        lines = para.split("\n")
        # Use first line as heading if it's short enough
        if len(lines) > 1 and len(lines[0]) < 80:
            heading = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
        else:
            heading = f"Section {i + 1}"
            body = para

        sections.append({"heading": heading, "body": body})

    return sections


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize(user_input: str) -> dict:
    """Normalize user input into the planner's input format.

    Args:
        user_input: Raw user text (plain text or markdown).

    Returns:
        A dict matching normalized_content.schema.json.
    """
    text = user_input.strip()
    if not text:
        return {
            "title": "Untitled Presentation",
            "sections": [{"heading": "Content", "body": ""}],
            "metadata": {"source_type": "text", "word_count": 0},
        }

    # Extract cues
    slide_count_hint = _extract_slide_count(text)
    audience = _extract_audience(text)
    density = _extract_density(text)

    # Detect markdown
    has_headings = bool(re.search(r"^#{1,3}\s+", text, re.MULTILINE))

    if has_headings:
        sections = _split_markdown_sections(text)
        source_type = "document"
    else:
        sections = _split_plain_text_sections(text)
        source_type = "text"

    # Ensure at least one section
    if not sections:
        sections = [{"heading": "Content", "body": text}]

    # Extract title from first heading or first section
    title = _extract_title(text, sections)

    # Build metadata
    metadata: dict = {
        "source_type": source_type,
        "word_count": len(text.split()),
    }
    if slide_count_hint:
        metadata["slide_count_hint"] = slide_count_hint
    if density:
        metadata["density_preference"] = density

    result: dict = {
        "title": title,
        "sections": sections,
        "metadata": metadata,
    }
    if audience:
        result["audience"] = audience

    return result


# ---------------------------------------------------------------------------
# Cue extractors
# ---------------------------------------------------------------------------

def _extract_title(text: str, sections: list[dict]) -> str:
    """Extract a deck title from the input."""
    # Check for a top-level markdown heading
    m = re.match(r"^#\s+(.+)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()

    # Use first section heading if it looks like a title (not "Section 1")
    if sections and not sections[0]["heading"].startswith("Section "):
        return sections[0]["heading"]

    # Fallback: first ~60 chars
    first_line = text.split("\n")[0].strip()
    if len(first_line) <= 80:
        return first_line
    return first_line[:60] + "..."


def _extract_slide_count(text: str) -> int | None:
    """Extract a slide count hint from user input."""
    m = _SLIDE_COUNT_RE.search(text)
    if m:
        count = int(m.group(1))
        if 1 <= count <= 30:
            return count
    return None


def _extract_audience(text: str) -> str | None:
    """Extract an audience hint from user input."""
    m = _AUDIENCE_RE.search(text)
    if m:
        audience = m.group(1).strip().rstrip(".,;:")
        if len(audience) > 3:
            return audience
    return None


def _extract_density(text: str) -> str | None:
    """Extract a density preference from user input."""
    text_lower = text.lower()
    for keyword, level in _DENSITY_KEYWORDS.items():
        if keyword in text_lower:
            return level
    return None
