"""ValidationReport contracts."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import Field

from .base import PptxBaseModel

ValidationSeverity = Literal["BLOCKING", "WARN"]
ViolationType = Literal[
    "TITLE_TOO_LONG",
    "BODY_TOO_DENSE",
    "TOO_MANY_BULLETS",
    "WORDS_PER_BULLET",
    "TOTAL_BODY_CHARS",
    "BODY_LINE_BUDGET",
]


class ValidationViolation(PptxBaseModel):
    slide_id: str
    layout_id: str
    field_key: Optional[str] = None
    violation_type: ViolationType
    severity: ValidationSeverity
    recommended_action: Optional[str] = None


class ValidationReport(PptxBaseModel):
    violations: List[ValidationViolation] = Field(default_factory=list)
