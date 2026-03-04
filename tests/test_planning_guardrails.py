"""Tests for deterministic planning guardrails."""

from __future__ import annotations

import unittest
from pathlib import Path

from src.assets import load_visual_primitive_policy
from src.normalize.parser import parse_markdown_string
from src.planning import build_planning_bundle, validate_planning_bundle


class TestPlanningGuardrails(unittest.TestCase):
    def test_build_planning_bundle_generates_artifacts(self) -> None:
        content = """# Deck

---
<!-- section_id: exec_summary -->
## Executive Summary
- We can reduce operating cost by 20% in two quarters
- Delivery risk is controlled through phased rollout

---
<!-- section_id: solution_approach -->
## Solution Approach
- Establish baseline
- Build target architecture
- Execute in three phases
"""
        model = parse_markdown_string(content, doc_id="guardrails_doc")
        cues = {
            "cues": [
                {"section_id": "exec_summary", "notes": "RFP response summary"},
                {"section_id": "solution_approach", "notes": "Use process visual"},
            ]
        }
        project_root = Path(__file__).resolve().parents[1]
        bundle = build_planning_bundle(
            content_model=model,
            cues_data=cues,
            layout_catalog_path=project_root / "assets" / "layout" / "layout_catalog.json",
            assets_dir=project_root / "assets",
        )

        self.assertEqual(len(bundle.intent_briefs), 2)
        self.assertEqual(len(bundle.structure_plans), 2)
        self.assertEqual(len(bundle.visual_realization_plans), 2)
        self.assertEqual(bundle.validation.status, "PASS")
        self.assertIn("planner_context", bundle.to_dict())

    def test_validate_planning_bundle_flags_missing_required_message_field(self) -> None:
        content = """# Deck

---
<!-- section_id: slide_a -->
## Strategy Priorities
- Focus on value pools
"""
        model = parse_markdown_string(content, doc_id="guardrails_doc")
        project_root = Path(__file__).resolve().parents[1]
        bundle = build_planning_bundle(
            content_model=model,
            cues_data={"cues": []},
            layout_catalog_path=project_root / "assets" / "layout" / "layout_catalog.json",
            assets_dir=project_root / "assets",
        )
        bundle.intent_briefs[0].bottom_line = ""
        report = validate_planning_bundle(
            intent_briefs=bundle.intent_briefs,
            structure_plans=bundle.structure_plans,
            visual_plans=bundle.visual_realization_plans,
            primitive_policy=load_visual_primitive_policy(project_root / "assets"),
        )
        self.assertEqual(report.status, "FAIL")
        self.assertTrue(
            any(issue.issue_type == "MISSING_REQUIRED_FIELD" for issue in report.issues)
        )


if __name__ == "__main__":
    unittest.main()
