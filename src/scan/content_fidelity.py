"""Content fidelity checker: compares user input facts against PPTX output.

Usage::

    report = check_content_fidelity("Our Q3 revenue grew 14%.", "output.pptx")
    assert report["visible_coverage_score"] > 0.8
"""

from __future__ import annotations

import re
from pathlib import Path

from pptx import Presentation


# ---------------------------------------------------------------------------
# Fact extraction
# ---------------------------------------------------------------------------

# Patterns to extract fact-like tokens from user input
_FACT_PATTERNS = [
    re.compile(r"\d+(?:\.\d+)?%"),                            # percentages
    re.compile(r"\$[\d,]+(?:\.\d+)?[BMKbmk]?"),               # dollar amounts
    re.compile(r"\b\d{4}\b"),                                  # years
    re.compile(r"\b(?:Q[1-4])\b"),                             # quarters
    re.compile(r"\b\d+(?:,\d{3})*(?:\.\d+)?\b"),              # numbers
    re.compile(r'"[^"]{3,}"'),                                 # quoted phrases
    re.compile(r"'[^']{3,}'"),                                 # single-quoted
]

# Pattern to find proper nouns (capitalized words not at sentence start)
_PROPER_NOUN_RE = re.compile(r"(?<=[.!?]\s)(?:[A-Z][a-z]+)|(?<=\s)([A-Z][a-z]{2,})")


def extract_facts(text: str) -> list[str]:
    """Extract factual tokens from user input text.

    Returns a deduplicated list of fact strings: numbers, percentages,
    dates, proper nouns, and quoted phrases.
    """
    facts = []
    seen = set()

    # Extract pattern-based facts
    for pattern in _FACT_PATTERNS:
        for match in pattern.finditer(text):
            fact = match.group(0).strip("'\"")
            if fact and fact not in seen and len(fact) > 1:
                seen.add(fact)
                facts.append(fact)

    # Extract proper nouns (capitalized words not at sentence start)
    sentences = re.split(r'[.!?]\s+', text)
    for sentence in sentences:
        words = sentence.split()
        for word in words[1:]:  # Skip first word of sentence
            clean = re.sub(r'[^\w]', '', word)
            if clean and clean[0].isupper() and len(clean) >= 3 and clean not in seen:
                seen.add(clean)
                facts.append(clean)

    return facts


# ---------------------------------------------------------------------------
# Text extraction from PPTX
# ---------------------------------------------------------------------------

def _extract_visible_text(prs: Presentation) -> str:
    """Extract all visible text from slide shapes."""
    texts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                texts.append(shape.text_frame.text)
    return "\n".join(texts)


def _extract_notes_text(prs: Presentation) -> str:
    """Extract text from slide notes."""
    texts = []
    for slide in prs.slides:
        if slide.has_notes_slide:
            notes = slide.notes_slide
            if notes.notes_text_frame:
                texts.append(notes.notes_text_frame.text)
    return "\n".join(texts)


# ---------------------------------------------------------------------------
# Detection patterns (shared with scanner)
# ---------------------------------------------------------------------------

_PLACEHOLDER_PATTERNS = [
    re.compile(r"\{title\}", re.IGNORECASE),
    re.compile(r"\{body\}", re.IGNORECASE),
    re.compile(r"Lorem ipsum", re.IGNORECASE),
    re.compile(r"\bTODO\b"),
    re.compile(r"\[insert\]", re.IGNORECASE),
    re.compile(r"\bTBD\b"),
    re.compile(r"\{\{.*?\}\}"),
]

_MARKDOWN_PATTERNS = [
    re.compile(r"\*\*"),
    re.compile(r"__"),
    re.compile(r"##"),
    re.compile(r"```"),
    re.compile(r"\[.*?\]\(.*?\)"),
    re.compile(r"(?m)^- "),
]

# Common numbers to exclude from hallucination detection
_COMMON_NUMBERS = {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
                   "0", "100", "1st", "2nd", "3rd"}

_NUMBER_RE = re.compile(r"\b\d+(?:,\d{3})*(?:\.\d+)?%?\b")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_content_fidelity(user_input: str, pptx_path: str | Path) -> dict:
    """Check how faithfully a PPTX represents the user's input content.

    Args:
        user_input: The original user text/prompt.
        pptx_path: Path to the generated PPTX file.

    Returns:
        A content_fidelity_report dict.
    """
    pptx_path = Path(pptx_path)
    prs = Presentation(str(pptx_path))

    # Extract text
    visible_text = _extract_visible_text(prs)
    notes_text = _extract_notes_text(prs)

    # Extract facts from user input
    facts = extract_facts(user_input)
    total_facts = len(facts)

    # Match facts
    matched_visible = []
    matched_notes_only = []
    dropped = []

    for fact in facts:
        fact_lower = fact.lower()
        if fact_lower in visible_text.lower():
            matched_visible.append(fact)
        elif fact_lower in notes_text.lower():
            matched_notes_only.append(fact)
        else:
            dropped.append(fact)

    # Coverage score
    visible_coverage = len(matched_visible) / total_facts if total_facts > 0 else 1.0

    # Detect placeholders in visible text
    placeholder_leaks = []
    for pattern in _PLACEHOLDER_PATTERNS:
        for m in pattern.finditer(visible_text):
            placeholder_leaks.append(m.group(0))

    # Detect markdown leaks
    markdown_leaks = []
    for pattern in _MARKDOWN_PATTERNS:
        for m in pattern.finditer(visible_text):
            markdown_leaks.append(m.group(0))

    # Detect hallucinated specifics
    # Numbers/percentages in visible text not in user input
    input_numbers = set()
    for m in _NUMBER_RE.finditer(user_input):
        input_numbers.add(m.group(0))

    hallucinated = []
    for m in _NUMBER_RE.finditer(visible_text):
        num = m.group(0)
        if num not in input_numbers and num not in _COMMON_NUMBERS:
            # Check if it's an ordinal
            if re.match(r"^\d+(?:st|nd|rd|th)$", num):
                continue
            hallucinated.append(num)

    # Deduplicate
    hallucinated = list(dict.fromkeys(hallucinated))
    placeholder_leaks = list(dict.fromkeys(placeholder_leaks))
    markdown_leaks = list(dict.fromkeys(markdown_leaks))

    return {
        "visible_coverage_score": round(visible_coverage, 2),
        "notes_only_fact_count": len(matched_notes_only),
        "total_facts": total_facts,
        "matched_visible_facts": len(matched_visible),
        "matched_notes_only_facts": matched_notes_only,
        "dropped_facts": dropped,
        "hallucinated_specifics": hallucinated,
        "placeholder_leaks": placeholder_leaks,
        "markdown_leaks": markdown_leaks,
    }
