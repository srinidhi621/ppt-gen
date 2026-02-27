"""Deterministic DeckIR -> CompositionSpec projection."""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

from ..models.composition import (
    CompositionFitDiagnostics,
    CompositionSlide,
    CompositionSpec,
    CompositionTextBlock,
    CompositionVisualBlock,
    OverflowAction,
    PlacementMode,
    VisualRole,
)
from ..models.deck_ir import DeckIR, DeckSlide, FieldValue
from ..models.validation import ValidationReport, ValidationViolation


def build_composition_spec(
    *,
    deck_before: DeckIR,
    deck_after: DeckIR,
    before_report: ValidationReport,
    after_report: ValidationReport | None,
    stage: str,
) -> CompositionSpec:
    """Build deterministic composition metadata from pre/post validation state."""
    before_by_slide, before_by_field = _index_violations(before_report)
    after_by_slide, _ = _index_violations(after_report)
    slides_before = {slide.slide_id: slide for slide in deck_before.slides}

    composition_slides: List[CompositionSlide] = []
    for slide_after in deck_after.slides:
        slide_before = slides_before.get(slide_after.slide_id, slide_after)
        notes_additions = _extract_notes_additions(slide_before, slide_after)

        text_blocks = _build_text_blocks(slide_after, before_by_field)
        visual_blocks = _build_visual_blocks(slide_after)

        remediations = _collect_remediations(text_blocks, notes_additions)
        fit = CompositionFitDiagnostics(
            before=sorted(before_by_slide.get(slide_after.slide_id, set())),
            after=sorted(after_by_slide.get(slide_after.slide_id, set())),
            remediations=remediations,
        )
        composition_slides.append(
            CompositionSlide(
                slide_id=slide_after.slide_id,
                layout_id=slide_after.layout_id,
                archetype=_infer_archetype(slide_after.layout_id),
                text_blocks=text_blocks,
                visual_blocks=visual_blocks,
                notes_additions=notes_additions,
                fit_diagnostics=fit,
            )
        )

    return CompositionSpec(version="1.0", stage=stage, slides=composition_slides)


def _index_violations(
    report: ValidationReport | None,
) -> Tuple[Dict[str, set[str]], Dict[Tuple[str, str], List[ValidationViolation]]]:
    by_slide: Dict[str, set[str]] = {}
    by_field: Dict[Tuple[str, str], List[ValidationViolation]] = {}
    if report is None:
        return by_slide, by_field

    for violation in report.violations:
        by_slide.setdefault(violation.slide_id, set()).add(violation.violation_type)
        if violation.field_key:
            by_field.setdefault((violation.slide_id, violation.field_key), []).append(violation)
    return by_slide, by_field


def _build_text_blocks(
    slide: DeckSlide,
    violations_by_field: Dict[Tuple[str, str], List[ValidationViolation]],
) -> List[CompositionTextBlock]:
    blocks: List[CompositionTextBlock] = []
    for field_key in sorted(slide.fields.keys()):
        value = slide.fields[field_key]
        if not _is_textual_field(field_key, value):
            continue
        field_violations = violations_by_field.get((slide.slide_id, field_key), [])
        blocks.append(
            CompositionTextBlock(
                field_key=field_key,
                text=_field_to_text(value),
                font_size_pt=_infer_font_size(field_key),
                line_spacing_pt=_infer_line_spacing(field_key),
                overflow_action=_infer_overflow_action(field_violations),
            )
        )
    return blocks


def _build_visual_blocks(slide: DeckSlide) -> List[CompositionVisualBlock]:
    blocks: List[CompositionVisualBlock] = []
    for idx, asset in enumerate(slide.asset_refs):
        role = _infer_visual_role(layout_id=slide.layout_id, visual_index=idx)
        placement = _infer_placement_mode(asset_type=asset.asset_type, role=role)
        blocks.append(
            CompositionVisualBlock(
                target_field_key=asset.target_field_key or "ph_image",
                asset_ref=asset,
                role=role,
                placement_mode=placement,
                size_cap_pct=_infer_size_cap(role, placement),
            )
        )
    return blocks


def _is_textual_field(field_key: str, value: FieldValue) -> bool:
    if field_key.startswith("ph_image"):
        return False
    if isinstance(value, (str, list)):
        return True
    return False


def _field_to_text(value: FieldValue) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        bullets = [str(item).strip() for item in value if str(item).strip()]
        return "\n".join(f"- {bullet}" for bullet in bullets)
    return str(value)


def _infer_font_size(field_key: str) -> float | None:
    if field_key == "ph_title":
        return 34.0
    if field_key == "ph_subtitle":
        return 22.0
    if field_key.startswith("ph_body"):
        return 18.0
    if field_key.startswith("ph_col"):
        return 16.0
    return None


def _infer_line_spacing(field_key: str) -> float | None:
    if field_key == "ph_title":
        return 1.08
    if field_key.startswith("ph_body") or field_key.startswith("ph_col"):
        return 1.2
    return None


def _infer_overflow_action(violations: Iterable[ValidationViolation]) -> OverflowAction:
    action_priority: List[Tuple[str, OverflowAction]] = [
        ("TOTAL_BODY_CHARS", "move_to_speaker_notes"),
        ("BODY_LINE_BUDGET", "move_to_speaker_notes"),
        ("TOO_MANY_BULLETS", "drop_bullets"),
        ("WORDS_PER_BULLET", "condense"),
        ("TITLE_TOO_LONG", "condense"),
        ("BODY_TOO_DENSE", "split_slide"),
    ]
    violation_types = {violation.violation_type for violation in violations}
    for violation_type, action in action_priority:
        if violation_type in violation_types:
            return action
    return "none"


def _infer_archetype(layout_id: str) -> str:
    lowered = layout_id.lower()
    if "section_break" in lowered or lowered.startswith("title_"):
        return "section_break"
    if "image" in lowered:
        return "visual_story"
    if "two_content" in lowered or "three_content" in lowered or "four_content" in lowered:
        return "comparison"
    if "closing" in lowered:
        return "closing"
    return "content"


def _infer_visual_role(*, layout_id: str, visual_index: int) -> VisualRole:
    if visual_index == 0:
        if "section_break" in layout_id or layout_id.startswith("title_"):
            return "hero"
        return "primary"
    if visual_index == 1:
        return "secondary"
    return "accent"


def _infer_placement_mode(*, asset_type: str, role: VisualRole) -> PlacementMode:
    if asset_type == "icon":
        if role == "hero":
            return "contain"
        if role == "accent":
            return "grid"
        return "centered_icon"
    if role == "hero":
        return "fill"
    return "contain"


def _infer_size_cap(role: VisualRole, placement_mode: PlacementMode) -> float | None:
    if placement_mode == "fill":
        return None
    if role == "primary":
        return 0.22
    if role == "secondary":
        return 0.16
    if role == "accent":
        return 0.1
    return 0.28


def _extract_notes_additions(slide_before: DeckSlide, slide_after: DeckSlide) -> List[str]:
    before = _notes_as_text(slide_before.speaker_notes)
    after = _notes_as_text(slide_after.speaker_notes)
    if not after:
        return []
    if not before:
        before = ""
    if len(after) <= len(before):
        return []
    delta = after[len(before) :]
    marker = "[REMEDIATION OVERFLOW]"
    if marker in delta:
        delta = delta.split(marker, 1)[1]
    lines = [line.strip() for line in delta.splitlines() if line.strip() and line.strip() != "---"]
    return lines


def _notes_as_text(notes: object) -> str:
    if notes is None:
        return ""
    if isinstance(notes, str):
        return notes
    return str(notes)


def _collect_remediations(
    text_blocks: List[CompositionTextBlock], notes_additions: List[str]
) -> List[str]:
    remediations: List[str] = []
    for block in text_blocks:
        if block.overflow_action != "none":
            remediations.append(f"{block.field_key}:{block.overflow_action}")
    remediations.extend(notes_additions)
    return remediations
