"""Deterministic planning guardrails for message, structure, and visuals."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from ..assets import load_archetype_message_contracts, load_visual_primitive_policy
from ..models.content import ContentModel, ContentSection
from ..models.planning import (
    DeckLinkage,
    DensityBudget,
    EvidenceRequirement,
    PlanningBundle,
    PlanningValidationIssue,
    PlanningValidationReport,
    SlideIntentBrief,
    SlideStructurePlan,
    StructureInformationBlock,
    VisualBinding,
    VisualRealizationPlan,
)

DEFAULT_REQUIRED_FIELDS = [
    "core_theme",
    "bottom_line",
    "audience_takeaway",
    "speaker_intent",
]

PATTERN_LAYOUT_PREFERENCES: Dict[str, List[str]] = {
    "claim_support": ["statement_light", "one_content_light", "content_image_light"],
    "comparison": ["two_content_light", "comparison_light", "two_content_image_light"],
    "timeline": ["agenda_light", "three_content_light", "content_image_light"],
    "process": ["three_content_light", "content_image_light", "one_content_light"],
    "kpi_summary": ["two_content_light", "content_image_light", "one_content_light"],
    "option_matrix": ["two_content_light", "four_content_light", "content_image_light"],
    "problem_solution": ["two_content_light", "content_image_light", "one_content_light"],
    "status_update": ["kpi_dashboard_light", "two_content_light", "one_content_light"],
}

PATTERN_PRIMITIVES: Dict[str, List[str]] = {
    "claim_support": ["shape_cluster", "icon_label_grid", "text_callout"],
    "comparison": ["matrix_grid", "table", "icon_label_grid"],
    "timeline": ["timeline_stepper", "shape_cluster", "icon_label_grid"],
    "process": ["smartart_like_flow", "shape_cluster", "icon_label_grid"],
    "kpi_summary": ["chart", "table", "text_callout"],
    "option_matrix": ["matrix_grid", "chart", "table"],
    "problem_solution": ["shape_cluster", "icon_label_grid", "text_callout"],
    "status_update": ["chart", "table", "text_callout"],
}


def build_planning_bundle(
    *,
    content_model: ContentModel,
    cues_data: Dict[str, Any],
    layout_catalog_path: Path,
    assets_dir: Path,
) -> PlanningBundle:
    """Build deterministic planning artifacts and validation report."""
    layout_ids = _load_layout_ids(layout_catalog_path)
    contract_payload = load_archetype_message_contracts(assets_dir)
    primitive_policy = load_visual_primitive_policy(assets_dir)
    contracts = _as_contract_list(contract_payload.get("archetypes", []))
    default_contract = _default_contract(contracts)
    cues_by_section = _cues_by_section(cues_data)

    intent_briefs: List[SlideIntentBrief] = []
    structure_plans: List[SlideStructurePlan] = []
    visual_plans: List[VisualRealizationPlan] = []

    for idx, section in enumerate(content_model.sections):
        cue = cues_by_section.get(section.section_id, {})
        contract = _select_contract(section=section, cue=cue, contracts=contracts, default_contract=default_contract)
        archetype_id = str(contract.get("archetype_id", "general_story"))
        required_fields = _required_fields(contract)
        core_theme = _core_theme(section)
        bottom_line = _bottom_line(section)
        brief = SlideIntentBrief(
            section_id=section.section_id,
            archetype_id=archetype_id,
            required_fields=required_fields,
            core_theme=core_theme,
            bottom_line=bottom_line,
            audience_takeaway=f"Audience should retain: {bottom_line}",
            speaker_intent=_speaker_intent(contract, bottom_line),
            deck_linkage=_deck_linkage(content_model.sections, idx),
        )
        narrative_pattern = _narrative_pattern(
            section=section,
            cue=cue,
            default_pattern=str(contract.get("default_narrative_pattern", "claim_support")),
        )
        density_budget = _density_budget(contract)
        structure_plan = _build_structure_plan(
            section=section,
            archetype_id=archetype_id,
            bottom_line=bottom_line,
            narrative_pattern=narrative_pattern,
            density_budget=density_budget,
            contract=contract,
            layout_ids=layout_ids,
        )
        visual_plan = _build_visual_plan(
            structure_plan=structure_plan,
            primitive_policy=primitive_policy,
        )
        intent_briefs.append(brief)
        structure_plans.append(structure_plan)
        visual_plans.append(visual_plan)

    validation = validate_planning_bundle(
        intent_briefs=intent_briefs,
        structure_plans=structure_plans,
        visual_plans=visual_plans,
        primitive_policy=primitive_policy,
    )
    planner_context = {
        "intent_briefs": [brief.to_dict() for brief in intent_briefs],
        "structure_plans": [plan.to_dict() for plan in structure_plans],
        "visual_realization_plans": [plan.to_dict() for plan in visual_plans],
        "planning_validation": validation.to_dict(),
        "structure_mode": "llm_first_guardrails",
        "visual_policy": "insert_primitives_plus_curated_icons",
    }

    return PlanningBundle(
        intent_briefs=intent_briefs,
        structure_plans=structure_plans,
        visual_realization_plans=visual_plans,
        validation=validation,
        planner_context=planner_context,
    )


def validate_planning_bundle(
    *,
    intent_briefs: Sequence[SlideIntentBrief],
    structure_plans: Sequence[SlideStructurePlan],
    visual_plans: Sequence[VisualRealizationPlan],
    primitive_policy: Dict[str, Any],
) -> PlanningValidationReport:
    """Validate deterministic planning artifacts before rendering."""
    issues: List[PlanningValidationIssue] = []
    allowed_primitives = set(str(item) for item in primitive_policy.get("allowed_primitives", []))
    max_primitives = int(primitive_policy.get("max_primitives_per_slide", 3))

    for brief in intent_briefs:
        for field_name in brief.required_fields:
            value = getattr(brief, field_name, "")
            if str(value).strip():
                continue
            issues.append(
                PlanningValidationIssue(
                    section_id=brief.section_id,
                    stage="message",
                    severity="BLOCKING",
                    issue_type="MISSING_REQUIRED_FIELD",
                    message=f"Required message field '{field_name}' is empty.",
                )
            )

    for plan in structure_plans:
        if not plan.layout_candidate_ids:
            issues.append(
                PlanningValidationIssue(
                    section_id=plan.section_id,
                    stage="structure",
                    severity="BLOCKING",
                    issue_type="NO_LAYOUT_CANDIDATE",
                    message="No layout candidates were generated for this section.",
                )
            )
        if len(plan.information_blocks) > plan.density_budget.max_blocks:
            issues.append(
                PlanningValidationIssue(
                    section_id=plan.section_id,
                    stage="structure",
                    severity="BLOCKING",
                    issue_type="BLOCK_COUNT_OVER_BUDGET",
                    message=(
                        f"Information blocks exceed budget: {len(plan.information_blocks)} > "
                        f"{plan.density_budget.max_blocks}."
                    ),
                )
            )
        bullet_count = _bullet_count(plan.information_blocks)
        if bullet_count > plan.density_budget.max_bullets:
            issues.append(
                PlanningValidationIssue(
                    section_id=plan.section_id,
                    stage="structure",
                    severity="BLOCKING",
                    issue_type="BULLET_COUNT_OVER_BUDGET",
                    message=(
                        f"Body bullets exceed budget: {bullet_count} > "
                        f"{plan.density_budget.max_bullets}."
                    ),
                )
            )
        word_count = _word_count(plan.information_blocks)
        if word_count > plan.density_budget.max_words:
            issues.append(
                PlanningValidationIssue(
                    section_id=plan.section_id,
                    stage="structure",
                    severity="WARN",
                    issue_type="WORD_COUNT_OVER_BUDGET",
                    message=(
                        f"Estimated words exceed budget: {word_count} > "
                        f"{plan.density_budget.max_words}."
                    ),
                )
            )

    for plan in visual_plans:
        if not plan.primitive_set:
            issues.append(
                PlanningValidationIssue(
                    section_id=plan.section_id,
                    stage="visual",
                    severity="BLOCKING",
                    issue_type="NO_PRIMITIVE_SET",
                    message="Visual realization primitive set is empty.",
                )
            )
        disallowed = [primitive for primitive in plan.primitive_set if primitive not in allowed_primitives]
        if disallowed:
            issues.append(
                PlanningValidationIssue(
                    section_id=plan.section_id,
                    stage="visual",
                    severity="BLOCKING",
                    issue_type="DISALLOWED_PRIMITIVE",
                    message=f"Disallowed primitive types: {', '.join(sorted(disallowed))}.",
                )
            )
        if len(set(plan.primitive_set)) > max_primitives:
            issues.append(
                PlanningValidationIssue(
                    section_id=plan.section_id,
                    stage="visual",
                    severity="BLOCKING",
                    issue_type="PRIMITIVE_OVERUSE",
                    message=(
                        f"Too many primitive families: {len(set(plan.primitive_set))} > "
                        f"{max_primitives}."
                    ),
                )
            )
        if not plan.binding_map:
            issues.append(
                PlanningValidationIssue(
                    section_id=plan.section_id,
                    stage="visual",
                    severity="WARN",
                    issue_type="MISSING_BINDINGS",
                    message="No visual bindings were generated for structure blocks.",
                )
            )

    has_blocking = any(issue.severity == "BLOCKING" for issue in issues)
    return PlanningValidationReport(status="FAIL" if has_blocking else "PASS", issues=issues)


def _as_contract_list(contracts: Sequence[Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for contract in contracts:
        if isinstance(contract, dict):
            out.append(contract)
    return out


def _default_contract(contracts: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    for contract in contracts:
        if contract.get("archetype_id") == "general_story":
            return contract
    if contracts:
        return contracts[0]
    return {
        "archetype_id": "general_story",
        "keywords": [],
        "required_fields": DEFAULT_REQUIRED_FIELDS,
        "default_narrative_pattern": "claim_support",
        "density_budget": {"max_words": 90, "max_blocks": 4, "max_bullets": 5},
        "layout_preferences": ["one_content_light", "content_image_light"],
    }


def _select_contract(
    *,
    section: ContentSection,
    cue: Dict[str, Any],
    contracts: Sequence[Dict[str, Any]],
    default_contract: Dict[str, Any],
) -> Dict[str, Any]:
    hint = str(cue.get("archetype_hint", "")).strip()
    if hint:
        for contract in contracts:
            if str(contract.get("archetype_id", "")) == hint:
                return contract

    text = " ".join(
        filter(
            None,
            [
                section.title,
                " ".join(section.bullets),
                " ".join(section.paragraphs),
                str(cue.get("notes", "")),
            ],
        )
    )
    tokens = set(_tokenize(text))
    if not tokens:
        return default_contract

    best_contract = default_contract
    best_score = 0
    for contract in contracts:
        keywords = set(_tokenize(" ".join(str(item) for item in contract.get("keywords", []))))
        score = len(tokens & keywords)
        if score > best_score:
            best_contract = contract
            best_score = score
    return best_contract


def _required_fields(contract: Dict[str, Any]) -> List[str]:
    required = [str(field) for field in contract.get("required_fields", []) if str(field).strip()]
    return required or DEFAULT_REQUIRED_FIELDS


def _core_theme(section: ContentSection) -> str:
    return section.title.strip()


def _bottom_line(section: ContentSection) -> str:
    for source in (section.bullets, section.paragraphs):
        for item in source:
            text = str(item).strip()
            if text:
                return _ensure_terminal_period(text)
    return _ensure_terminal_period(section.title.strip())


def _speaker_intent(contract: Dict[str, Any], bottom_line: str) -> str:
    template = str(contract.get("speaker_intent_template", "")).strip()
    if template:
        return template.replace("{bottom_line}", bottom_line)
    return f"Land this bottom line with confidence: {bottom_line}"


def _deck_linkage(sections: Sequence[ContentSection], index: int) -> DeckLinkage:
    prev_context = sections[index - 1].title if index > 0 else ""
    next_setup = sections[index + 1].title if index + 1 < len(sections) else ""
    return DeckLinkage(prev_context=prev_context, next_setup=next_setup)


def _narrative_pattern(*, section: ContentSection, cue: Dict[str, Any], default_pattern: str) -> str:
    combined = " ".join(
        filter(
            None,
            [section.title, " ".join(section.bullets), " ".join(section.paragraphs), str(cue.get("notes", ""))],
        )
    )
    text = combined.lower()
    if any(token in text for token in ("timeline", "roadmap", "phase", "milestone")):
        return "timeline"
    if any(token in text for token in ("compare", "versus", "vs", "tradeoff", "option")):
        return "comparison"
    if any(token in text for token in ("kpi", "metric", "quarter", "qbr", "performance")):
        return "kpi_summary"
    if any(token in text for token in ("process", "workflow", "step", "journey")):
        return "process"
    if any(token in text for token in ("matrix", "prioritization", "prioritise", "prioritize")):
        return "option_matrix"
    if any(token in text for token in ("problem", "solution", "approach", "strategy")):
        return "problem_solution"
    if any(token in text for token in ("status", "update", "progress")):
        return "status_update"
    return default_pattern if default_pattern in PATTERN_LAYOUT_PREFERENCES else "claim_support"


def _density_budget(contract: Dict[str, Any]) -> DensityBudget:
    budget = contract.get("density_budget", {})
    try:
        max_words = int(budget.get("max_words", 90))
        max_blocks = int(budget.get("max_blocks", 4))
        max_bullets = int(budget.get("max_bullets", 5))
    except (TypeError, ValueError):
        max_words, max_blocks, max_bullets = 90, 4, 5
    return DensityBudget(
        max_words=max(30, max_words),
        max_blocks=max(2, max_blocks),
        max_bullets=max(2, max_bullets),
    )


def _build_structure_plan(
    *,
    section: ContentSection,
    archetype_id: str,
    bottom_line: str,
    narrative_pattern: str,
    density_budget: DensityBudget,
    contract: Dict[str, Any],
    layout_ids: Sequence[str],
) -> SlideStructurePlan:
    blocks: List[StructureInformationBlock] = [
        StructureInformationBlock(
            block_id="headline",
            block_type="headline",
            content=bottom_line,
        )
    ]

    if section.paragraphs:
        blocks.append(
            StructureInformationBlock(
                block_id="context",
                block_type="context",
                content=section.paragraphs[0],
            )
        )

    if section.bullets:
        blocks.append(
            StructureInformationBlock(
                block_id="body_points",
                block_type="body_points",
                content=section.bullets[: density_budget.max_bullets],
            )
        )
    elif len(section.paragraphs) > 1:
        blocks.append(
            StructureInformationBlock(
                block_id="body_points",
                block_type="body_points",
                content=section.paragraphs[1 : 1 + density_budget.max_bullets],
            )
        )

    evidence_type = _evidence_type_for_pattern(narrative_pattern)
    if evidence_type != "none":
        blocks.append(
            StructureInformationBlock(
                block_id="evidence",
                block_type="evidence",
                content=f"Support with {evidence_type.replace('_', ' ')}.",
            )
        )

    if archetype_id in {"rfp_response", "strategy", "qbr"}:
        blocks.append(
            StructureInformationBlock(
                block_id="decision",
                block_type="decision",
                content="Confirm decision, owner, and next action.",
            )
        )

    while len(blocks) > density_budget.max_blocks:
        removable_idx = next(
            (idx for idx, block in enumerate(blocks) if block.block_type in {"context", "decision", "evidence"}),
            None,
        )
        if removable_idx is None:
            blocks = blocks[: density_budget.max_blocks]
            break
        del blocks[removable_idx]

    layout_preferences = [str(item) for item in contract.get("layout_preferences", [])]
    layout_candidates = _resolve_layout_candidates(
        narrative_pattern=narrative_pattern,
        layout_preferences=layout_preferences,
        layout_ids=layout_ids,
    )
    evidence_map = [
        EvidenceRequirement(
            block_id="evidence",
            evidence_type=_evidence_type_for_pattern(narrative_pattern),
            required=_evidence_type_for_pattern(narrative_pattern) != "none",
        )
    ]
    return SlideStructurePlan(
        section_id=section.section_id,
        archetype_id=archetype_id,
        narrative_pattern=narrative_pattern,  # type: ignore[arg-type]
        information_blocks=blocks,
        density_budget=density_budget,
        evidence_map=evidence_map,
        layout_candidate_ids=layout_candidates,
    )


def _resolve_layout_candidates(
    *,
    narrative_pattern: str,
    layout_preferences: Sequence[str],
    layout_ids: Sequence[str],
) -> List[str]:
    preferred = [layout for layout in layout_preferences if layout in layout_ids]
    pattern_defaults = [layout for layout in PATTERN_LAYOUT_PREFERENCES.get(narrative_pattern, []) if layout in layout_ids]
    merged: List[str] = []
    for layout in preferred + pattern_defaults + ["one_content_light", "content_image_light"]:
        if layout in layout_ids and layout not in merged:
            merged.append(layout)
    return merged[:4]


def _build_visual_plan(
    *,
    structure_plan: SlideStructurePlan,
    primitive_policy: Dict[str, Any],
) -> VisualRealizationPlan:
    allowed_primitives = [str(item) for item in primitive_policy.get("allowed_primitives", [])]
    max_primitives = int(primitive_policy.get("max_primitives_per_slide", 3))
    defaults = PATTERN_PRIMITIVES.get(structure_plan.narrative_pattern, PATTERN_PRIMITIVES["claim_support"])
    primitive_set = [primitive for primitive in defaults if primitive in allowed_primitives]
    if not primitive_set and allowed_primitives:
        primitive_set = [allowed_primitives[0]]
    primitive_set = primitive_set[: max(1, max_primitives)]

    bindings: List[VisualBinding] = []
    if primitive_set:
        has_evidence = any(block.block_type == "evidence" for block in structure_plan.information_blocks)
        has_body = any(block.block_type == "body_points" for block in structure_plan.information_blocks)
        if has_evidence:
            bindings.append(
                VisualBinding(
                    block_id="evidence",
                    primitive_type=primitive_set[0],  # type: ignore[arg-type]
                    target_field_key="ph_image",
                )
            )
        elif has_body:
            bindings.append(
                VisualBinding(
                    block_id="body_points",
                    primitive_type=primitive_set[0],  # type: ignore[arg-type]
                    target_field_key="ph_image",
                )
            )
        if "text_callout" in primitive_set:
            bindings.append(
                VisualBinding(
                    block_id="headline",
                    primitive_type="text_callout",
                    target_field_key="ph_title",
                )
            )

    return VisualRealizationPlan(
        section_id=structure_plan.section_id,
        archetype_id=structure_plan.archetype_id,
        primitive_set=primitive_set,  # type: ignore[arg-type]
        binding_map=bindings,
        style_tokens={
            str(key): str(value)
            for key, value in primitive_policy.get("style_tokens", {}).items()
            if str(key).strip()
        },
        declutter_rules_applied=[
            str(rule) for rule in primitive_policy.get("declutter_rules", []) if str(rule).strip()
        ],
    )


def _load_layout_ids(layout_catalog_path: Path) -> List[str]:
    payload = json.loads(layout_catalog_path.read_text(encoding="utf-8"))
    out: List[str] = []
    for entry in payload.get("layouts", []):
        layout_id = str(entry.get("layout_id", "")).strip()
        if layout_id:
            out.append(layout_id)
    return out


def _cues_by_section(cues_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for cue in cues_data.get("cues", []):
        if not isinstance(cue, dict):
            continue
        section_id = str(cue.get("section_id", "")).strip()
        if not section_id:
            continue
        out[section_id] = cue
    return out


def _evidence_type_for_pattern(narrative_pattern: str) -> str:
    if narrative_pattern in {"kpi_summary"}:
        return "chart"
    if narrative_pattern in {"comparison", "option_matrix"}:
        return "table"
    if narrative_pattern in {"timeline", "process"}:
        return "timeline"
    return "none"


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _ensure_terminal_period(text: str) -> str:
    trimmed = text.strip()
    if not trimmed:
        return ""
    if trimmed[-1] in {".", "!", "?"}:
        return trimmed
    return f"{trimmed}."


def _word_count(blocks: Iterable[StructureInformationBlock]) -> int:
    total = 0
    for block in blocks:
        if isinstance(block.content, list):
            total += sum(len(str(item).split()) for item in block.content)
        else:
            total += len(str(block.content).split())
    return total


def _bullet_count(blocks: Iterable[StructureInformationBlock]) -> int:
    total = 0
    for block in blocks:
        if block.block_type != "body_points":
            continue
        if isinstance(block.content, list):
            total += len(block.content)
        elif str(block.content).strip():
            total += 1
    return total
