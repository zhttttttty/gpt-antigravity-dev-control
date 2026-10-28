from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys
import tempfile
import shutil
import unittest

import yaml


REPO = Path(__file__).resolve().parents[1]
CONTROL = REPO / ".agents" / "skills" / "antigravity-delegate" / "scripts" / "control.py"


class UnifiedControlCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.project)], check=True)
        subprocess.run([sys.executable, str(CONTROL), "init", "--repo", str(self.project)], check=True,
                       capture_output=True, text=True)

    def tearDown(self):
        self.temp.cleanup()

    def run_control(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CONTROL), *args],
            cwd=REPO,
            text=True,
            capture_output=True,
            timeout=20,
        )

    def test_top_level_help_lists_both_command_families(self):
        result = self.run_control("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Task protocol commands", result.stdout)
        self.assertIn("Local delegation commands", result.stdout)
        self.assertIn("check-orchestration", result.stdout)
        self.assertIn("status [--json]", result.stdout)
        self.assertIn("verify", result.stdout)

    def test_verify_and_daily_run_are_both_available(self):
        for command in ("verify", "run"):
            result = self.run_control(command, "--help")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("usage:", result.stdout)

    def test_invalid_repo_arguments_fail_without_traceback(self):
        for args in (("--repo",), ("--repo=",), ("--repo", "--help"), ("--repo", "-h"),
                     ("--repo", str(self.project), "--repo", str(self.project), "status"),
                     ("--repo", str(self.project / "missing"), "status")):
            with self.subTest(args=args):
                result = self.run_control(*args)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("ERROR:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_relative_init_path_resolved_before_chdir(self):
        result = subprocess.run(
            [sys.executable, str(CONTROL), "init", "--repo", self.project.name],
            cwd=self.project.parent, text=True, capture_output=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.project / self.project.name).exists())

    def test_explicit_child_directory_cannot_target_parent_tasks(self):
        child = self.project / "nested project"
        child.mkdir()
        (child / ".ai").mkdir()
        for command in (("status",), ("create", "TASK-WRONG", "--title", "Wrong", "--objective", "Wrong")):
            result = self.run_control("--repo", str(child), *command)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("must name the Git repository root", result.stderr)
        self.assertFalse((self.project / ".ai/tasks/queue/TASK-WRONG").exists())
        default = subprocess.run([sys.executable, str(CONTROL), "status"], cwd=child,
                                 text=True, capture_output=True, timeout=20)
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertIn("READY", default.stdout)

    def test_explicit_equals_repo_and_live_json_status(self):
        summary = self.project / ".ai/state/PROJECT_STATE.yaml"
        before = summary.read_bytes()
        created = self.run_control("--repo", str(self.project), "create", "TASK-LIVE",
                                   "--title", "Live status", "--objective", "Read actual directories")
        self.assertEqual(created.returncode, 0, created.stderr)
        result = self.run_control(f"--repo={self.project}", "status", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(Path(data["repository"]), self.project.resolve())
        self.assertEqual(data["tasks"]["READY"], ["TASK-LIVE"])
        self.assertEqual(data["counts"]["READY"], 1)
        self.assertEqual(data["unfinished_tasks"], ["TASK-LIVE"])
        self.assertEqual(data["in_progress_tasks"], [])
        self.assertEqual(summary.read_bytes(), before)

    def test_live_status_rejects_duplicate_or_mismatched_tasks(self):
        self.run_control("--repo", str(self.project), "create", "TASK-LIVE",
                         "--title", "Live status", "--objective", "Check consistency")
        folder = self.project / ".ai/tasks/queue/TASK-LIVE"
        data = yaml.safe_load((folder / "task.yaml").read_text(encoding="utf-8"))
        data["status"] = "REVIEW"
        (folder / "task.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
        result = self.run_control("--repo", str(self.project), "status", "--json")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("mismatch", result.stderr)
        data["status"] = "READY"
        (folder / "task.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
        target = self.project / ".ai/tasks/active/TASK-LIVE"
        shutil.copytree(folder, target)
        data["status"] = "IN_PROGRESS"
        (target / "task.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
        result = self.run_control("--repo", str(self.project), "status", "--json")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("multiple state folders", result.stderr)

    def test_status_without_task_uses_protocol_status(self):
        result = self.run_control("--repo", str(self.project), "status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("READY", result.stdout)
        self.assertIn("ARCHIVED", result.stdout)

    def test_status_with_task_uses_delegation_status(self):
        result = self.run_control("status", "TASK-NOT-PRESENT", "--repo", str(REPO))
        self.assertEqual(result.returncode, 2)
        self.assertIn("No local run found", result.stderr)

    def test_unknown_command_fails_at_unified_boundary(self):
        result = self.run_control("unknown")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown command", result.stderr)

    def test_core_domain_error_uses_unified_exit_code(self):
        result = self.run_control("validate", "TASK-NOT-PRESENT")
        self.assertEqual(result.returncode, 2)
        self.assertIn("task not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
