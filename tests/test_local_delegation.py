import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / ".ai/scripts"))
import delegate as d
from antigravity_cli import AntigravityCLI


class TaskDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def task_yaml(task):
    return yaml.dump(task, Dumper=TaskDumper, sort_keys=False)


class LocalDelegationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="local delegation ")
        self.root = Path(self.temp.name).resolve()
        shutil.copytree(REPO / ".ai/templates", self.root / ".ai/templates")
        shutil.copy(REPO / ".gitignore", self.root / ".gitignore")
        self.folder = self.root / ".ai/tasks/queue/TASK-TEST"
        shutil.copytree(self.root / ".ai/templates/task", self.folder)
        self.task = d.read_yaml(self.folder / "task.yaml")
        self.task.update(id="TASK-TEST", title="local fixture", objective="Create src/result.txt")
        self.task["planning"]["risk"] = "low"
        self.task["scope"]["writable"] = ["src/**"]
        self.task["isolation"]["base_branch"] = "main"
        self.task["checks"]["required"] = [{"command": "python -m unittest", "purpose": "fixture check"}]
        self.task["execution"] = {"mode": "delegated", "adapter": "antigravity_cli", "max_execution_attempts": 2}
        self.write_task()
        d.git(self.root, "init", "-b", "main")
        d.git(self.root, "config", "user.name", "Test")
        d.git(self.root, "config", "user.email", "test@example.invalid")
        self.commit()

    def tearDown(self):
        # Use Git's own safe removal for temporary worktrees before temp cleanup.
        for worktree in (self.root / ".worktrees").glob("*") if (self.root / ".worktrees").exists() else []:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=self.root, capture_output=True)
        self.temp.cleanup()

    def write_task(self):
        (self.folder / "task.yaml").write_text(task_yaml(self.task), encoding="utf-8")

    def commit(self):
        d.git(self.root, "add", ".")
        d.git(self.root, "commit", "--allow-empty", "-m", "fixture")

    def prepare(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return d.prepare(self.root, "TASK-TEST", True)

    def finish(self, record, name="src/result.txt", missing=False):
        wt = Path(record["worktree"])
        file = wt / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("implemented\n", encoding="utf-8")
        d.git(wt, "add", name)
        d.git(wt, "commit", "-m", "implementation")
        p = wt / ".ai/runtime/delegation/receipt.executor.yaml"
        receipt = d.read_yaml(p)
        receipt.update(status="COMPLETE", commands=[] if missing else [
            {"command": "python -m unittest", "exit_code": 0, "result": "PASS"}],
            acceptance_evidence=[{"acceptance_id": "AC-001", "result": "PASS", "evidence": "src/result.txt"}])
        p.write_text(yaml.safe_dump(receipt), encoding="utf-8")
        return p

    def collect(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return d.collect(self.root, "TASK-TEST")

    def test_legacy_is_direct(self):
        self.task.pop("execution")
        self.assertEqual(d.route(self.task)["mode"], "direct")

    def test_confirmation_required(self):
        with self.assertRaisesRegex(ValueError, "confirmation"):
            d.prepare(self.root, "TASK-TEST")

    def test_direct_not_dispatched(self):
        self.task["execution"]["mode"] = "direct"
        self.write_task(); self.commit()
        with self.assertRaisesRegex(ValueError, "Direct task"):
            self.prepare()

    def test_dirty_checkout_preserved(self):
        (self.root / "user.txt").write_text("keep")
        with self.assertRaisesRegex(ValueError, "Commit or stash"):
            self.prepare()
        self.assertEqual((self.root / "user.txt").read_text(), "keep")

    def test_base_no_fallback(self):
        self.task["isolation"]["base_branch"] = "missing"
        self.write_task(); self.commit()
        with self.assertRaises(subprocess.CalledProcessError):
            self.prepare()
        self.assertFalse((self.root / ".worktrees").exists())

    def test_context_budget_fail_before_worktree(self):
        (self.folder / "context.md").write_text("x" * 33000)
        self.commit()
        with self.assertRaisesRegex(ValueError, "too large"):
            self.prepare()

    def test_architecture_approval_bound_to_contract(self):
        self.task["authority"]["public_api_change"] = True
        self.write_task(); self.commit()
        with self.assertRaisesRegex(ValueError, "Pre-review approval"):
            self.prepare()
        approval = self.root / ".ai/runtime/approval.yaml"
        d.atomic(approval, yaml.safe_dump({"task_id": "TASK-TEST", "contract_sha256": d.digest(self.task),
                                         "result": "APPROVED", "approved_by": "human", "evidence": "ADR reviewed"}))
        with contextlib.redirect_stdout(io.StringIO()):
            record = d.prepare(self.root, "TASK-TEST", True, approval)
        self.assertEqual(record["phase"], "PREPARED")

    def test_roundtrip_independent_review_not_done(self):
        record = self.prepare()
        self.finish(record)
        result = self.collect()
        self.assertEqual(result["task_state"], "REVIEW")
        self.assertEqual(result["review_verdict"], "PENDING")
        self.assertEqual(result["checks"]["reported_passed"], 1)
        self.assertIsNone(result["usage"]["codex_tokens"])
        self.assertTrue((Path(record["run_dir"]) / "changes.diff").exists())
        self.assertEqual(self.collect(), result)
        with self.assertRaises(SystemExit):
            d.ai.transition(self.root, "TASK-TEST", "DONE")

    def test_missing_receipt_not_success(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "not complete"):
            self.collect()

    def test_scope_violation_blocks(self):
        record = self.prepare()
        self.finish(record, "outside.txt")
        result = self.collect()
        self.assertEqual(result["scope_check"], "FAIL")
        self.assertEqual(result["task_state"], "BLOCKED")

    def test_missing_test_evidence_blocks(self):
        record = self.prepare()
        self.finish(record, missing=True)
        self.assertEqual(self.collect()["task_state"], "BLOCKED")

    def test_dirty_worktree_rejected(self):
        record = self.prepare()
        (Path(record["worktree"]) / "untracked.txt").write_text("keep")
        with self.assertRaisesRegex(ValueError, "untracked/dirty"):
            self.collect()

    def test_contract_mutation_rejected(self):
        record = self.prepare(); self.finish(record)
        self.folder = self.root / ".ai/tasks/active/TASK-TEST"
        task = d.read_yaml(self.folder / "task.yaml")
        task["objective"] = "widened"
        (self.folder / "task.yaml").write_text(task_yaml(task))
        with self.assertRaisesRegex(ValueError, "contract changed"):
            self.collect()

    def test_receipt_revision_mismatch(self):
        record = self.prepare(); p = self.finish(record)
        receipt = d.read_yaml(p); receipt["attempt"] = 99
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "identity/revision"):
            self.collect()

    def test_lock_and_task_path_validation(self):
        with d.lock(self.root):
            with self.assertRaisesRegex(ValueError, "locked"):
                with d.lock(self.root):
                    pass
        for value in ("../escape", "TASK-../../x", "TASK-", "TASK-x/y"):
            with self.assertRaises(ValueError):
                d.task_id(value)

    def test_native_adapter_argv_and_no_duplicate_launch(self):
        self.prepare()
        adapter = AntigravityCLI(sys.executable, ["-c", "print('launch only')"], 5)
        record = d.launch(self.root, "TASK-TEST", adapter, True)
        self.assertEqual(record["phase"], "AWAITING_RECEIPT")
        with self.assertRaisesRegex(ValueError, "only once"):
            d.launch(self.root, "TASK-TEST", adapter, True)
        with self.assertRaisesRegex(ValueError, "not complete"):
            self.collect()

    def test_adapter_timeout_and_missing_binary(self):
        logs = self.root / ".ai/runtime/testlogs"; logs.mkdir(parents=True)
        adapter = AntigravityCLI(sys.executable, ["-c", "import time; time.sleep(2)"], .05)
        result = adapter.launch(self.root, self.root / "context", self.root / "receipt", logs)
        self.assertIsNone(result["exit_code"])
        self.assertEqual(result["completion"], "UNKNOWN")
        self.assertFalse(AntigravityCLI("missing-binary-237987").probe(logs)["available"])

    def test_protected_scope_even_with_broad_allowlist(self):
        self.task["scope"]["writable"] = ["**"]
        self.assertEqual(d.scope_violations([".ai/config.yaml", "AGENTS.md", "src/a.py"], self.task),
                         [".ai/config.yaml", "AGENTS.md"])

    def test_exhausted_attempt_budget(self):
        self.task["execution"]["max_execution_attempts"] = 1
        self.write_task(); self.commit()
        record = self.prepare(); self.finish(record); self.collect()
        with contextlib.redirect_stdout(io.StringIO()):
            d.ai.transition(self.root, "TASK-TEST", "READY")
        self.commit()
        with self.assertRaisesRegex(ValueError, "budget exhausted"):
            self.prepare()

    def test_cli_prepare_is_single_json_document(self):
        cp = subprocess.run([sys.executable, str(REPO / ".ai/scripts/delegate.py"),
                             "--repo", str(self.root), "prepare", "TASK-TEST", "--approve"],
                            capture_output=True, text=True)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(json.loads(cp.stdout)["phase"], "PREPARED")

    def test_high_risk_v2_flags_still_required(self):
        self.task["planning"]["risk"] = "high"
        self.write_task(); self.commit()
        self.assertEqual(d.route(self.task)["mode"], "approval_required")
        with self.assertRaisesRegex(ValueError, "Invalid V2 contract"):
            self.prepare()

    def test_nonzero_executor_does_not_complete(self):
        self.prepare()
        adapter = AntigravityCLI(sys.executable, ["-c", "raise SystemExit(7)"], 5)
        record = d.launch(self.root, "TASK-TEST", adapter, True)
        self.assertEqual(record["phase"], "LAUNCH_FAILED")
        self.assertEqual(record["launch"]["exit_code"], 7)
        self.assertEqual(d.ai.find_task(self.root, "TASK-TEST")[0], "IN_PROGRESS")

    def test_scope_covers_delete_and_rename(self):
        (self.root / "outside.txt").write_text("original")
        self.commit()
        record = self.prepare()
        wt = Path(record["worktree"])
        (wt / "src").mkdir()
        d.git(wt, "mv", "outside.txt", "src/moved.txt")
        d.git(wt, "commit", "-m", "rename")
        self.finish(record)
        result = self.collect()
        self.assertEqual(result["scope_check"], "FAIL")
        self.assertIn("outside.txt", result["changed_files_preview"])


if __name__ == "__main__":
    unittest.main()
