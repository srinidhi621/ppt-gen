"""Preflight validation + remediation for DeckIR."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..models.deck_ir import DeckIR, DeckSlide, FieldValue
from ..models.validation import ValidationReport, ValidationViolation


def _load_layout_catalog(catalog_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load layout catalog and index by layout_id."""
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    return {entry["layout_id"]: entry for entry in catalog.get("layouts", [])}


def _count_chars(value: FieldValue) -> int:
    """Count total characters in a field value."""
    if isinstance(value, str):
        return len(value)
    elif isinstance(value, list):
        return sum(len(str(item)) for item in value)
    return 0


def _count_bullets(value: FieldValue) -> int:
    """Count number of bullets in a field value."""
    if isinstance(value, list):
        return len(value)
    elif isinstance(value, str) and value.strip():
        return 1  # Single text counts as 1 bullet
    return 0


def _max_words_in_bullet(value: FieldValue) -> int:
    """Get maximum word count across all bullets."""
    if isinstance(value, str):
        return len(value.split())
    elif isinstance(value, list):
        return max((len(str(item).split()) for item in value), default=0)
    return 0


def _estimate_lines(value: FieldValue, avg_chars_per_line: int) -> int:
    """Estimate number of lines needed for the text."""
    if avg_chars_per_line <= 0:
        avg_chars_per_line = 50  # Fallback default
    total_chars = _count_chars(value)
    return math.ceil(total_chars / avg_chars_per_line) if total_chars > 0 else 0


def _truncate_text(text: str, max_chars: int) -> str:
    """Truncate text to max chars, preserving word boundaries."""
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    truncated = text[: max_chars - 3]
    last_space = truncated.rfind(" ")
    if last_space > (max_chars - 3) * 0.7:  # Keep at least 70% of allowed length
        truncated = truncated[:last_space]
    return truncated.rstrip() + "..."


def _shorten_bullet(bullet: str, max_words: int) -> str:
    """Shorten a bullet to max words."""
    words = bullet.split()
    if len(words) <= max_words:
        return bullet
    return " ".join(words[:max_words]) + "..."


def _validate_slide(
    slide: DeckSlide, layout_entry: Dict[str, Any]
) -> List[ValidationViolation]:
    """Validate a single slide against layout constraints."""
    violations: List[ValidationViolation] = []
    constraints = layout_entry.get("constraints", {})
    
    max_title_chars = constraints.get("max_title_chars", 100)
    max_bullets = constraints.get("max_bullets", 7)
    max_words_per_bullet = constraints.get("max_words_per_bullet", 18)
    max_total_body_chars = constraints.get("max_total_body_chars", 500)
    body_line_budget = constraints.get("body_line_budget", 12)
    avg_chars_per_line = constraints.get("avg_chars_per_line", 50)
    
    # Check title length
    if "ph_title" in slide.fields:
        title_chars = _count_chars(slide.fields["ph_title"])
        if title_chars > max_title_chars:
            violations.append(ValidationViolation(
                slide_id=slide.slide_id,
                layout_id=slide.layout_id,
                field_key="ph_title",
                violation_type="TITLE_TOO_LONG",
                severity="WARN",
                recommended_action=f"Truncate title to {max_title_chars} chars",
            ))
    
    # Check body fields (ph_body, ph_body_left, ph_body_right, ph_col1-4)
    body_fields = [k for k in slide.fields.keys() if k.startswith("ph_body") or k.startswith("ph_col")]
    
    for field_key in body_fields:
        value = slide.fields[field_key]
        
        # Check bullet count
        bullet_count = _count_bullets(value)
        if max_bullets > 0 and bullet_count > max_bullets:
            violations.append(ValidationViolation(
                slide_id=slide.slide_id,
                layout_id=slide.layout_id,
                field_key=field_key,
                violation_type="TOO_MANY_BULLETS",
                severity="BLOCKING",
                recommended_action=f"Reduce to {max_bullets} bullets or move overflow to notes",
            ))
        
        # Check words per bullet
        max_words = _max_words_in_bullet(value)
        if max_words > max_words_per_bullet:
            violations.append(ValidationViolation(
                slide_id=slide.slide_id,
                layout_id=slide.layout_id,
                field_key=field_key,
                violation_type="WORDS_PER_BULLET",
                severity="WARN",
                recommended_action=f"Shorten bullets to {max_words_per_bullet} words max",
            ))
        
        # Check total body chars
        total_chars = _count_chars(value)
        if max_total_body_chars > 0 and total_chars > max_total_body_chars:
            violations.append(ValidationViolation(
                slide_id=slide.slide_id,
                layout_id=slide.layout_id,
                field_key=field_key,
                violation_type="TOTAL_BODY_CHARS",
                severity="BLOCKING",
                recommended_action=f"Reduce body text to {max_total_body_chars} chars",
            ))
        
        # Check estimated line count
        estimated_lines = _estimate_lines(value, avg_chars_per_line)
        if body_line_budget > 0 and estimated_lines > body_line_budget:
            violations.append(ValidationViolation(
                slide_id=slide.slide_id,
                layout_id=slide.layout_id,
                field_key=field_key,
                violation_type="BODY_LINE_BUDGET",
                severity="WARN",
                recommended_action=f"Content exceeds line budget ({estimated_lines} > {body_line_budget})",
            ))
    
    return violations


def _remediate_slide(
    slide: DeckSlide, 
    violations: List[ValidationViolation],
    layout_entry: Dict[str, Any]
) -> DeckSlide:
    """Apply deterministic remediation to a slide.
    
    Remediation order (per AGENTS.md):
    1. DROP_BULLETS - trim bullet count
    2. CONDENSE - shorten bullets
    3. MOVE_TO_SPEAKER_NOTES - pressure valve
    4. (SPLIT_SLIDE - not implemented in MVP, just warns)
    """
    constraints = layout_entry.get("constraints", {})
    max_title_chars = constraints.get("max_title_chars", 100)
    max_bullets = constraints.get("max_bullets", 7)
    max_words_per_bullet = constraints.get("max_words_per_bullet", 18)
    max_total_body_chars = constraints.get("max_total_body_chars", 500)
    
    # Deep copy slide to avoid mutation
    new_fields = copy.deepcopy(slide.fields)
    notes_additions: List[str] = []
    
    # Group violations by field
    violations_by_field: Dict[str, List[ValidationViolation]] = {}
    for v in violations:
        if v.field_key:
            violations_by_field.setdefault(v.field_key, []).append(v)
    
    # Handle title truncation
    if "ph_title" in new_fields:
        title_violations = [v for v in violations if v.field_key == "ph_title"]
        if any(v.violation_type == "TITLE_TOO_LONG" for v in title_violations):
            original_title = str(new_fields["ph_title"])
            new_fields["ph_title"] = _truncate_text(original_title, max_title_chars)
    
    # Handle body field violations
    body_fields = [k for k in new_fields.keys() if k.startswith("ph_body") or k.startswith("ph_col")]
    
    for field_key in body_fields:
        field_violations = violations_by_field.get(field_key, [])
        if not field_violations:
            continue
        
        value = new_fields[field_key]
        
        # Step 1: DROP_BULLETS - trim bullet count if too many
        if isinstance(value, list) and max_bullets > 0:
            has_too_many = any(v.violation_type == "TOO_MANY_BULLETS" for v in field_violations)
            if has_too_many and len(value) > max_bullets:
                overflow = value[max_bullets:]
                value = value[:max_bullets]
                notes_additions.append(
                    f"[Overflow from {field_key}]: " + " | ".join(str(b) for b in overflow)
                )
                new_fields[field_key] = value
        
        # Step 2: CONDENSE - shorten individual bullets
        has_word_violation = any(v.violation_type == "WORDS_PER_BULLET" for v in field_violations)
        if has_word_violation:
            if isinstance(value, list):
                new_fields[field_key] = [_shorten_bullet(str(b), max_words_per_bullet) for b in value]
            elif isinstance(value, str):
                new_fields[field_key] = _shorten_bullet(value, max_words_per_bullet)
        
        # Step 3: MOVE_TO_SPEAKER_NOTES - if still exceeds total chars
        value = new_fields[field_key]
        total_chars = _count_chars(value)
        if max_total_body_chars > 0 and total_chars > max_total_body_chars:
            if isinstance(value, list) and len(value) > 1:
                # Move last bullets to notes until under budget
                while len(value) > 1 and _count_chars(value) > max_total_body_chars:
                    moved = value.pop()
                    notes_additions.append(f"[Moved from {field_key}]: {moved}")
                new_fields[field_key] = value
            elif isinstance(value, list) and len(value) == 1:
                original = str(value[0])
                truncated = _truncate_text(original, max_total_body_chars)
                new_fields[field_key] = [truncated]
                if truncated != original:
                    notes_additions.append(f"[Full text from {field_key}]: {original}")
            elif isinstance(value, str):
                # Truncate string
                new_fields[field_key] = _truncate_text(value, max_total_body_chars)
                if len(value) > max_total_body_chars:
                    notes_additions.append(f"[Full text from {field_key}]: {value}")
    
    # Build new speaker notes
    original_notes = slide.speaker_notes or ""
    if isinstance(original_notes, dict):
        original_notes = json.dumps(original_notes, sort_keys=True)
    
    if notes_additions:
        separator = "\n\n---\n[REMEDIATION OVERFLOW]\n" if original_notes else "[REMEDIATION OVERFLOW]\n"
        new_notes = original_notes + separator + "\n".join(notes_additions)
    else:
        new_notes = original_notes
    
    return DeckSlide(
        slide_id=slide.slide_id,
        layout_id=slide.layout_id,
        fields=new_fields,
        speaker_notes=new_notes,
        asset_refs=slide.asset_refs,
        constraints_override=slide.constraints_override,
    )


def validate_and_remediate(
    deck: DeckIR, layout_catalog_path: Path
) -> Tuple[DeckIR, ValidationReport]:
    """Validate and remediate DeckIR, returning (deck_v1_1, report).
    
    Args:
        deck: Input DeckIR to validate
        layout_catalog_path: Path to layout_catalog.json
        
    Returns:
        Tuple of (remediated DeckIR, ValidationReport)
    """
    layout_catalog = _load_layout_catalog(layout_catalog_path)
    all_violations: List[ValidationViolation] = []
    remediated_slides: List[DeckSlide] = []
    
    for slide in deck.slides:
        layout_entry = layout_catalog.get(slide.layout_id)
        if not layout_entry:
            # Unknown layout - can't validate constraints
            all_violations.append(ValidationViolation(
                slide_id=slide.slide_id,
                layout_id=slide.layout_id,
                field_key=None,
                violation_type="BODY_TOO_DENSE",  # Use as catch-all
                severity="BLOCKING",
                recommended_action=f"Unknown layout_id: {slide.layout_id}",
            ))
            remediated_slides.append(slide)
            continue
        
        # Validate slide
        slide_violations = _validate_slide(slide, layout_entry)
        all_violations.extend(slide_violations)
        
        # Remediate if there are violations
        if slide_violations:
            remediated_slide = _remediate_slide(slide, slide_violations, layout_entry)
            remediated_slides.append(remediated_slide)
        else:
            remediated_slides.append(slide)
    
    # Build remediated deck
    remediated_deck = DeckIR(
        deck_id=deck.deck_id,
        run_id=deck.run_id,
        template_id=deck.template_id,
        title=deck.title,
        subtitle=deck.subtitle,
        global_constraints=deck.global_constraints,
        slides=remediated_slides,
    )
    
    report = ValidationReport(violations=all_violations)
    return remediated_deck, report
