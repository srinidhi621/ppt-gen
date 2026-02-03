"""Config loader tests."""

import tempfile
import unittest
from pathlib import Path

from src.config import load_config


class TestConfig(unittest.TestCase):
    def _setup_project_root(self) -> Path:
        temp_dir = Path(tempfile.mkdtemp())
        assets_dir = temp_dir / "assets"
        (assets_dir / "template").mkdir(parents=True)
        (assets_dir / "layout").mkdir(parents=True)
        (assets_dir / "icons").mkdir(parents=True)
        (temp_dir / "inputs").mkdir(parents=True)
        (temp_dir / "runs").mkdir(parents=True)

        (assets_dir / "template" / "template.pptx").touch()
        (assets_dir / "layout" / "layout_catalog.json").touch()
        (assets_dir / "icons" / "icons.json").touch()
        return temp_dir

    def test_load_config_success(self) -> None:
        root = self._setup_project_root()
        config = load_config(root)
        self.assertTrue(Path(config.template_path).exists())
        self.assertEqual(Path(config.project_root), root)

    def test_load_config_missing_template(self) -> None:
        root = self._setup_project_root()
        Path(root / "assets" / "template" / "template.pptx").unlink()
        with self.assertRaises(FileNotFoundError):
            load_config(root)


if __name__ == "__main__":
    unittest.main()
