"""CritiqueReport contracts."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import Field

from .base import PptxBaseModel

CritiqueSeverity = Literal["S0", "S1", "S2", "S3"]
CritiqueFindingType = Literal[
    "OVERFLOW_RISK",
    "DENSITY_HIGH",
    "HIERARCHY_WEAK",
    "VISUAL_MISMATCH",
    "WHITESPACE_ISSUE",
]


class CritiqueFinding(PptxBaseModel):
    slide_id: str
    finding_type: CritiqueFindingType
    severity: CritiqueSeverity
    affected_field_keys: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class CritiqueReport(PptxBaseModel):
    findings: List[CritiqueFinding] = Field(default_factory=list)
