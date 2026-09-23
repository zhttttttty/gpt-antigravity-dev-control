import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / ".agents/skills/antigravity-delegate/scripts/check_skill_sync.py"
SPEC = importlib.util.spec_from_file_location("check_skill_sync", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_compare_normalizes_line_endings_and_ignores_cache(tmp_path):
    canonical = tmp_path / "canonical"
    other = tmp_path / "other"
    canonical.mkdir()
    other.mkdir()
    (canonical / "a.md").write_bytes(b"a\r\nb\r\n")
    (other / "a.md").write_bytes(b"a\rb\r")
    cache = other / "__pycache__"
    cache.mkdir()
    (cache / "a.pyc").write_bytes(b"cache")
    (other / "ignored.PYC").write_bytes(b"cache")
    assert MODULE.compare(canonical, other)["in_sync"] is True


def test_compare_reports_missing_extra_and_changed(tmp_path):
    canonical = tmp_path / "canonical"
    other = tmp_path / "other"
    canonical.mkdir()
    other.mkdir()
    (canonical / "missing.md").write_text("missing", encoding="utf-8")
    (canonical / "changed.md").write_text("before", encoding="utf-8")
    (other / "changed.md").write_text("after", encoding="utf-8")
    (other / "extra.md").write_text("extra", encoding="utf-8")
    result = MODULE.compare(canonical, other)
    assert result["in_sync"] is False
    assert result["missing"] == ["missing.md"]
    assert result["extra"] == ["extra.md"]
    assert result["changed"] == ["changed.md"]
