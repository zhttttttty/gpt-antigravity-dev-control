from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml


REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("orchestration_check", REPO / ".ai/scripts/check_orchestration.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class OrchestrationConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(REPO / ".codex", self.root / ".codex")
        (self.root / ".ai/templates/task").mkdir(parents=True)
        for relative in (".ai/config.yaml", ".ai/templates/task/task.yaml"):
            shutil.copy2(REPO / relative, self.root / relative)

    def test_repository_and_cli_agree(self):
        self.assertEqual(CHECK.validate(REPO), [])
        result = subprocess.run(
            [sys.executable, str(REPO / ".ai/scripts/control.py"), "check-orchestration", "--repo", str(self.root)],
            capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("NOT_RUN", result.stdout)

    def test_detects_wrong_reviewer_model_and_write_access(self):
        path = self.root / ".codex/agents/reviewer.toml"
        path.write_text(path.read_text(encoding="utf-8").replace('"gpt-6-astra"', '"gpt-5.6-luna"').replace('"read-only"', '"workspace-write"'), encoding="utf-8")
        errors = "\n".join(CHECK.validate(self.root))
        self.assertIn("reviewer.model:", errors)
        self.assertIn("reviewer.sandbox_mode:", errors)

    def test_cli_failure_and_help(self):
        (self.root / ".codex/config.toml").unlink()
        command = [sys.executable, str(REPO / ".ai/scripts/control.py"), "--repo", str(self.root), "check-orchestration"]
        failed = subprocess.run(command, capture_output=True, text=True, timeout=20)
        self.assertEqual(failed.returncode, 1, failed.stderr)
        self.assertIn('"status": "FAIL"', failed.stdout)
        help_result = subprocess.run(command + ["--help"], capture_output=True, text=True, timeout=20)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("without launching providers", help_result.stdout)

    def test_detects_default_and_template_drift(self):
        path = self.root / ".ai/config.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["roles"]["planner"]["preferred_model"] = "different-model"
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        errors = "\n".join(CHECK.validate(self.root))
        self.assertIn("root model / planner", errors)
        self.assertIn("new task planner", errors)

    def test_missing_and_malformed_role_fail_closed(self):
        (self.root / ".codex/agents/worker.toml").unlink()
        (self.root / ".codex/agents/tester.toml").write_text("[broken", encoding="utf-8")
        errors = "\n".join(CHECK.validate(self.root))
        self.assertIn("worker.toml:", errors)
        self.assertIn("tester.toml:", errors)

    def test_invalid_policy_shapes_and_boolean_limit_fail(self):
        path = self.root / ".ai/config.yaml"
        for policy in (["invalid"], {"native_subagent_limit": True, "combined_execution_limit": 0}):
            with self.subTest(policy=policy):
                data = yaml.safe_load((REPO / ".ai/config.yaml").read_text(encoding="utf-8"))
                data["orchestration"] = policy
                path.write_text(yaml.safe_dump(data), encoding="utf-8")
                self.assertIn("expected a positive integer", "\n".join(CHECK.validate(self.root)))

    def test_native_capacity_cannot_exceed_combined_budget(self):
        path = self.root / ".ai/config.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        data["orchestration"]["combined_execution_limit"] = 1
        path.write_text(yaml.safe_dump(data), encoding="utf-8")
        self.assertIn("native limit exceeds coordinator combined limit", CHECK.validate(self.root))


if __name__ == "__main__":
    unittest.main()
