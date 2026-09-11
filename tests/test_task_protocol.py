import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / ".agents/skills/antigravity-delegate/scripts"))
import ai
from task_data import read_yaml, write_yaml, parse_yaml, digest


class TaskProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="task protocol ")
        self.root = Path(self.temp.name).resolve()
        shutil.copytree(REPO / ".agents/skills/antigravity-delegate/templates", self.root / ".ai/templates")
        shutil.copy(REPO / ".gitignore", self.root / ".gitignore")
        self.folder = self.root / ".ai/tasks/queue/TASK-TEST"
        shutil.copytree(self.root / ".ai/templates/task", self.folder)
        self.task = read_yaml(self.folder / "task.yaml")
        self.task.update(id="TASK-TEST", title="Protocol test", objective="Produce verified result")
        self.task["planning"]["risk"] = "low"
        self.task["isolation"]["branch"] = "ai/TASK-TEST"
        self.task["checks"]["required"] = [{"command": "verify", "purpose": "Check result"}]
        write_yaml(self.folder / "task.yaml", self.task)
        ai.reset_receipts(self.root, self.folder, "TASK-TEST", 1, 1)
        for args in (("init", "-b", "main"), ("config", "user.name", "Test"),
                     ("config", "user.email", "test@example.invalid")):
            self.git(*args)
        self.commit()

    def tearDown(self):
        worktrees = self.root / ".worktrees"
        for path in worktrees.iterdir() if worktrees.exists() else []:
            self.git("worktree", "remove", "--force", str(path))
        self.temp.cleanup()

    def git(self, *args):
        return ai.run(["git", *args], cwd=self.root).stdout.strip()

    def commit(self):
        self.git("add", ".")
        self.git("commit", "--allow-empty", "-m", "fixture")

    def transition(self, target):
        with contextlib.redirect_stdout(io.StringIO()):
            self.folder = ai.transition(self.root, "TASK-TEST", target)

    def ready_review(self):
        self.transition("IN_PROGRESS")
        self.transition("REVIEW")

    def fill_evidence(self):
        executor = read_yaml(self.folder / "receipt.executor.yaml")
        executor.update(status="COMPLETE", executor="worker-1", commands=[
            {"command": "verify", "exit_code": 0, "result": "PASS"}],
            acceptance_evidence=[{"acceptance_id": "AC-001", "result": "PASS", "evidence": "verified result"}])
        executor["scope_check"] = {"result": "PASS", "out_of_scope_files": []}
        write_yaml(self.folder / "receipt.executor.yaml", executor)
        qa = read_yaml(self.folder / "receipt.qa.yaml")
        qa.update(status="REVIEWED", reviewer="reviewer-1", reviewed_at=ai.now(), verdict="PASS",
                  acceptance_review=[{"acceptance_id": "AC-001", "result": "PASS", "evidence_checked": "checked result"}])
        qa["risk_gate"].update(tier=self.task["planning"]["risk"], result="PASS")
        for section in ("scope_review", "architecture_review", "regression_review"):
            qa[section]["result"] = "PASS"
        write_yaml(self.folder / "receipt.qa.yaml", qa)
        review = read_yaml(self.folder / "review.yaml")
        review.update(verdict="PASS", summary="Independent acceptance verified")
        write_yaml(self.folder / "review.yaml", review)

    def test_bare_pass_does_not_complete_low_or_medium_task(self):
        self.ready_review()
        for risk in ("low", "medium"):
            with self.subTest(risk=risk):
                task = read_yaml(self.folder / "task.yaml")
                task["planning"]["risk"] = risk
                write_yaml(self.folder / "task.yaml", task)
                review = read_yaml(self.folder / "review.yaml")
                review["verdict"] = "PASS"
                write_yaml(self.folder / "review.yaml", review)
                with self.assertRaisesRegex(SystemExit, "DONE rejected"):
                    self.transition("DONE")
                self.assertEqual(ai.find_task(self.root, "TASK-TEST")[0], "REVIEW")

    def test_complete_current_evidence_allows_done(self):
        self.ready_review()
        self.fill_evidence()
        self.transition("DONE")
        self.assertEqual(ai.find_task(self.root, "TASK-TEST")[0], "DONE")

    def test_bad_evidence_rejected_without_state_mutation(self):
        self.ready_review()
        self.fill_evidence()
        cases = [
            ("receipt.executor.yaml", "attempt", 2),
            ("receipt.executor.yaml", "task_id", "TASK-OTHER"),
            ("receipt.executor.yaml", "contract_revision", 2),
            ("receipt.executor.yaml", "commands", [{"command": "verify", "exit_code": False, "result": "PASS"}]),
            ("receipt.executor.yaml", "acceptance_evidence", []),
            ("receipt.executor.yaml", "unverified_items", ["missing check"]),
            ("receipt.qa.yaml", "acceptance_review", []),
            ("receipt.qa.yaml", "reviewer", "worker-1"),
            ("receipt.qa.yaml", "risk_gate", {"tier": "high", "result": "PASS", "missing_evidence": []}),
            ("receipt.qa.yaml", "blocking_findings", ["bug"]),
            ("review.yaml", "verdict", "PASS_WITH_NOTES"),
        ]
        for name, key, value in cases:
            with self.subTest(name=name, key=key):
                path = self.folder / name
                original = read_yaml(path)
                changed = copy.deepcopy(original)
                changed[key] = value
                write_yaml(path, changed)
                before = (self.folder / "task.yaml").read_bytes()
                with self.assertRaises(SystemExit):
                    self.transition("DONE")
                self.assertEqual((self.folder / "task.yaml").read_bytes(), before)
                write_yaml(path, original)

    def test_high_risk_needs_merge_approval_and_cross_review(self):
        self.task["planning"]["risk"] = "high"
        self.task["risk_controls"] = dict.fromkeys(self.task["risk_controls"], True)
        write_yaml(self.folder / "task.yaml", self.task)
        self.ready_review()
        self.fill_evidence()
        with self.assertRaisesRegex(SystemExit, "Human merge approval"):
            self.transition("DONE")
        qa = read_yaml(self.folder / "receipt.qa.yaml")
        qa["human_approval"].update(result="APPROVED", approved_by="human", approved_at=ai.now())
        qa["cross_family_review"].update(result="WAIVED", reviewer="human", findings=["Human waiver: inspected risk evidence"])
        write_yaml(self.folder / "receipt.qa.yaml", qa)
        self.transition("DONE")

    def test_rework_preserves_evidence_and_resets_identity(self):
        self.ready_review()
        self.fill_evidence()
        previous = (self.folder / "receipt.executor.yaml").read_bytes()
        self.transition("READY")
        self.assertEqual((self.folder / "history/attempt-1/receipt.executor.yaml").read_bytes(), previous)
        self.assertEqual(read_yaml(self.folder / "task.yaml")["attempt"], 2)
        self.assertEqual(read_yaml(self.folder / "receipt.qa.yaml")["attempt"], 2)
        self.assertEqual(read_yaml(self.folder / "receipt.executor.yaml")["status"], "NOT_STARTED")

    def test_start_owns_state_in_controller(self):
        with contextlib.redirect_stdout(io.StringIO()):
            active = ai.start(self.root, "TASK-TEST", True)
        self.assertEqual(active.parent.name, "active")
        snapshot = self.root / ".worktrees/TASK-TEST/.ai/tasks/queue/TASK-TEST/task.yaml"
        self.assertEqual(read_yaml(snapshot)["status"], "READY")
        self.assertEqual(ai.find_task(self.root, "TASK-TEST")[0], "IN_PROGRESS")

    def test_start_enforces_isolation_and_preapproval(self):
        with self.assertRaisesRegex(ValueError, "isolation"):
            ai.start(self.root, "TASK-TEST", False)
        self.task["authority"]["public_api_change"] = True
        write_yaml(self.folder / "task.yaml", self.task)
        self.commit()
        with self.assertRaisesRegex(ValueError, "Pre-review approval"):
            ai.start(self.root, "TASK-TEST", True)
        approval = self.root / ".ai/runtime/approval.yaml"
        write_yaml(approval, {"task_id": "TASK-TEST", "contract_sha256": digest(self.task),
                              "result": "APPROVED", "approved_by": "human", "evidence": "reviewed contract"})
        with contextlib.redirect_stdout(io.StringIO()):
            ai.start(self.root, "TASK-TEST", True, approval)

    def test_missing_worktree_base_never_falls_back(self):
        self.task["isolation"]["base_branch"] = "does-not-exist"
        write_yaml(self.folder / "task.yaml", self.task)
        self.commit()
        with self.assertRaises(subprocess.CalledProcessError):
            ai.start(self.root, "TASK-TEST", True)
        self.assertEqual(ai.find_task(self.root, "TASK-TEST")[0], "READY")

    def test_dirty_contract_does_not_create_worktree(self):
        self.task["objective"] = "new objective"
        write_yaml(self.folder / "task.yaml", self.task)
        with self.assertRaisesRegex(ValueError, "Commit or stash"):
            ai.start(self.root, "TASK-TEST", True)
        self.assertFalse((self.root / ".worktrees").exists())

    def test_stale_base_and_unfinished_dependency_reject_start(self):
        self.git("branch", "old-base")
        self.task["isolation"]["base_branch"] = "old-base"
        write_yaml(self.folder / "task.yaml", self.task)
        self.commit()
        with self.assertRaisesRegex(ValueError, "equal current HEAD"):
            ai.start(self.root, "TASK-TEST", True)
        self.task["planning"]["depends_on"] = ["TASK-TEST"]
        write_yaml(self.folder / "task.yaml", self.task)
        with self.assertRaisesRegex(ValueError, "Dependency not completed"):
            ai.start(self.root, "TASK-TEST", True)
        self.assertFalse((self.root / ".worktrees").exists())

    def test_unified_cli_create_and_direct_status(self):
        command = [sys.executable, str(REPO / ".agents/skills/antigravity-delegate/scripts/control.py"), "--repo", str(self.root)]
        result = subprocess.run(command + ["create", "TASK-NEW", "--title", "CLI task", "--objective", "Check CLI"],
                                text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(command + ["status", "TASK-TEST"], text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["task_state"], "READY")
        result = subprocess.run(command + ["validate", "TASK-NEW"], text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 2)

    def test_create_initializes_invalid_scaffold_without_overwrite(self):
        with contextlib.redirect_stdout(io.StringIO()):
            folder = ai.create(self.root, "TASK-NEW", "New task", "Observable outcome", "high")
        self.assertFalse(ai.validate_task(self.root, "TASK-NEW", quiet=True))
        self.assertEqual(read_yaml(folder / "receipt.qa.yaml")["task_id"], "TASK-NEW")
        self.assertTrue(all(read_yaml(folder / "task.yaml")["risk_controls"].values()))
        before = (folder / "task.yaml").read_bytes()
        with self.assertRaisesRegex(ValueError, "already exists"):
            ai.create(self.root, "TASK-NEW", "Replacement", "Replacement")
        self.assertEqual((folder / "task.yaml").read_bytes(), before)
        for ident in ("../TASK-OUTSIDE", "TASK-../escape", "TASK-X/../../escape"):
            with self.assertRaises(ValueError):
                ai.create(self.root, ident, "title", "objective")

    def test_structured_yaml_supports_flow_and_rejects_ambiguous_keys(self):
        import yaml
        (self.folder / "task.yaml").write_text(yaml.safe_dump(self.task, default_flow_style=True), encoding="utf-8")
        self.assertTrue(ai.validate_task(self.root, "TASK-TEST", quiet=True))
        self.transition("IN_PROGRESS")
        for value in ("id: TASK-A\nid: TASK-B\n", "[]", "1: value", "task: ["):
            with self.assertRaises(ValueError):
                parse_yaml(value)
        for key, value in (("authority", []), ("attempt", True), ("acceptance", {}), ("planning", None)):
            task = copy.deepcopy(self.task)
            task.update(status="IN_PROGRESS")
            task[key] = value
            write_yaml(self.folder / "task.yaml", task)
            self.assertFalse(ai.validate_task(self.root, "TASK-TEST", quiet=True))


if __name__ == "__main__":
    unittest.main()
