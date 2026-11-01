import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / ".agents/skills/antigravity-delegate/scripts"
sys.path.insert(0, str(SCRIPTS))
import doctor
import run_history
from test_quick_run import FakeExecutor
import quick_run


class DailyWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="daily user workflow ")
        self.root = Path(self.temp.name).resolve()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.root / "README.md").write_text("original\n")
        self.git("add", "."); self.git("commit", "-qm", "fixture")

    def tearDown(self):
        for directory in (self.root / ".git/agy-runs").glob("*/workspace"):
            self.git("worktree", "remove", "--force", str(directory))
        self.temp.cleanup()

    def git(self, *args):
        return quick_run.git(self.root, *args)

    def cli(self, script, *args):
        return subprocess.run([sys.executable, str(script), *args], cwd=self.root,
                              capture_output=True, text=True, timeout=25)

    def test_copied_skill_preview_keeps_project_clean_without_gitignore(self):
        installed = self.root / ".agents/skills/antigravity-delegate"
        shutil.copytree(SCRIPTS.parent, installed, ignore=shutil.ignore_patterns("__pycache__"))
        self.git("add", "."); self.git("commit", "-qm", "install skill")
        result = self.cli(installed / "scripts/control.py", "run", "Update README", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["source_clean"])
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertFalse(list(installed.rglob("__pycache__")))

    def test_doctor_reports_missing_dependency_without_traceback_or_artifacts(self):
        result = subprocess.run([sys.executable, "-S", str(SCRIPTS / "control.py"), "doctor"],
                                cwd=self.root, capture_output=True, text=True, timeout=25)
        self.assertEqual(result.returncode, 2, result.stderr)
        data = json.loads(result.stdout)
        dependency = next(c for c in data["checks"] if c["name"] == "dependencies")
        self.assertEqual(dependency["status"], "BLOCKED")
        self.assertIn("pip install", dependency["next_step"])
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertFalse((self.root / ".ai").exists())

    def test_missing_dependency_run_error_is_actionable(self):
        result = subprocess.run([sys.executable, "-S", str(SCRIPTS / "control.py"),
                                 "run", "Update README", "--dry-run"],
                                cwd=self.root, capture_output=True, text=True, timeout=25)
        self.assertEqual(result.returncode, 2)
        self.assertIn("pip install", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_doctor_reports_dirty_paths_and_does_not_launch(self):
        (self.root / "README.md").write_text("user edits")
        with patch("adapters.antigravity_cli.AntigravityCLI.validate_launch"), \
             patch("adapters.antigravity_cli.AntigravityCLI.resolve", return_value="fake-agy"), \
             patch("adapters.antigravity_cli.AntigravityCLI.capabilities", return_value={}), \
             patch("adapters.antigravity_cli.AntigravityCLI.launch") as launch:
            result = doctor.inspect(self.root)
        launch.assert_not_called()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("README.md", str(result["checks"]))
        self.assertEqual(result["login"], "UNKNOWN")

    def test_daily_history_lists_and_reads_actual_results_without_init(self):
        self.assertEqual(run_history.history(self.root)["runs"], [])
        result = quick_run.run(self.root, "Update README", adapter=FakeExecutor())
        listing = run_history.history(self.root)
        self.assertEqual(listing["runs"][0]["run_id"], result["run_id"])
        self.assertEqual(run_history.history(self.root, "latest"), result)
        cli = self.cli(SCRIPTS / "control.py", "runs", result["run_id"])
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertEqual(json.loads(cli.stdout), result)
        self.assertFalse((self.root / ".ai").exists())
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_history_rejects_path_escape_and_reports_corrupt_record(self):
        for value in ("../outside", "../../config", "C:/outside"):
            with self.assertRaises(ValueError):
                run_history.history(self.root, value)
        result = quick_run.run(self.root, "Update README", adapter=FakeExecutor())
        Path(result["result_file"]).write_text("broken JSON")
        listing = run_history.history(self.root)
        self.assertEqual(listing["total"], 1)
        self.assertEqual(len(listing["errors"]), 1)
        with self.assertRaisesRegex(ValueError, "Cannot read run"):
            run_history.history(self.root, "latest")

    def test_latest_uses_record_update_time_not_random_run_id_suffix(self):
        first = quick_run.run(self.root, "First run", adapter=FakeExecutor())
        second = quick_run.run(self.root, "Second run", adapter=FakeExecutor())
        os.utime(first["result_file"], ns=(1_000_000_000, 1_000_000_000))
        os.utime(second["result_file"], ns=(2_000_000_000, 2_000_000_000))
        self.assertEqual(run_history.history(self.root, "latest")["run_id"], second["run_id"])

    def test_real_adapter_daily_run_and_history_end_to_end(self):
        script = self.root / ".git/fake_executor.py"
        script.write_text(
            "import json, sys\nfrom pathlib import Path\n"
            "Path('README.md').write_text('updated by child process\\n')\n"
            "Path('new.txt').write_text('new file\\n')\n"
            "Path(sys.argv[1]).write_text(json.dumps(dict(status='COMPLETE', summary='updated two files')))\n"
            "print('EXECUTOR_FINISHED')\n", encoding="utf-8")
        adapter = quick_run.AntigravityCLI(sys.executable, [str(script), "{receipt}"])
        result = quick_run.run(self.root, "Update documentation", allow=["README.md", "new.txt"],
                               checks=["git diff --check"], adapter=adapter)
        self.assertEqual(result["status"], "READY_FOR_REVIEW", result)
        self.assertEqual(result["checks_status"], "PASS")
        self.assertEqual(result["changed_files"], ["README.md", "new.txt"])
        self.assertEqual(run_history.history(self.root, result["run_id"]), result)
        self.assertEqual((self.root / "README.md").read_text(), "original\n")
        self.assertEqual(self.git("status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
