"""Multimodal post-render review loop support."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import ValidationError

from ..models.review import ReviewFeedback
from .base import LLMClient, LLMClientError, LLMUsage


class ReviewerError(RuntimeError):
    """Raised when multimodal review fails across retries."""


@dataclass
class ReviewStats:
    provider: str
    model: str
    attempts: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None
    usage_by_attempt: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "attempts": self.attempts,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "usage_by_attempt": self.usage_by_attempt,
        }


def review_rendered_deck_with_llm(
    *,
    client: LLMClient,
    run_id: str,
    deck_id: str,
    content_markdown: str,
    cues_data: Dict[str, Any],
    planner_deck_v1: Dict[str, Any],
    composition_spec_v1: Dict[str, Any],
    diagnose_report_v1: Dict[str, Any],
    capability_manifest: Dict[str, Any],
    image_paths: List[Path],
    max_retries: int = 1,
) -> Tuple[ReviewFeedback, ReviewStats]:
    system_prompt = _build_review_system_prompt()
    user_prompt = _build_review_user_prompt(
        run_id=run_id,
        deck_id=deck_id,
        content_markdown=content_markdown,
        cues_data=cues_data,
        planner_deck_v1=planner_deck_v1,
        composition_spec_v1=composition_spec_v1,
        diagnose_report_v1=diagnose_report_v1,
        capability_manifest=capability_manifest,
    )

    attempts = max_retries + 1
    usage_records: List[LLMUsage] = []
    errors: List[str] = []
    for attempt in range(1, attempts + 1):
        try:
            response = client.generate_json_with_images(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                image_paths=image_paths,
            )
            if response.usage is not None:
                usage_records.append(response.usage)
            feedback = ReviewFeedback.model_validate(response.data)
            return feedback, _aggregate_review_stats(client, attempt, usage_records)
        except (LLMClientError, ValidationError, ValueError) as exc:
            errors.append(f"attempt {attempt}: {exc}")

    raise ReviewerError("Multimodal review failed after retries: " + " | ".join(errors))


def _aggregate_review_stats(
    client: LLMClient, attempts_used: int, usage_records: List[LLMUsage]
) -> ReviewStats:
    prompt_tokens = sum(u.prompt_tokens for u in usage_records)
    completion_tokens = sum(u.completion_tokens for u in usage_records)
    total_tokens = sum(u.total_tokens for u in usage_records)
    known_costs = [u.estimated_cost_usd for u in usage_records if u.estimated_cost_usd is not None]
    estimated_cost_usd = round(sum(known_costs), 8) if known_costs else None
    return ReviewStats(
        provider=getattr(client, "provider", "unknown"),
        model=getattr(client, "model", "unknown"),
        attempts=attempts_used,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost_usd,
        usage_by_attempt=[u.to_dict() for u in usage_records],
    )


def _build_review_system_prompt() -> str:
    return (
        "You are a slide quality reviewer for an automated PPTX pipeline. "
        "Use both structured diagnostics and slide images. "
        "Output ONLY valid JSON that matches the required schema. "
        "Do not include markdown fences or commentary.\n\n"
        "Required top-level keys:\n"
        "- summary (string)\n"
        "- slide_findings (array of objects with: slide_id, severity[S0|S1|S2|S3], "
        "finding_type, expected, observed, evidence_refs[])\n"
        "- change_requests (array of objects with: target_stage='planner', instruction, "
        "constraint_refs[], must_preserve[])\n\n"
        "Review policy:\n"
        "1. Prioritize critical issues: missing/weak visuals, overflow, hierarchy, density, layout mismatch.\n"
        "2. Keep recommendations feasible within provided capability manifest.\n"
        "3. Recommend concrete planner-level changes with slide_id references.\n"
        "4. If a slide is acceptable, omit it from findings.\n"
    )


def _build_review_user_prompt(
    *,
    run_id: str,
    deck_id: str,
    content_markdown: str,
    cues_data: Dict[str, Any],
    planner_deck_v1: Dict[str, Any],
    composition_spec_v1: Dict[str, Any],
    diagnose_report_v1: Dict[str, Any],
    capability_manifest: Dict[str, Any],
) -> str:
    return (
        f"Run ID: {run_id}\n"
        f"Deck ID: {deck_id}\n"
        "You are reviewing Version V1 and should propose planner-level rework instructions for V2.\n\n"
        "=== ORIGINAL CONTENT (MARKDOWN) ===\n"
        f"{content_markdown}\n\n"
        "=== VISUALIZATION CUES JSON ===\n"
        f"{json.dumps(cues_data, ensure_ascii=True)}\n\n"
        "=== PLANNER OUTPUT V1 ===\n"
        f"{json.dumps(planner_deck_v1, ensure_ascii=True)}\n\n"
        "=== COMPOSITION OUTPUT V1 ===\n"
        f"{json.dumps(composition_spec_v1, ensure_ascii=True)}\n\n"
        "=== DIAGNOSE REPORT V1 ===\n"
        f"{json.dumps(diagnose_report_v1, ensure_ascii=True)}\n\n"
        "=== CAPABILITY MANIFEST ===\n"
        f"{json.dumps(capability_manifest, ensure_ascii=True)}\n\n"
        "Images attached are the rendered slides in order. Use image evidence plus diagnostics together."
    )
