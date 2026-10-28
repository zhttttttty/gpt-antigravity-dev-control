from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / ".agents/skills/antigravity-delegate/scripts"))
import quick_run as quick

CONTROL = REPO / ".agents/skills/antigravity-delegate/scripts/control.py"


class FakeExecutor:
    def __init__(self, action=None, report=None, exit_code=0):
        self.action = action
        self.report = {"status": "COMPLETE", "summary": "Updated requested files"} if report is None else report
        self.exit_code = exit_code
        self.validated = False
        self.launched = False

    def validate_launch(self):
        self.validated = True

    def launch(self, worktree, context, report, logs):
        self.launched = True
        if self.action:
            self.action(worktree)
        if self.report != "MISSING":
            report.write_text(self.report if isinstance(self.report, str) else json.dumps(self.report), encoding="utf-8")
        (logs / "launch.log").write_text("fake executor output\n", encoding="utf-8")
        return {"exit_code": self.exit_code, "log": str(logs / "launch.log")}


class QuickRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="quick agy project ")
        self.root = Path(self.temp.name).resolve()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.root / "README.md").write_text("original\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        self.base = self.git("rev-parse", "HEAD").strip()

    def tearDown(self):
        for folder in (self.root / ".git/agy-runs").glob("*/workspace"):
            self.git("worktree", "remove", "--force", str(folder))
        self.temp.cleanup()

    def git(self, *args):
        return quick.git(self.root, *args)

    def check(self, code):
        argv = [sys.executable, "-c", code]
        return subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)

    def run_quick(self, executor=None, **kwargs):
        return quick.run(self.root, "Update the README", adapter=executor or FakeExecutor(), **kwargs)

    def test_complete_run_isolated_without_init_and_caller_check_is_real(self):
        def edit(worktree):
            (worktree / "README.md").write_text("updated\n", encoding="utf-8")
            (worktree / "new file.txt").write_text("new evidence\n", encoding="utf-8")
        command = self.check("from pathlib import Path; assert Path('README.md').read_text().strip() == 'updated'; print('CALLER_CHECK_OK')")
        record = self.run_quick(FakeExecutor(edit), checks=[command])
        self.assertEqual(record["status"], "READY_FOR_REVIEW", record)
        self.assertEqual(record["checks_status"], "PASS")
        self.assertEqual(record["checks"][0]["exit_code"], 0)
        self.assertIn("CALLER_CHECK_OK", Path(record["checks"][0]["log"]).read_text())
        self.assertEqual(record["changed_files"], ["README.md", "new file.txt"])
        self.assertEqual(record["untracked_files"], ["new file.txt"])
        self.assertIn("updated", Path(record["diff"]).read_text())
        self.assertEqual(record["review_verdict"], "PENDING")
        self.assertEqual(json.loads(Path(record["result_file"]).read_text())["run_id"], record["run_id"])
        self.assertEqual((self.root / "README.md").read_text(), "original\n")
        self.assertFalse((self.root / ".ai").exists())
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), self.base)
        self.assertTrue(record["branch"].startswith("codex/agy-"))

    def test_missing_checks_are_not_reported_as_passed(self):
        result = self.run_quick()
        self.assertEqual(result["status"], "READY_FOR_REVIEW")
        self.assertEqual(result["checks_status"], "NOT_RUN")
        self.assertEqual(result["checks"], [])

    def test_failed_check_retains_actual_exit_code_and_workspace(self):
        result = self.run_quick(checks=[self.check("raise SystemExit(7)")])
        self.assertEqual(result["status"], "CHECK_FAILED")
        self.assertEqual(result["checks_status"], "FAIL")
        self.assertEqual(result["checks"][0]["exit_code"], 7)
        self.assertTrue(Path(result["worktree"]).is_dir())

    def test_reported_commands_are_never_executed(self):
        report = {"status": "COMPLETE", "summary": "No checks run",
                  "commands": [self.check("from pathlib import Path; Path('INJECTED').write_text('bad')")]}
        result = self.run_quick(FakeExecutor(report=report))
        self.assertEqual(result["checks_status"], "NOT_RUN")
        self.assertFalse((Path(result["worktree"]) / "INJECTED").exists())

    def test_missing_invalid_or_blocked_report_never_means_completion(self):
        for report in ("MISSING", "not JSON", [], {"status": "COMPLETE"},
                       {"status": [], "summary": "Invalid status"},
                       {"status": "BLOCKED", "summary": "Permission denied"}, "x" * 128001):
            with self.subTest(report=str(report)[:50]):
                result = self.run_quick(FakeExecutor(report=report))
                self.assertEqual(result["status"], "BLOCKED", result)
                self.assertTrue(Path(result["result_file"]).is_file())
                self.assertEqual(result["review_verdict"], "PENDING")

    def test_failed_launch_cannot_be_hidden_by_complete_report(self):
        for exit_code in (None, False, "0"):
            with self.subTest(exit_code=exit_code):
                result = self.run_quick(FakeExecutor(exit_code=exit_code))
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(result["checks_status"], "NOT_RUN")

    def test_permission_diagnostic_blocks_even_with_a_complete_report(self):
        class Denied(FakeExecutor):
            def __init__(self, diagnostic):
                super().__init__()
                self.diagnostic = diagnostic
            def launch(self, *args):
                return {**super().launch(*args), "diagnostic": self.diagnostic}
        for diagnostic in ("PERMISSION_BLOCKED", "FORMAT_INVALID", "EMPTY_OUTPUT"):
            with self.subTest(diagnostic=diagnostic):
                result = self.run_quick(Denied(diagnostic))
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(result["checks"], [])

    def test_console_summary_is_bounded_but_full_record_is_preserved(self):
        full = {"status": "READY_FOR_REVIEW", "request": "original request",
                "changed_files": [f"file-{n}.txt" for n in range(100)],
                "executor_summary": "x" * 5000, "result_file": "result.json"}
        summary = quick.compact(full)
        self.assertEqual(summary["changed_files_total"], 100)
        self.assertEqual(len(summary["changed_files"]), 20)
        self.assertEqual(len(summary["executor_summary"]), 2000)
        self.assertEqual(len(full["changed_files"]), 100)
        self.assertNotIn("request", summary)

    def test_out_of_scope_and_control_files_block_before_checks(self):
        for name, allow in (("outside.txt", ["README.md"]), (".codex/config.toml", ["**"]),
                            (".AI/data", ["**"]), ("AGENTS.md", ["**"])):
            with self.subTest(name=name):
                def edit(worktree):
                    path = worktree / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("forbidden\n")
                result = self.run_quick(FakeExecutor(edit), allow=allow, checks=[self.check("print('MUST_NOT_RUN')")])
                self.assertEqual(result["status"], "BLOCKED")
                self.assertIn(name, result["scope_violations"])
                self.assertEqual(result["checks"], [])

    def test_check_side_effects_are_in_the_final_scope_observation(self):
        command = self.check("from pathlib import Path; Path('outside.txt').write_text('check side effect')")
        result = self.run_quick(allow=["README.md"], checks=[command])
        self.assertEqual(result["checks_status"], "PASS")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("outside.txt", result["scope_violations"])

    def test_git_history_changes_are_retained_and_flagged(self):
        def commit(worktree):
            (worktree / "README.md").write_text("unexpected commit\n")
            quick.git(worktree, "add", "README.md")
            quick.git(worktree, "commit", "-qm", "unexpected")
        result = self.run_quick(FakeExecutor(commit))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("changed Git history", result["error"])
        self.assertNotEqual(result["head_commit"], self.base)
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), self.base)

    def test_dirty_source_is_not_silently_omitted(self):
        (self.root / "README.md").write_text("uncommitted user work\n")
        executor = FakeExecutor()
        with self.assertRaisesRegex(ValueError, "Source checkout is dirty"):
            self.run_quick(executor)
        self.assertFalse(executor.validated)
        self.assertFalse((self.root / ".git/agy-runs").exists())
        self.assertEqual((self.root / "README.md").read_text(), "uncommitted user work\n")

    def test_dry_run_is_cli_accessible_and_creates_no_artifacts(self):
        result = subprocess.run([sys.executable, str(CONTROL), "--repo", str(self.root),
                                 "run", "Update README", "--dry-run"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "DRY_RUN")
        self.assertTrue(data["source_clean"])
        self.assertFalse((self.root / ".git/agy-runs").exists())
        self.assertEqual(self.git("worktree", "list", "--porcelain").count("worktree "), 1)

    def test_invalid_requests_and_scope_are_rejected_without_artifacts(self):
        for request, options in ((" ", {}), ("x", {"allow": ["../outside"]}),
                                 ("x", {"allow": ["C:/outside"]}), ("x", {"allow": ["/outside"]}),
                                 ("x" * 32000, {}), ("x", {"timeout": 0}), ("x", {"checks": [" "]})):
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    quick.run(self.root, request, adapter=FakeExecutor(), **options)
        self.assertFalse((self.root / ".git/agy-runs").exists())

    def test_check_timeout_is_recorded_as_failure(self):
        result = self.run_quick(checks=[self.check("import time; time.sleep(10)")], check_timeout=1)
        self.assertEqual(result["status"], "CHECK_FAILED")
        self.assertEqual(result["checks"][0]["exit_code"], 124)
        self.assertIn("timed out", result["checks"][0]["error"])

    def test_shell_syntax_is_only_executed_after_explicit_opt_in(self):
        command = self.check("print('first')") + " && " + self.check("print('second')")
        with self.assertRaisesRegex(ValueError, "explicit shell check"):
            self.run_quick(checks=[command])
        opted_in = self.run_quick(checks=[command], shell_checks=True)
        self.assertEqual(opted_in["status"], "READY_FOR_REVIEW", opted_in)
        self.assertTrue(opted_in["checks"][0]["shell"])
        self.assertIn("second", Path(opted_in["checks"][0]["log"]).read_text())

    def test_total_check_deadline_skips_remaining_commands(self):
        result = self.run_quick(checks=[self.check("import time; time.sleep(10)"),
                                       self.check("print('MUST_NOT_RUN')")],
                                check_timeout=10, total_check_timeout=1)
        self.assertEqual(result["status"], "CHECK_FAILED")
        self.assertEqual(result["checks"][0]["exit_code"], 124)
        self.assertEqual(result["checks"][1]["result"], "NOT_RUN")

    def test_scope_drift_stops_later_checks(self):
        command = self.check("from pathlib import Path; Path('outside.txt').write_text('side effect')")
        result = self.run_quick(allow=["README.md"], checks=[command, self.check("print('MUST_NOT_RUN')")])
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(len(result["checks"]), 1)
        self.assertEqual(result["checks_status"], "FAIL")

    def test_adapter_uses_quick_instructions_without_changing_full_protocol_default(self):
        capabilities = {"mode": True, "mode_values": ["accept-edits"], "permission_bypass": True,
                        "stream_json": False, "print_arg": "--print", "interactive_arg": "-i"}
        normal = quick.AntigravityCLI()
        daily = quick.AntigravityCLI(launch_prompt=quick.LAUNCH_PROMPT)
        for adapter in (normal, daily):
            adapter.resolve = lambda: "fake-agy"
            adapter.capabilities = lambda: capabilities
        original = " ".join(normal.argv(self.root, self.root / "context", self.root / "receipt", self.root))
        single = " ".join(daily.argv(self.root, self.root / "context", self.root / "report", self.root))
        self.assertIn("Commit implementation files only", original)
        self.assertNotIn("Commit implementation files only", single)
        self.assertIn("Do not commit", single)
        self.assertNotIn("--dangerously-skip-permissions", single)


if __name__ == "__main__":
    unittest.main()
