from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
CONTROL = REPO / ".agents/skills/antigravity-delegate/scripts/control.py"


class ProjectInitializationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="init project ")
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.project)], check=True)

    def run_control(self, *args):
        return subprocess.run([sys.executable, str(CONTROL), "--repo", str(self.project), *args],
                              capture_output=True, text=True, timeout=20)

    def profile(self, *args):
        return self.run_control("init", "--install-codex-profile", *args)

    def test_minimal_init_is_non_destructive_and_leaves_profile_optional(self):
        result = self.run_control("init")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.project / ".codex").exists())
        self.assertFalse((self.project / ".ai/config.yaml").exists())
        doc = self.project / ".ai/project/PROJECT.md"
        doc.write_text("User project specification\n", encoding="utf-8")
        template = self.project / ".ai/templates/task/task.yaml"
        original = template.read_bytes()
        self.assertEqual(self.run_control("init").returncode, 0)
        self.assertEqual(doc.read_text(encoding="utf-8"), "User project specification\n")
        self.assertEqual(template.read_bytes(), original)

    def test_profile_is_complete_idempotent_and_passes_offline_check(self):
        installed = self.profile()
        self.assertEqual(installed.returncode, 0, installed.stderr)
        checked = self.run_control("check-orchestration")
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertEqual(json.loads(checked.stdout)["status"], "PASS")
        paths = list((self.project / ".codex").rglob("*.toml")) + [self.project / ".ai/config.yaml"]
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}
        repeated = self.profile()
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual({p: (p.read_bytes(), p.stat().st_mtime_ns) for p in paths}, before)

    def test_conflict_preflight_does_not_partially_initialize(self):
        config = self.project / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text('model = "custom"\n', encoding="utf-8")
        result = self.profile()
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Existing configuration differs", result.stderr)
        self.assertEqual(config.read_text(encoding="utf-8"), 'model = "custom"\n')
        self.assertFalse((self.project / ".ai").exists())
        self.assertFalse((self.project / ".codex/agents").exists())

    def test_canonical_conflict_preserved_and_explicit_overwrite_supported(self):
        self.assertEqual(self.profile().returncode, 0)
        config = self.project / ".ai/config.yaml"
        config.write_text("custom: true\n", encoding="utf-8")
        result = self.profile()
        self.assertEqual(result.returncode, 2)
        self.assertIn(".ai/config.yaml", result.stderr)
        self.assertEqual(config.read_text(encoding="utf-8"), "custom: true\n")
        overwritten = self.profile("--overwrite-codex-profile")
        self.assertEqual(overwritten.returncode, 0, overwritten.stderr)
        self.assertEqual(self.run_control("check-orchestration").returncode, 0)

    def test_overwrite_requires_profile_and_root_target(self):
        result = self.run_control("init", "--overwrite-codex-profile")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.project / ".ai").exists())
        child = self.project / "child"
        child.mkdir()
        result = subprocess.run([sys.executable, str(CONTROL), "--repo", str(child), "init"],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Git repository root", result.stderr)
        self.assertFalse((child / ".ai").exists())

    def test_profile_target_directory_rejected_before_writes(self):
        (self.project / ".codex/config.toml").mkdir(parents=True)
        result = self.profile("--overwrite-codex-profile")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not a file", result.stderr)
        self.assertFalse((self.project / ".ai").exists())

    def test_profile_refuses_link_to_external_directory(self):
        outside = tempfile.TemporaryDirectory(prefix="external profile ")
        self.addCleanup(outside.cleanup)
        try:
            (self.project / ".codex").symlink_to(Path(outside.name), target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"Directory symlinks unavailable: {exc}")
        result = self.profile("--overwrite-codex-profile")
        self.assertEqual(result.returncode, 2)
        self.assertIn("must not traverse a link", result.stderr)
        self.assertEqual(list(Path(outside.name).iterdir()), [])
        self.assertFalse((self.project / ".ai").exists())


if __name__ == "__main__":
    unittest.main()
