"""Deterministic quality gates for final deck validation."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List

from ..models.deck_ir import DeckIR
from ..models.validation import ValidationReport


def summarize_composition_spec(spec: Dict[str, Any]) -> Dict[str, int]:
    """Summarize composition-level metrics for V1/V2 deltas."""
    slides = spec.get("slides", [])
    total_visual_blocks = 0
    slides_with_visuals = 0
    hero_icon_count = 0
    text_overflow_actions = 0
    slides_with_notes_additions = 0
    slides_with_image_assets = 0
    total_image_assets = 0

    for slide in slides:
        visual_blocks = slide.get("visual_blocks", []) or []
        text_blocks = slide.get("text_blocks", []) or []
        notes_additions = slide.get("notes_additions", []) or []

        if visual_blocks:
            slides_with_visuals += 1
        total_visual_blocks += len(visual_blocks)
        slides_with_notes_additions += 1 if notes_additions else 0

        has_image_asset = False
        for visual in visual_blocks:
            asset_ref = visual.get("asset_ref", {}) if isinstance(visual, dict) else {}
            if isinstance(asset_ref, dict) and asset_ref.get("asset_type") == "image":
                total_image_assets += 1
                has_image_asset = True
            if (
                visual.get("role") == "hero"
                and isinstance(asset_ref, dict)
                and asset_ref.get("asset_type") == "icon"
            ):
                hero_icon_count += 1
        if has_image_asset:
            slides_with_image_assets += 1

        for block in text_blocks:
            action = block.get("overflow_action") if isinstance(block, dict) else "none"
            if action and action != "none":
                text_overflow_actions += 1

    return {
        "slides_total": len(slides),
        "slides_with_visuals": slides_with_visuals,
        "total_visual_blocks": total_visual_blocks,
        "hero_icon_count": hero_icon_count,
        "text_overflow_actions": text_overflow_actions,
        "slides_with_notes_additions": slides_with_notes_additions,
        "slides_with_image_assets": slides_with_image_assets,
        "total_image_assets": total_image_assets,
    }


def evaluate_v2_quality_gates(
    *,
    deck_v2: DeckIR,
    validation_v2_post: ValidationReport,
    diagnose_report_v2: Dict[str, Any],
    composition_spec_v2: Dict[str, Any],
    image_capable_layouts: List[str],
    run_log_path: Path,
    intent_briefs: List[Dict[str, Any]] | None = None,
    structure_plans: List[Dict[str, Any]] | None = None,
    visual_realization_plans: List[Dict[str, Any]] | None = None,
    planning_validation: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Evaluate final V2 quality gates and return structured results."""
    issues: List[Dict[str, Any]] = []
    checks: Dict[str, Dict[str, Any]] = {}

    # Gate 1: no blocking violations after remediation.
    blocking_violations = [
        violation
        for violation in validation_v2_post.violations
        if violation.severity == "BLOCKING"
    ]
    checks["no_blocking_overflow"] = {
        "pass": len(blocking_violations) == 0,
        "count": len(blocking_violations),
    }
    for violation in blocking_violations:
        issues.append(
            {
                "gate": "no_blocking_overflow",
                "slide_id": violation.slide_id,
                "message": (
                    f"Blocking violation remains: {violation.violation_type}"
                    f" ({violation.field_key or 'slide-level'})"
                ),
            }
        )

    # Gate 2: image-capable slides must have a planned+rendered visual unless unresolved is logged.
    diagnose_by_slide_id = _index_diagnose_slides(diagnose_report_v2)
    unresolved_slide_ids = _collect_unresolved_visual_slide_ids(run_log_path)
    missing_visuals: List[Dict[str, Any]] = []
    for slide in deck_v2.slides:
        if slide.layout_id not in image_capable_layouts:
            continue
        planned_visual = any(
            _is_image_target(asset_ref.target_field_key) for asset_ref in slide.asset_refs
        )
        diagnosed = diagnose_by_slide_id.get(slide.slide_id, {})
        actual_images = int(diagnosed.get("actual_images", 0) or 0)
        if planned_visual and actual_images >= 1:
            continue
        if slide.slide_id in unresolved_slide_ids:
            continue
        missing_visuals.append(
            {
                "slide_id": slide.slide_id,
                "layout_id": slide.layout_id,
                "planned_visual": planned_visual,
                "actual_images": actual_images,
            }
        )

    checks["visual_coverage_image_layouts"] = {
        "pass": len(missing_visuals) == 0,
        "missing_count": len(missing_visuals),
    }
    for missing in missing_visuals:
        issues.append(
            {
                "gate": "visual_coverage_image_layouts",
                "slide_id": missing["slide_id"],
                "message": (
                    "Image-capable layout has missing visual coverage "
                    f"(planned={missing['planned_visual']}, actual_images={missing['actual_images']})."
                ),
                "details": missing,
            }
        )

    # Gate 3: icon cannot be used as hero visual.
    hero_icon_violations = _collect_hero_icon_violations(composition_spec_v2)
    checks["no_icon_hero_stretch"] = {
        "pass": len(hero_icon_violations) == 0,
        "count": len(hero_icon_violations),
    }
    for violation in hero_icon_violations:
        issues.append(
            {
                "gate": "no_icon_hero_stretch",
                "slide_id": violation["slide_id"],
                "message": (
                    f"Hero slot uses icon asset ({violation['asset_id']}); "
                    "reserve hero role for image assets."
                ),
                "details": violation,
            }
        )

    # Gate 4: markdown markers should not be visible in rendered text.
    markdown_leaks = _collect_markdown_leaks(diagnose_report_v2)
    checks["no_markdown_marker_leak"] = {
        "pass": len(markdown_leaks) == 0,
        "count": len(markdown_leaks),
    }
    for leak in markdown_leaks:
        issues.append(
            {
                "gate": "no_markdown_marker_leak",
                "slide_id": leak["slide_id"],
                "message": f"Rendered text contains markdown marker: {leak['snippet']}",
                "details": leak,
            }
        )

    # Gate 5: deck-level visual density must be high enough to look intentional.
    composition_metrics = summarize_composition_spec(composition_spec_v2)
    slides_total = max(1, int(composition_metrics.get("slides_total", 0)))
    slides_with_visuals = int(composition_metrics.get("slides_with_visuals", 0))
    min_visual_slides = max(1, math.ceil(slides_total * 0.5))
    checks["min_visual_density"] = {
        "pass": slides_with_visuals >= min_visual_slides,
        "slides_with_visuals": slides_with_visuals,
        "min_required": min_visual_slides,
    }
    if slides_with_visuals < min_visual_slides:
        issues.append(
            {
                "gate": "min_visual_density",
                "slide_id": "deck",
                "message": (
                    f"Deck visual density too low: {slides_with_visuals}/{slides_total} "
                    f"(minimum {min_visual_slides})."
                ),
            }
        )

    # Gate 6: require material use of image assets (not icon-only visuals).
    slides_with_image_assets = int(composition_metrics.get("slides_with_image_assets", 0))
    min_image_slides = max(1, math.ceil(slides_total * 0.2))
    checks["min_image_asset_presence"] = {
        "pass": slides_with_image_assets >= min_image_slides,
        "slides_with_image_assets": slides_with_image_assets,
        "min_required": min_image_slides,
    }
    if slides_with_image_assets < min_image_slides:
        issues.append(
            {
                "gate": "min_image_asset_presence",
                "slide_id": "deck",
                "message": (
                    f"Deck image usage too low: {slides_with_image_assets}/{slides_total} slides "
                    f"with image assets (minimum {min_image_slides})."
                ),
            }
        )

    # Gate 7: message contracts must be present and pre-validated when planning artifacts are provided.
    message_gate_payload = _evaluate_message_gate(
        deck=deck_v2,
        intent_briefs=intent_briefs or [],
        planning_validation=planning_validation or {},
    )
    checks["message_contract_alignment"] = message_gate_payload["check"]
    issues.extend(message_gate_payload["issues"])

    # Gate 8: planned structure should align with selected layouts.
    structure_gate_payload = _evaluate_structure_gate(
        deck=deck_v2,
        structure_plans=structure_plans or [],
    )
    checks["structure_layout_alignment"] = structure_gate_payload["check"]
    issues.extend(structure_gate_payload["issues"])

    # Gate 9: visual primitive plan should align with rendered composition.
    visual_gate_payload = _evaluate_visual_gate(
        deck=deck_v2,
        composition_spec=composition_spec_v2,
        visual_realization_plans=visual_realization_plans or [],
        image_capable_layouts=image_capable_layouts,
    )
    checks["visual_primitive_policy"] = visual_gate_payload["check"]
    issues.extend(visual_gate_payload["issues"])

    status = "PASS" if all(value.get("pass") for value in checks.values()) else "FAIL"
    return {"status": status, "checks": checks, "issues": issues}


def _is_image_target(field_key: str | None) -> bool:
    if not field_key:
        return True
    return field_key.startswith("ph_image")


def _index_diagnose_slides(diagnose_report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    by_slide_id: Dict[str, Dict[str, Any]] = {}
    for slide in diagnose_report.get("slides", []):
        slide_id = slide.get("deckir_slide_id")
        if isinstance(slide_id, str) and slide_id:
            by_slide_id[slide_id] = slide
    return by_slide_id


def _collect_unresolved_visual_slide_ids(run_log_path: Path) -> set[str]:
    unresolved: set[str] = set()
    if not run_log_path.exists():
        return unresolved
    for line in run_log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("event_type") != "VISUAL_CUE_UNRESOLVED":
            continue
        payload = record.get("payload", {})
        if isinstance(payload, dict):
            slide_id = payload.get("slide_id")
            if isinstance(slide_id, str) and slide_id:
                unresolved.add(slide_id)
    return unresolved


def _collect_hero_icon_violations(composition_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    violations: List[Dict[str, Any]] = []
    for slide in composition_spec.get("slides", []):
        slide_id = str(slide.get("slide_id", "unknown"))
        for visual in slide.get("visual_blocks", []):
            if visual.get("role") != "hero":
                continue
            asset_ref = visual.get("asset_ref", {})
            if not isinstance(asset_ref, dict):
                continue
            if asset_ref.get("asset_type") != "icon":
                continue
            violations.append(
                {
                    "slide_id": slide_id,
                    "target_field_key": visual.get("target_field_key"),
                    "asset_id": asset_ref.get("asset_id"),
                }
            )
    return violations


def _evaluate_message_gate(
    *,
    deck: DeckIR,
    intent_briefs: List[Dict[str, Any]],
    planning_validation: Dict[str, Any],
) -> Dict[str, Any]:
    if not intent_briefs:
        return {"check": {"pass": True, "coverage": "not_provided"}, "issues": []}

    issues: List[Dict[str, Any]] = []
    planning_status = str(planning_validation.get("status", "PASS"))
    if planning_status == "FAIL":
        issues.append(
            {
                "gate": "message_contract_alignment",
                "slide_id": "deck",
                "message": "Planning validation reported FAIL for message/structure/visual guardrails.",
            }
        )

    matched = 0
    for slide, intent in _pair_slides_with_plans(deck.slides, intent_briefs):
        if intent is None:
            issues.append(
                {
                    "gate": "message_contract_alignment",
                    "slide_id": slide.slide_id,
                    "message": "No intent brief available for slide.",
                }
            )
            continue
        matched += 1
        required_fields = intent.get("required_fields", [])
        for field_name in required_fields:
            if str(intent.get(field_name, "")).strip():
                continue
            issues.append(
                {
                    "gate": "message_contract_alignment",
                    "slide_id": slide.slide_id,
                    "message": f"Intent brief missing required field '{field_name}'.",
                    "details": {"section_id": intent.get("section_id")},
                }
            )
        title_text = str(slide.fields.get("ph_title", "")).strip()
        if not title_text:
            issues.append(
                {
                    "gate": "message_contract_alignment",
                    "slide_id": slide.slide_id,
                    "message": "Slide title is empty; bottom-line headline is required.",
                }
            )

    pass_check = not any(issue.get("gate") == "message_contract_alignment" for issue in issues)
    return {
        "check": {
            "pass": pass_check,
            "slides": len(deck.slides),
            "intent_briefs": len(intent_briefs),
            "matched": matched,
            "planning_status": planning_status,
        },
        "issues": issues,
    }


def _evaluate_structure_gate(
    *,
    deck: DeckIR,
    structure_plans: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not structure_plans:
        return {"check": {"pass": True, "coverage": "not_provided"}, "issues": []}

    issues: List[Dict[str, Any]] = []
    matched = 0
    for slide, plan in _pair_slides_with_plans(deck.slides, structure_plans):
        if plan is None:
            issues.append(
                {
                    "gate": "structure_layout_alignment",
                    "slide_id": slide.slide_id,
                    "message": "No structure plan available for slide.",
                }
            )
            continue
        matched += 1
        layout_candidates = [str(item) for item in plan.get("layout_candidate_ids", []) if str(item).strip()]
        if layout_candidates and slide.layout_id not in layout_candidates:
            issues.append(
                {
                    "gate": "structure_layout_alignment",
                    "slide_id": slide.slide_id,
                    "message": (
                        f"Selected layout '{slide.layout_id}' not in structure layout candidates: "
                        f"{', '.join(layout_candidates)}."
                    ),
                    "details": {"section_id": plan.get("section_id")},
                }
            )

    pass_check = not any(issue.get("gate") == "structure_layout_alignment" for issue in issues)
    return {
        "check": {
            "pass": pass_check,
            "slides": len(deck.slides),
            "structure_plans": len(structure_plans),
            "matched": matched,
        },
        "issues": issues,
    }


def _evaluate_visual_gate(
    *,
    deck: DeckIR,
    composition_spec: Dict[str, Any],
    visual_realization_plans: List[Dict[str, Any]],
    image_capable_layouts: List[str],
) -> Dict[str, Any]:
    if not visual_realization_plans:
        return {"check": {"pass": True, "coverage": "not_provided"}, "issues": []}

    issues: List[Dict[str, Any]] = []
    composition_by_slide = {
        str(slide.get("slide_id", "")): slide
        for slide in composition_spec.get("slides", [])
        if isinstance(slide, dict) and str(slide.get("slide_id", "")).strip()
    }
    matched = 0
    for slide, plan in _pair_slides_with_plans(deck.slides, visual_realization_plans):
        if plan is None:
            issues.append(
                {
                    "gate": "visual_primitive_policy",
                    "slide_id": slide.slide_id,
                    "message": "No visual realization plan available for slide.",
                }
            )
            continue
        matched += 1
        primitive_set = [str(item) for item in plan.get("primitive_set", []) if str(item).strip()]
        if not primitive_set:
            issues.append(
                {
                    "gate": "visual_primitive_policy",
                    "slide_id": slide.slide_id,
                    "message": "Visual realization plan primitive_set is empty.",
                }
            )
            continue
        composition_slide = composition_by_slide.get(slide.slide_id, {})
        visual_blocks = composition_slide.get("visual_blocks", [])
        if slide.layout_id in image_capable_layouts and not visual_blocks:
            issues.append(
                {
                    "gate": "visual_primitive_policy",
                    "slide_id": slide.slide_id,
                    "message": "Image-capable slide has no visual blocks after composition.",
                }
            )

    pass_check = not any(issue.get("gate") == "visual_primitive_policy" for issue in issues)
    return {
        "check": {
            "pass": pass_check,
            "slides": len(deck.slides),
            "visual_plans": len(visual_realization_plans),
            "matched": matched,
        },
        "issues": issues,
    }


def _pair_slides_with_plans(
    slides: List[Any], plans: List[Dict[str, Any]]
) -> List[tuple[Any, Dict[str, Any] | None]]:
    plans_by_section = {}
    for plan in plans:
        section_id = str(plan.get("section_id", "")).strip()
        if section_id:
            plans_by_section[section_id] = plan
    out: List[tuple[Any, Dict[str, Any] | None]] = []
    for idx, slide in enumerate(slides):
        direct = plans_by_section.get(slide.slide_id)
        if direct is not None:
            out.append((slide, direct))
            continue
        indexed = plans[idx] if idx < len(plans) else None
        out.append((slide, indexed))
    return out


def _collect_markdown_leaks(diagnose_report: Dict[str, Any]) -> List[Dict[str, Any]]:
    leaks: List[Dict[str, Any]] = []
    for slide in diagnose_report.get("slides", []):
        slide_id = str(slide.get("deckir_slide_id", f"slide_{slide.get('slide_index', '?')}"))
        text_shapes = slide.get("text_shapes_by_alt", {})
        if isinstance(text_shapes, dict):
            for field_key, info in text_shapes.items():
                preview = ""
                if isinstance(info, dict):
                    preview = str(info.get("text_preview", ""))
                marker = _find_markdown_marker(preview)
                if marker:
                    leaks.append(
                        {
                            "slide_id": slide_id,
                            "field_key": field_key,
                            "snippet": marker,
                        }
                    )
    return leaks


def _find_markdown_marker(text: str) -> str | None:
    if "**" in text:
        return "**"
    if "*" in text:
        return "*"
    return None
