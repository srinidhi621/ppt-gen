"""Renderer tests."""

import json
import tempfile
import unittest
from pathlib import Path

from pptx import Presentation

from src.config import load_config
from src.models.deck_ir import AssetRef, DeckIR, DeckSlide
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

    def test_icon_index_includes_external_registry_and_resolves_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            assets_dir = root / "assets"
            template_path = assets_dir / "template" / "template.pptx"
            layout_catalog_path = assets_dir / "layout" / "layout_catalog.json"
            icons_json_path = assets_dir / "icons" / "icons.json"
            local_icon_path = assets_dir / "icons" / "png" / "icon_001.png"
            external_icon_path = assets_dir / "external_assets" / "tabler" / "svg" / "cloud.svg"
            external_registry_path = assets_dir / "external_assets" / "registry.manifest.json"

            template_path.parent.mkdir(parents=True, exist_ok=True)
            layout_catalog_path.parent.mkdir(parents=True, exist_ok=True)
            icons_json_path.parent.mkdir(parents=True, exist_ok=True)
            local_icon_path.parent.mkdir(parents=True, exist_ok=True)
            external_icon_path.parent.mkdir(parents=True, exist_ok=True)
            external_registry_path.parent.mkdir(parents=True, exist_ok=True)

            template_path.write_bytes(b"")
            layout_catalog_path.write_text('{"layouts":[]}', encoding="utf-8")
            local_icon_path.write_bytes(b"local")
            external_icon_path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"></svg>',
                encoding="utf-8",
            )
            icons_json_path.write_text(
                '{"icons":[{"icon_id":"icon_001","filename":"icon_001.png"}]}',
                encoding="utf-8",
            )
            external_registry_path.write_text(
                json.dumps(
                    {
                        "icons": [
                            {
                                "id": "tabler:cloud",
                                "pack": "tabler",
                                "svg_path": "svg/cloud.svg",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            renderer = Renderer(template_path, layout_catalog_path, icons_json_path)
            icon_index = renderer._load_icon_index()
            self.assertIn("icon_001", icon_index)
            self.assertIn("tabler:cloud", icon_index)

            local_asset = AssetRef(
                asset_type="icon",
                asset_id="icon_001",
                target_field_key="ph_image",
            )
            external_asset = AssetRef(
                asset_type="icon",
                asset_id="tabler:cloud",
                target_field_key="ph_image",
            )
            self.assertEqual(
                renderer._resolve_asset_path(local_asset, icon_index),
                local_icon_path,
            )
            self.assertEqual(
                renderer._resolve_asset_path(external_asset, icon_index),
                external_icon_path,
            )


if __name__ == "__main__":
    unittest.main()
