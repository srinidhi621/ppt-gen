from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.llm.base import LLMResponse, LLMUsage
from src.llm.reviewer import review_rendered_deck_with_llm
from src.review.automation import collect_review_images


class _FakeReviewClient:
    provider = "azure_openai"
    model = "gpt-5.2"

    def generate_json(self, system_prompt: str, user_prompt: str):  # pragma: no cover - unused
        raise NotImplementedError

    def generate_json_with_images(self, system_prompt: str, user_prompt: str, image_paths):
        payload = {
            "summary": "overall acceptable with some issues",
            "slide_findings": [
                {
                    "slide_id": "s1",
                    "severity": "S1",
                    "finding_type": "visual_mismatch",
                    "expected": "branded hero image",
                    "observed": "stretched icon",
                    "evidence_refs": ["slide_001.png"],
                }
            ],
            "change_requests": [
                {
                    "target_stage": "planner",
                    "instruction": "Use branded image for hero slot on s1",
                    "constraint_refs": ["image-capable-layout"],
                    "must_preserve": ["title text"],
                }
            ],
        }
        usage = LLMUsage(
            provider=self.provider,
            model=self.model,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            estimated_cost_usd=0.01,
        )
        return LLMResponse(data=payload, usage=usage)


class TestReviewAutomation(unittest.TestCase):
    def test_collect_review_images_normalizes_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir)
            (out / "Slide 10.png").write_bytes(b"")
            (out / "Slide 2.PNG").write_bytes(b"")
            (out / "Slide 1.png").write_bytes(b"")

            images = collect_review_images(out, expected_count=3, min_width=1)

            self.assertEqual([p.name for p in images], ["slide_001.png", "slide_002.png", "slide_003.png"])


class TestReviewer(unittest.TestCase):
    def test_review_rendered_deck_with_llm_validates_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "slide_001.png"
            image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

            feedback, stats = review_rendered_deck_with_llm(
                client=_FakeReviewClient(),  # type: ignore[arg-type]
                run_id="run_1",
                deck_id="deck_1",
                content_markdown="# Title",
                cues_data={"cues": []},
                planner_deck_v1={"slides": []},
                composition_spec_v1={"slides": []},
                diagnose_report_v1={"summary": {}},
                capability_manifest={"layout_count": 1},
                image_paths=[image_path],
                max_retries=0,
            )

            self.assertEqual(feedback.slide_findings[0].slide_id, "s1")
            self.assertEqual(stats.total_tokens, 30)


if __name__ == "__main__":
    unittest.main()
