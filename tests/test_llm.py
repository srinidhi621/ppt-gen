"""Tests for Gemini-based LLM planning layer."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from src.llm.base import LLMResponse, LLMUsage
from src.llm.env import load_dotenv
from src.llm.planner import PlannerError, plan_deck_with_gemini
from src.models.content import ContentModel, ContentSection


class _FakeGeminiClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def generate_json(self, system_prompt: str, user_prompt: str):
        self.calls += 1
        return LLMResponse(
            data=self.payload,
            usage=LLMUsage(
                provider="gemini",
                model="gemini-2.5-flash",
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30,
                estimated_cost_usd=0.00005,
            ),
        )


class TestDotenvLoader(unittest.TestCase):
    def test_load_dotenv_sets_missing_env_vars(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dotenv_path = Path(temp_dir) / ".env"
            dotenv_path.write_text("GEMINI_API_KEY=test-key\nGEMINI_MODEL=gemini-3.0-flash\n")
            os.environ.pop("GEMINI_API_KEY", None)
            os.environ.pop("GEMINI_MODEL", None)

            loaded = load_dotenv(dotenv_path)

            self.assertEqual(loaded["GEMINI_API_KEY"], "test-key")
            self.assertEqual(os.environ["GEMINI_MODEL"], "gemini-3.0-flash")


class TestGeminiPlanner(unittest.TestCase):
    def test_plan_deck_with_valid_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            layout_path = root / "layout.json"
            icons_path = root / "icons.json"
            layout_path.write_text(
                '{"layouts":[{"layout_id":"one_content_light","fields":[{"field_key":"ph_title"},{"field_key":"ph_body"}]}]}',
                encoding="utf-8",
            )
            icons_path.write_text('{"icons":[{"icon_id":"ic_1"}]}', encoding="utf-8")

            model = ContentModel(
                doc_id="doc1",
                version="1.0",
                source_hash="hash1",
                sections=[ContentSection(section_id="s1", title="Title", bullets=["One"])],
            )

            fake = _FakeGeminiClient(
                {
                    "deck_id": "deck_1",
                    "run_id": "run_1",
                    "template_id": "corp_deck_2025",
                    "title": "Title",
                    "subtitle": None,
                    "global_constraints": {},
                    "slides": [
                        {
                            "slide_id": "s1",
                            "layout_id": "one_content_light",
                            "fields": {"ph_title": "Title", "ph_body": ["One"]},
                            "speaker_notes": "",
                            "asset_refs": [],
                            "constraints_override": None,
                        }
                    ],
                }
            )

            deck, stats = plan_deck_with_gemini(
                client=fake,  # type: ignore[arg-type]
                content_model=model,
                cues_data={"cues": []},
                layout_catalog_path=layout_path,
                icons_json_path=icons_path,
                run_id="run_1",
                deck_id="deck_1",
            )

            self.assertEqual(deck.deck_id, "deck_1")
            self.assertEqual(stats.attempts, 1)
            self.assertEqual(stats.total_tokens, 30)
            self.assertEqual(fake.calls, 1)

    def test_plan_deck_rejects_invalid_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            layout_path = root / "layout.json"
            icons_path = root / "icons.json"
            layout_path.write_text(
                '{"layouts":[{"layout_id":"one_content_light","fields":[{"field_key":"ph_title"}]}]}',
                encoding="utf-8",
            )
            icons_path.write_text('{"icons":[]}', encoding="utf-8")

            model = ContentModel(
                doc_id="doc1",
                version="1.0",
                source_hash="hash1",
                sections=[ContentSection(section_id="s1", title="Title")],
            )
            fake = _FakeGeminiClient(
                {
                    "deck_id": "deck_1",
                    "run_id": "run_1",
                    "template_id": "corp_deck_2025",
                    "title": "Title",
                    "subtitle": None,
                    "global_constraints": {},
                    "slides": [
                        {
                            "slide_id": "s1",
                            "layout_id": "bad_layout",
                            "fields": {"ph_title": "Title"},
                            "speaker_notes": "",
                            "asset_refs": [],
                            "constraints_override": None,
                        }
                    ],
                }
            )

            with self.assertRaises(PlannerError):
                plan_deck_with_gemini(
                    client=fake,  # type: ignore[arg-type]
                    content_model=model,
                    cues_data={"cues": []},
                    layout_catalog_path=layout_path,
                    icons_json_path=icons_path,
                    run_id="run_1",
                    deck_id="deck_1",
                    max_retries=0,
                )


if __name__ == "__main__":
    unittest.main()
