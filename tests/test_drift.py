"""Template drift validation tests."""

import json
import tempfile
import unittest
from pathlib import Path

from src.config import load_config
from src.validate.drift import validate_template_catalog


class TestTemplateDrift(unittest.TestCase):
    def test_validate_template_catalog_passes(self) -> None:
        config = load_config()
        errors = validate_template_catalog(
            Path(config.template_path), Path(config.layout_catalog_path)
        )
        self.assertEqual(errors, [])

    def test_missing_layout_is_detected(self) -> None:
        config = load_config()
        with open(config.layout_catalog_path, "r", encoding="utf-8") as handle:
            catalog = json.load(handle)
        catalog["layouts"][0]["master_index"] = 999

        with tempfile.TemporaryDirectory() as temp_dir:
            catalog_path = Path(temp_dir) / "layout_catalog.json"
            with open(catalog_path, "w", encoding="utf-8") as handle:
                json.dump(catalog, handle)
            errors = validate_template_catalog(
                Path(config.template_path), catalog_path
            )
            self.assertTrue(any("missing in template" in err for err in errors))

    def test_missing_required_field_key_is_detected(self) -> None:
        config = load_config()
        with open(config.layout_catalog_path, "r", encoding="utf-8") as handle:
            catalog = json.load(handle)
        catalog["layouts"][0]["fields"][0]["field_key"] = "ph_missing_required"
        catalog["layouts"][0]["fields"][0]["required"] = True

        with tempfile.TemporaryDirectory() as temp_dir:
            catalog_path = Path(temp_dir) / "layout_catalog.json"
            with open(catalog_path, "w", encoding="utf-8") as handle:
                json.dump(catalog, handle)
            errors = validate_template_catalog(
                Path(config.template_path), catalog_path
            )
            self.assertTrue(any("missing required field_key" in err for err in errors))


if __name__ == "__main__":
    unittest.main()
