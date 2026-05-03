from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.outputStyles import BUILTIN_OUTPUT_STYLES, load_output_styles_dir, resolve_output_style


class TestOutputStyles(unittest.TestCase):
    def test_load_output_styles_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "custom.md").write_text("Custom prompt", encoding="utf-8")
            styles = load_output_styles_dir(root)
            self.assertIn("default", styles)
            self.assertIn("custom", styles)
            self.assertEqual(styles["custom"].prompt, "Custom prompt")

    def test_resolve_output_style_fallback(self) -> None:
        style = resolve_output_style("missing")
        self.assertEqual(style.name, "default")
        self.assertEqual(style.prompt, BUILTIN_OUTPUT_STYLES["default"].prompt)

if __name__ == "__main__":
    unittest.main()
