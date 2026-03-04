"""Planning contracts for message, structure, and visual realization."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Union

from pydantic import Field

from .base import PptxBaseModel

NarrativePattern = Literal[
    "claim_support",
    "comparison",
    "timeline",
    "process",
    "kpi_summary",
    "option_matrix",
    "problem_solution",
    "status_update",
]

EvidenceType = Literal["none", "metric", "example", "timeline", "table", "chart", "proof_point"]
PrimitiveType = Literal[
    "table",
    "chart",
    "shape_cluster",
    "icon_label_grid",
    "smartart_like_flow",
    "matrix_grid",
    "timeline_stepper",
    "text_callout",
]
PlanningSeverity = Literal["BLOCKING", "WARN"]
PlanningStage = Literal["message", "structure", "visual"]


class DeckLinkage(PptxBaseModel):
    prev_context: str = ""
    next_setup: str = ""


class SlideIntentBrief(PptxBaseModel):
    section_id: str
    archetype_id: str
    required_fields: List[str] = Field(default_factory=list)
    core_theme: str
    bottom_line: str
    audience_takeaway: str
    speaker_intent: str
    deck_linkage: DeckLinkage = Field(default_factory=DeckLinkage)


class StructureInformationBlock(PptxBaseModel):
    block_id: str
    block_type: Literal[
        "headline",
        "context",
        "body_points",
        "evidence",
        "implication",
        "decision",
    ]
    content: Union[str, List[str]]


class EvidenceRequirement(PptxBaseModel):
    block_id: str
    evidence_type: EvidenceType = "none"
    required: bool = False


class DensityBudget(PptxBaseModel):
    max_words: int = 90
    max_blocks: int = 4
    max_bullets: int = 5


class SlideStructurePlan(PptxBaseModel):
    section_id: str
    archetype_id: str
    narrative_pattern: NarrativePattern
    information_blocks: List[StructureInformationBlock] = Field(default_factory=list)
    density_budget: DensityBudget = Field(default_factory=DensityBudget)
    evidence_map: List[EvidenceRequirement] = Field(default_factory=list)
    layout_candidate_ids: List[str] = Field(default_factory=list)


class VisualBinding(PptxBaseModel):
    block_id: str
    primitive_type: PrimitiveType
    target_field_key: str


class VisualRealizationPlan(PptxBaseModel):
    section_id: str
    archetype_id: str
    primitive_set: List[PrimitiveType] = Field(default_factory=list)
    binding_map: List[VisualBinding] = Field(default_factory=list)
    style_tokens: Dict[str, str] = Field(default_factory=dict)
    declutter_rules_applied: List[str] = Field(default_factory=list)


class PlanningValidationIssue(PptxBaseModel):
    section_id: str
    stage: PlanningStage
    severity: PlanningSeverity
    issue_type: str
    message: str


class PlanningValidationReport(PptxBaseModel):
    status: Literal["PASS", "FAIL"]
    issues: List[PlanningValidationIssue] = Field(default_factory=list)


class PlanningBundle(PptxBaseModel):
    intent_briefs: List[SlideIntentBrief] = Field(default_factory=list)
    structure_plans: List[SlideStructurePlan] = Field(default_factory=list)
    visual_realization_plans: List[VisualRealizationPlan] = Field(default_factory=list)
    validation: PlanningValidationReport
    planner_context: Dict[str, Any] = Field(default_factory=dict)
