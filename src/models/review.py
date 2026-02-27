"""Review feedback contracts for multimodal post-render critique."""

from __future__ import annotations

from typing import List, Literal

from pydantic import Field, constr

from .base import PptxBaseModel

NonEmptyStr = constr(min_length=1)
Severity = Literal["S0", "S1", "S2", "S3"]


class ReviewFinding(PptxBaseModel):
    slide_id: NonEmptyStr
    severity: Severity
    finding_type: NonEmptyStr
    expected: NonEmptyStr
    observed: NonEmptyStr
    evidence_refs: List[str] = Field(default_factory=list)


class ReviewChangeRequest(PptxBaseModel):
    target_stage: Literal["planner"] = "planner"
    instruction: NonEmptyStr
    constraint_refs: List[str] = Field(default_factory=list)
    must_preserve: List[str] = Field(default_factory=list)


class ReviewFeedback(PptxBaseModel):
    summary: NonEmptyStr
    slide_findings: List[ReviewFinding] = Field(default_factory=list)
    change_requests: List[ReviewChangeRequest] = Field(default_factory=list)
