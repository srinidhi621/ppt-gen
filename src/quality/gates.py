"""Deterministic quality gates for final deck validation."""

from __future__ import annotations

import json
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

    for slide in slides:
        visual_blocks = slide.get("visual_blocks", []) or []
        text_blocks = slide.get("text_blocks", []) or []
        notes_additions = slide.get("notes_additions", []) or []

        if visual_blocks:
            slides_with_visuals += 1
        total_visual_blocks += len(visual_blocks)
        slides_with_notes_additions += 1 if notes_additions else 0

        for visual in visual_blocks:
            asset_ref = visual.get("asset_ref", {}) if isinstance(visual, dict) else {}
            if (
                visual.get("role") == "hero"
                and isinstance(asset_ref, dict)
                and asset_ref.get("asset_type") == "icon"
            ):
                hero_icon_count += 1

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
    }


def evaluate_v2_quality_gates(
    *,
    deck_v2: DeckIR,
    validation_v2_post: ValidationReport,
    diagnose_report_v2: Dict[str, Any],
    composition_spec_v2: Dict[str, Any],
    image_capable_layouts: List[str],
    run_log_path: Path,
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
