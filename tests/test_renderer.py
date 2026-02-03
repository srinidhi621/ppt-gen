"""Renderer tests."""

import tempfile
import unittest
from pathlib import Path

from pptx import Presentation

from src.config import load_config
from src.models.deck_ir import DeckIR, DeckSlide
from src.render.renderer import Renderer


class TestRenderer(unittest.TestCase):
    def test_render_writes_pptx_and_map(self) -> None:
        config = load_config()
        renderer = Renderer(
            Path(config.template_path),
            Path(config.layout_catalog_path),
            Path(config.icons_json_path),
        )
        deck = DeckIR(
            deck_id="deck_1",
            run_id="run_1",
            template_id="template_1",
            title="Title",
            slides=[
                DeckSlide(
                    slide_id="slide_1",
                    layout_id="one_content_light",
                    fields={"ph_title": "Hello", "ph_body": ["One", "Two"]},
                    speaker_notes="Notes",
                )
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "out.pptx"
            render_map = renderer.render(deck, output_path)
            self.assertTrue(output_path.exists())
            self.assertIn("slide_1", render_map.entries)

            prs = Presentation(str(output_path))
            self.assertEqual(len(prs.slides), 1)
            entry = render_map.entries["slide_1"]
            self.assertIn("ph_title", entry.field_keys)
            self.assertIn("ph_body", entry.field_keys)


if __name__ == "__main__":
    unittest.main()
