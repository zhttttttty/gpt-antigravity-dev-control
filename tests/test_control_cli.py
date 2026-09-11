from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest


REPO = Path(__file__).resolve().parents[1]
CONTROL = REPO / ".agents" / "skills" / "antigravity-delegate" / "scripts" / "control.py"


class UnifiedControlCLITests(unittest.TestCase):
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

    def test_status_without_task_uses_protocol_status(self):
        result = self.run_control("--repo", str(REPO), "status")
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
