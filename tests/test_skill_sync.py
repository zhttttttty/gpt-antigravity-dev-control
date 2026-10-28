import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / ".agents/skills/antigravity-delegate/scripts/check_skill_sync.py"
SPEC = importlib.util.spec_from_file_location("check_skill_sync", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SkillSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.canonical = Path(self.temp.name) / "canonical"
        self.other = Path(self.temp.name) / "other"
        self.canonical.mkdir()
        self.other.mkdir()

    def test_normalizes_line_endings_and_ignores_cache(self):
        (self.canonical / "a.md").write_bytes(b"a\r\nb\r\n")
        (self.other / "a.md").write_bytes(b"a\rb\r")
        cache = self.other / "__pycache__"
        cache.mkdir()
        (cache / "a.pyc").write_bytes(b"cache")
        (self.other / "ignored.PYC").write_bytes(b"cache")
        self.assertTrue(MODULE.compare(self.canonical, self.other)["in_sync"])

    def test_reports_missing_extra_and_changed(self):
        (self.canonical / "missing.md").write_text("missing", encoding="utf-8")
        (self.canonical / "changed.md").write_text("before", encoding="utf-8")
        (self.other / "changed.md").write_text("after", encoding="utf-8")
        (self.other / "extra.md").write_text("extra", encoding="utf-8")
        result = MODULE.compare(self.canonical, self.other)
        self.assertFalse(result["in_sync"])
        self.assertEqual(result["missing"], ["missing.md"])
        self.assertEqual(result["extra"], ["extra.md"])
        self.assertEqual(result["changed"], ["changed.md"])


if __name__ == "__main__":
    unittest.main()
