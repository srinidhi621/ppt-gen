"""Content normalization tests."""

import tempfile
import unittest
from pathlib import Path

from src.normalize.parser import parse_markdown, parse_markdown_string


class TestContentNormalization(unittest.TestCase):
    def test_parse_simple_markdown(self) -> None:
        content = """# Document Title

---
<!-- section_id: intro -->
## Introduction

- First bullet
- Second bullet

---
<!-- section_id: body -->
## Main Content

Some paragraph text.

- Another bullet
"""
        model = parse_markdown_string(content, doc_id="test")
        self.assertEqual(model.doc_id, "test")
        self.assertEqual(len(model.sections), 2)
        self.assertEqual(model.sections[0].section_id, "intro")
        self.assertEqual(model.sections[0].title, "Introduction")
        self.assertEqual(len(model.sections[0].bullets), 2)

    def test_parse_with_metadata_comments(self) -> None:
        content = """# Title

---
<!-- section_id: custom_id -->
<!-- layout_hint: two_content_light -->
## Section Title

- Bullet one
"""
        model = parse_markdown_string(content)
        self.assertEqual(model.sections[0].section_id, "custom_id")

    def test_generated_section_id_from_title(self) -> None:
        content = """# Title

---
## My Section Title

- Bullet
"""
        model = parse_markdown_string(content)
        self.assertEqual(model.sections[0].section_id, "my_section_title")

    def test_source_hash_stability(self) -> None:
        content = "# Title\n\n---\n## Section\n- Bullet"
        model1 = parse_markdown_string(content)
        model2 = parse_markdown_string(content)
        self.assertEqual(model1.source_hash, model2.source_hash)

    def test_source_hash_changes_with_content(self) -> None:
        model1 = parse_markdown_string("# Title\n\n---\n## Section\n- Bullet A")
        model2 = parse_markdown_string("# Title\n\n---\n## Section\n- Bullet B")
        self.assertNotEqual(model1.source_hash, model2.source_hash)

    def test_bullets_preserved(self) -> None:
        content = """# Doc

---
## Section

- First bullet with **bold**
- Second bullet
- Third bullet
"""
        model = parse_markdown_string(content)
        self.assertEqual(len(model.sections[0].bullets), 3)
        self.assertIn("**bold**", model.sections[0].bullets[0])

    def test_paragraphs_captured(self) -> None:
        content = """# Doc

---
## Section

This is a paragraph.

- A bullet

Another paragraph.
"""
        model = parse_markdown_string(content)
        self.assertIn("This is a paragraph.", model.sections[0].paragraphs)
        self.assertIn("Another paragraph.", model.sections[0].paragraphs)

    def test_parse_sample_content_md(self) -> None:
        """Test parsing the actual sample content.md file."""
        config_path = Path(__file__).parent.parent / "inputs" / "content.md"
        if config_path.exists():
            model = parse_markdown(config_path)
            self.assertGreater(len(model.sections), 0)
            self.assertTrue(model.source_hash)
            # Check that some expected sections exist
            section_ids = [s.section_id for s in model.sections]
            # The content.md has section_id metadata comments
            self.assertIn("agenda", section_ids)
            self.assertIn("challenges", section_ids)

    def test_empty_content(self) -> None:
        model = parse_markdown_string("")
        self.assertEqual(len(model.sections), 0)

    def test_no_sections_just_bullets(self) -> None:
        content = """- Orphan bullet one
- Orphan bullet two
"""
        model = parse_markdown_string(content)
        # Should create a section for orphan content
        self.assertEqual(len(model.sections), 1)
        self.assertEqual(len(model.sections[0].bullets), 2)


if __name__ == "__main__":
    unittest.main()
