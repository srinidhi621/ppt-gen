"""Tests for combined markdown generate helpers."""

import unittest
from pathlib import Path

from src.generate_pipeline import (
    CombinedInputError,
    _build_asset_refs,
    build_deckir_from_content,
    split_combined_markdown,
)
from src.models.content import ContentSection
from src.normalize.parser import parse_markdown_string


class TestSplitCombinedMarkdown(unittest.TestCase):
    def test_split_with_json_fence(self) -> None:
        combined = """## Content
# Deck Title

---
## Slide One
- Point one
- Point two

## Visualization Cues
```json
{
  "cues": [
    {"section_id": "slide_one", "layout_hint": "one_content_light", "notes": "Keep concise"}
  ]
}
```
"""
        content_md, cues = split_combined_markdown(combined)
        self.assertIn("## Slide One", content_md)
        self.assertIn("cues", cues)
        self.assertEqual(len(cues["cues"]), 1)

    def test_split_without_cues_defaults_empty(self) -> None:
        combined = """## Content
# Deck Title

---
## Slide One
- Point one
"""
        _, cues = split_combined_markdown(combined)
        self.assertEqual(cues, {"cues": []})

    def test_split_missing_content_raises(self) -> None:
        combined = """## Visualization Cues
{"cues": []}
"""
        with self.assertRaises(CombinedInputError):
            split_combined_markdown(combined)

    def test_split_tolerates_plain_section_labels_and_unicode_bullets(self) -> None:
        combined = """Content
<!-- section_id: first_slide -->
Legacy Systems Overview
• Point one
• Point two
⸻
Visualization Cues
{"cues":[{"section_id":"first_slide","layout_hint":"one_content_light"}]}
"""
        content_md, cues = split_combined_markdown(combined)
        self.assertIn("## Legacy Systems Overview", content_md)
        self.assertIn("- Point one", content_md)
        self.assertIn("---", content_md)
        self.assertEqual(cues["cues"][0]["section_id"], "first_slide")

    def test_split_accepts_plain_content_markdown_without_combined_sections(self) -> None:
        plain_content = """# Deck Title

---
## Slide One
- Point one
"""
        content_md, cues = split_combined_markdown(plain_content)
        self.assertIn("## Slide One", content_md)
        self.assertEqual(cues, {"cues": []})


class TestBuildDeckFromContent(unittest.TestCase):
    def test_build_deck_respects_layout_hint(self) -> None:
        content = """# Deck

---
<!-- section_id: section_a -->
## Section A
- A1
- A2
"""
        model = parse_markdown_string(content, doc_id="doc")
        cues = {
            "cues": [
                {
                    "section_id": "section_a",
                    "layout_hint": "two_content_light",
                    "notes": "Use two columns",
                }
            ]
        }
        layout_catalog_path = Path(__file__).parent.parent / "assets" / "layout" / "layout_catalog.json"
        deck = build_deckir_from_content(
            content_model=model,
            cues_data=cues,
            layout_catalog_path=layout_catalog_path,
            run_id="run_1",
            deck_id="deck_1",
        )
        self.assertEqual(len(deck.slides), 1)
        self.assertEqual(deck.slides[0].layout_id, "two_content_light")
        self.assertIn("ph_body_left", deck.slides[0].fields)
        self.assertIn("ph_body_right", deck.slides[0].fields)

    def test_build_deck_generates_image_asset_ref_when_hint_matches(self) -> None:
        content = """# Deck

---
<!-- section_id: section_img -->
## Section With Image
- A1
"""
        model = parse_markdown_string(content, doc_id="doc")
        cues = {
            "cues": [
                {
                    "section_id": "section_img",
                    "layout_hint": "content_image_light",
                    "image_hint": "outmaneuver risk",
                }
            ]
        }
        layout_catalog_path = Path(__file__).parent.parent / "assets" / "layout" / "layout_catalog.json"
        deck = build_deckir_from_content(
            content_model=model,
            cues_data=cues,
            layout_catalog_path=layout_catalog_path,
            run_id="run_1",
            deck_id="deck_1",
        )
        self.assertEqual(len(deck.slides), 1)
        self.assertGreaterEqual(len(deck.slides[0].asset_refs), 1)
        self.assertEqual(deck.slides[0].asset_refs[0].asset_type, "image")
        self.assertEqual(deck.slides[0].asset_refs[0].target_field_key, "ph_image")

    def test_build_asset_refs_skips_non_renderable_icon_assets(self) -> None:
        section = ContentSection(
            section_id="section_icon",
            title="Section With Icon",
            paragraphs=[],
            bullets=["Point"],
        )
        cue = {"icon_hints": ["cloud"]}
        layout_entry = {
            "fields": [
                {"field_key": "ph_title"},
                {"field_key": "ph_body"},
                {"field_key": "ph_image"},
            ]
        }
        assets = [
            {
                "asset_type": "icon",
                "asset_id": "tabler:cloud",
                "source_path": "external_assets/tabler/svg/cloud.svg",
                "tags": ["cloud"],
                "synonyms": [],
            },
            {
                "asset_type": "icon",
                "asset_id": "icon_001",
                "source_path": "icons/png/icon_001.png",
                "tags": ["cloud"],
                "synonyms": [],
            },
        ]

        refs = _build_asset_refs(
            section=section,
            cue=cue,
            layout_entry=layout_entry,
            assets=assets,
        )
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].asset_type, "icon")
        self.assertEqual(refs[0].asset_id, "icon_001")


if __name__ == "__main__":
    unittest.main()
