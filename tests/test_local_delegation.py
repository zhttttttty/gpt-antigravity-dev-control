import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / ".agents/skills/antigravity-delegate/scripts"))
import delegate as d
from antigravity_cli import AntigravityCLI, diagnose, diagnose_tool_handle, parse_stream_events


class TaskDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def task_yaml(task):
    return yaml.dump(task, Dumper=TaskDumper, sort_keys=False)


class LocalDelegationTests(unittest.TestCase):
    def test_adaptive_routing_keeps_explicit_approval_requirement(self):
        self.task["execution"]["mode"] = "approval_required"
        self.task["planning"].update(work_type="semantic", judgment="high")
        result = d.route(self.task)
        self.assertEqual(result["backend"], "direct")
        self.assertEqual(result["mode"], "approval_required")

    def test_verify_timeout_short_circuits_later_gate(self):
        slow = f'"{sys.executable}" -c "import time; time.sleep(20)"'
        self.task["checks"].update(adversarial_probes=[], fast_gate=[{"command": slow}],
                                   final_gate=[{"command": f'"{sys.executable}" -c "print(123)"'}], required=[])
        self.write_task(); self.commit()
        record = self.prepare()
        wt = Path(record["worktree"])
        target = wt / "src/result.txt"; target.parent.mkdir(parents=True); target.write_text("x")
        d.git(wt, "add", "src/result.txt"); d.git(wt, "commit", "-m", "implementation")
        receipt_path = wt / ".ai/runtime/delegation/receipt.executor.yaml"
        receipt = d.read_yaml(receipt_path); receipt.update(executor="antigravity", status="IMPLEMENTED")
        d.write_yaml(receipt_path, receipt)
        run_path = Path(record["run_dir"]) / "run.json"
        run = json.loads(run_path.read_text(encoding="utf-8")); run["phase"] = "AWAITING_VERIFICATION"; d.save(run_path, run)
        result = d.verify(self.root, "TASK-TEST", True, timeout=1, approval=self.approval())
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["commands"][0]["exit_code"], 124)
        self.assertEqual(result["commands"][1]["result"], "NOT_RUN")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="local delegation ")
        self.root = Path(self.temp.name).resolve()
        shutil.copytree(REPO / ".agents/skills/antigravity-delegate/templates", self.root / ".ai/templates")
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

    def approval(self, name="verify-approval.yaml"):
        path = self.root / ".ai/runtime" / name
        d.atomic(path, yaml.safe_dump({
            "task_id": "TASK-TEST", "contract_sha256": d.digest(self.task),
            "result": "APPROVED", "approved_by": "human",
            "evidence": "approved exact contract verification matrix",
        }))
        return path

    def finish(self, record, name="src/result.txt", missing=False):
        wt = Path(record["worktree"])
        file = wt / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("implemented\n", encoding="utf-8")
        d.git(wt, "add", name)
        d.git(wt, "commit", "-m", "implementation")
        head = d.git(wt, "rev-parse", "HEAD")
        p = wt / ".ai/runtime/delegation/receipt.executor.yaml"
        receipt = d.read_yaml(p)
        receipt.update(
            status="COMPLETE",
            workspace={
                "path": str(wt),
                "branch": record["branch"],
                "base_commit": record["base_commit"],
                "head_commit": head,
            },
            commands=[] if missing else [
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

    def test_adaptive_route_keeps_high_judgment_work_direct(self):
        self.task["planning"].update(
            work_type="semantic", judgment="high",
            context_continuity="high", acceptance_determinism="low",
        )
        routed = d.route(self.task)
        self.assertEqual((routed["mode"], routed["backend"]), ("direct", "direct"))
        self.write_task(); self.commit()
        with self.assertRaisesRegex(ValueError, "Direct task"):
            self.prepare()

        self.task["execution"]["routing_override"] = {
            "result": "APPROVED", "approved_by": "human",
            "evidence": "bounded mechanical implementation despite semantic review",
        }
        routed = d.route(self.task)
        self.assertEqual((routed["mode"], routed["backend"]),
                         ("approval_required", "antigravity"))
        self.write_task(); self.commit()
        with self.assertRaisesRegex(ValueError, "Pre-review approval"):
            self.prepare()

    def test_high_risk_high_judgment_is_approval_gated_direct(self):
        self.task["planning"].update(risk="high", work_type="security", judgment="high")
        routed = d.route(self.task)
        self.assertEqual((routed["mode"], routed["backend"]), ("approval_required", "direct"))

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

    def test_controller_verify_runs_staged_checks_and_completes_receipt(self):
        command = f'"{sys.executable}" -c "print(123)"'
        self.task["checks"].update(
            adversarial_probes=[], fast_gate=[{"command": command}],
            final_gate=[], required=[],
        )
        self.write_task(); self.commit()
        record = self.prepare()
        wt = Path(record["worktree"])
        target = wt / "src/result.txt"
        target.parent.mkdir(parents=True)
        target.write_text("implemented\n", encoding="utf-8")
        d.git(wt, "add", "src/result.txt"); d.git(wt, "commit", "-m", "implementation")
        receipt_path = wt / ".ai/runtime/delegation/receipt.executor.yaml"
        receipt = d.read_yaml(receipt_path)
        receipt.update(
            executor="antigravity", status="IMPLEMENTED",
            acceptance_evidence=[{"acceptance_id": "AC-001", "result": "PASS", "evidence": "src/result.txt"}],
        )
        d.write_yaml(receipt_path, receipt)
        run_path = Path(record["run_dir"]) / "run.json"
        run = json.loads(run_path.read_text(encoding="utf-8")); run["phase"] = "AWAITING_VERIFICATION"; d.save(run_path, run)

        verified = d.verify(self.root, "TASK-TEST", True, 20, approval=self.approval())
        self.assertEqual(verified["status"], "PASS")
        receipt = d.read_yaml(receipt_path)
        self.assertEqual(receipt["status"], "COMPLETE")
        self.assertEqual(receipt["commands"][0]["stage"], "fast_gate")
        self.assertEqual(self.collect()["task_state"], "REVIEW")

    def test_controller_verify_stops_after_failed_probe(self):
        fail = f'"{sys.executable}" -c "raise SystemExit(7)"'
        marker = self.root / "should-not-run.txt"
        final = f'"{sys.executable}" -c "from pathlib import Path; Path(r\'{marker}\').write_text(r\'bad\')"'
        self.task["checks"].update(
            adversarial_probes=[{"command": fail}], fast_gate=[],
            final_gate=[{"command": final}], required=[],
        )
        self.write_task(); self.commit()
        record = self.prepare(); wt = Path(record["worktree"])
        target = wt / "src/result.txt"; target.parent.mkdir(parents=True); target.write_text("x")
        d.git(wt, "add", "src/result.txt"); d.git(wt, "commit", "-m", "implementation")
        receipt_path = wt / ".ai/runtime/delegation/receipt.executor.yaml"
        receipt = d.read_yaml(receipt_path); receipt.update(executor="antigravity", status="IMPLEMENTED")
        d.write_yaml(receipt_path, receipt)
        run_path = Path(record["run_dir"]) / "run.json"
        run = json.loads(run_path.read_text(encoding="utf-8")); run["phase"] = "AWAITING_VERIFICATION"; d.save(run_path, run)
        result = d.verify(self.root, "TASK-TEST", True, 20, approval=self.approval())
        self.assertEqual(result["phase"], "VERIFICATION_FAILED")
        self.assertFalse(marker.exists())
        commands = d.read_yaml(receipt_path)["commands"]
        self.assertEqual([item["result"] for item in commands], ["FAIL", "NOT_RUN"])

    def test_controller_verify_rejects_failed_executor_and_unverified_collect(self):
        command = f'"{sys.executable}" -c "print(123)"'
        self.task["checks"].update(
            adversarial_probes=[], fast_gate=[{"command": command}],
            final_gate=[], required=[],
        )
        self.write_task(); self.commit()
        record = self.prepare(); wt = Path(record["worktree"])
        target = wt / "src/result.txt"; target.parent.mkdir(parents=True); target.write_text("x")
        d.git(wt, "add", "src/result.txt"); d.git(wt, "commit", "-m", "implementation")
        receipt_path = wt / ".ai/runtime/delegation/receipt.executor.yaml"
        receipt = d.read_yaml(receipt_path)
        receipt.update(executor="antigravity", status="FAILED")
        d.write_yaml(receipt_path, receipt)
        run_path = Path(record["run_dir"]) / "run.json"
        run = json.loads(run_path.read_text(encoding="utf-8")); run["phase"] = "AWAITING_VERIFICATION"; d.save(run_path, run)
        with self.assertRaisesRegex(ValueError, "status IMPLEMENTED"):
            d.verify(self.root, "TASK-TEST", True, 20)
        receipt["status"] = "COMPLETE"; d.write_yaml(receipt_path, receipt)
        with self.assertRaisesRegex(ValueError, "not ready for collection|require controller verification"):
            self.collect()

    def test_shell_check_requires_contract_bound_approval(self):
        command = f'"{sys.executable}" -c "print(123)"'
        self.task["checks"].update(
            adversarial_probes=[], fast_gate=[{"command": command, "shell": True}],
            final_gate=[], required=[],
        )
        self.write_task(); self.commit()
        record = self.prepare(); wt = Path(record["worktree"])
        target = wt / "src/result.txt"; target.parent.mkdir(parents=True); target.write_text("x")
        d.git(wt, "add", "src/result.txt"); d.git(wt, "commit", "-m", "implementation")
        receipt_path = wt / ".ai/runtime/delegation/receipt.executor.yaml"
        receipt = d.read_yaml(receipt_path); receipt.update(executor="antigravity", status="IMPLEMENTED")
        d.write_yaml(receipt_path, receipt)
        run_path = Path(record["run_dir"]) / "run.json"
        run = json.loads(run_path.read_text(encoding="utf-8")); run["phase"] = "AWAITING_VERIFICATION"; d.save(run_path, run)
        with self.assertRaisesRegex(ValueError, "Pre-review approval"):
            d.verify(self.root, "TASK-TEST", True, 20)
        self.assertFalse((Path(record["run_dir"]) / "verify").exists())

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
        self.assertEqual(record["phase"], "NEEDS_ATTENTION")
        self.assertEqual(record["launch"]["diagnostic"], "NO_COMPLETION_EVIDENCE")
        self.assertEqual(record["launch"]["output_format"], "NOT_APPLICABLE")
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

    def test_reuse_terminal_worktree_preserves_exact_untracked_candidate(self):
        self.task["scope"]["writable"] = ["src/result.txt"]
        self.write_task(); self.commit()
        first = self.prepare()
        worktree = Path(first["worktree"])
        candidate = worktree / "src/result.txt"
        candidate.parent.mkdir(parents=True)
        candidate.write_text("attempt-one-candidate\n", encoding="utf-8")
        run_one = Path(first["run_dir"]) / "run.json"
        failed = json.loads(run_one.read_text(encoding="utf-8"))
        failed["phase"] = "LAUNCH_FAILED"
        d.save(run_one, failed)

        with contextlib.redirect_stdout(io.StringIO()):
            d.ai.transition(self.root, "TASK-TEST", "BLOCKED")
            d.ai.transition(self.root, "TASK-TEST", "READY")
        self.folder = self.root / ".ai/tasks/queue/TASK-TEST"
        self.task = d.read_yaml(self.folder / "task.yaml")
        self.task["contract_revision"] = 2
        self.task["attempt"] = 2
        self.task["isolation"]["reuse_terminal_worktree"] = True
        self.write_task(); self.commit()
        with self.assertRaisesRegex(ValueError, "requires both"):
            d.prepare(self.root, "TASK-TEST", True)
        with self.assertRaisesRegex(ValueError, "process tree exited"):
            d.prepare(self.root, "TASK-TEST", True, reuse_terminal_worktree=True)

        with contextlib.redirect_stdout(io.StringIO()):
            second = d.prepare(
                self.root, "TASK-TEST", True, reuse_terminal_worktree=True,
                previous_process_exited=True
            )
        self.assertEqual(Path(second["worktree"]), worktree)
        self.assertEqual(second["base_commit"], first["base_commit"])
        self.assertEqual(second["branch"], "ai/local/TASK-TEST-2")
        self.assertEqual(d.git(worktree, "branch", "--show-current"), second["branch"])
        self.assertEqual(candidate.read_text(encoding="utf-8"), "attempt-one-candidate\n")
        self.assertEqual(second["reused_terminal_worktree"]["candidate_files"], ["src/result.txt"])
        receipt = d.read_yaml(worktree / ".ai/runtime/delegation/receipt.executor.yaml")
        self.assertEqual((receipt["contract_revision"], receipt["attempt"]), (2, 2))

    def test_reuse_tracked_worktree_requires_contract_and_approval(self):
        tracked = self.root / "src/result.txt"
        tracked.parent.mkdir(parents=True); tracked.write_text("base\n", encoding="utf-8")
        self.task["scope"]["writable"] = ["src/result.txt"]
        self.write_task(); self.commit()
        first = self.prepare(); worktree = Path(first["worktree"])
        (worktree / "src/result.txt").write_text("partial\n", encoding="utf-8")
        run_one = Path(first["run_dir"]) / "run.json"
        failed = json.loads(run_one.read_text(encoding="utf-8")); failed["phase"] = "LAUNCH_FAILED"; d.save(run_one, failed)
        with contextlib.redirect_stdout(io.StringIO()):
            d.ai.transition(self.root, "TASK-TEST", "BLOCKED")
            d.ai.transition(self.root, "TASK-TEST", "READY")
        self.folder = self.root / ".ai/tasks/queue/TASK-TEST"
        self.task = d.read_yaml(self.folder / "task.yaml")
        self.task.update(contract_revision=2, attempt=2)
        self.task["isolation"]["reuse_tracked_worktree"] = True
        self.write_task(); self.commit()
        approval = self.root / ".ai/runtime/tracked-approval.yaml"
        candidate_diff = subprocess.run(
            ["git", "diff", "--binary", "HEAD"], cwd=worktree,
            check=True, capture_output=True,
        ).stdout
        approval_data = {
            "task_id": "TASK-TEST", "contract_sha256": d.digest(self.task),
            "result": "APPROVED", "approved_by": "human",
            "evidence": "reuse exact scoped tracked partial after process exit",
        }
        d.atomic(approval, yaml.safe_dump(approval_data))
        with self.assertRaisesRegex(ValueError, "bind previous/current contracts"):
            d.prepare(
                self.root, "TASK-TEST", True, approval,
                reuse_tracked_worktree=True, previous_process_exited=True,
            )
        approval_data.update(
            previous_contract_sha256=first["contract_sha256"],
            candidate_diff_sha256=hashlib.sha256(candidate_diff).hexdigest(),
        )
        d.atomic(approval, yaml.safe_dump(approval_data))
        with contextlib.redirect_stdout(io.StringIO()):
            second = d.prepare(
                self.root, "TASK-TEST", True, approval,
                reuse_tracked_worktree=True, previous_process_exited=True,
            )
        self.assertEqual(Path(second["worktree"]), worktree)
        self.assertEqual(second["reused_terminal_worktree"]["candidate_kind"], "tracked")
        self.assertEqual((worktree / "src/result.txt").read_text(encoding="utf-8"), "partial\n")

    def test_reuse_tracked_worktree_rejects_untracked_candidate(self):
        self.task["scope"]["writable"] = ["src/new.txt"]
        self.write_task(); self.commit()
        first = self.prepare(); worktree = Path(first["worktree"])
        candidate = worktree / "src/new.txt"
        candidate.parent.mkdir(parents=True); candidate.write_text("untracked\n", encoding="utf-8")
        run_one = Path(first["run_dir"]) / "run.json"
        failed = json.loads(run_one.read_text(encoding="utf-8")); failed["phase"] = "LAUNCH_FAILED"; d.save(run_one, failed)
        with contextlib.redirect_stdout(io.StringIO()):
            d.ai.transition(self.root, "TASK-TEST", "BLOCKED")
            d.ai.transition(self.root, "TASK-TEST", "READY")
        self.folder = self.root / ".ai/tasks/queue/TASK-TEST"
        self.task = d.read_yaml(self.folder / "task.yaml")
        self.task.update(contract_revision=2, attempt=2)
        self.task["isolation"]["reuse_tracked_worktree"] = True
        self.write_task(); self.commit()
        with self.assertRaisesRegex(ValueError, "already-tracked"):
            d.prepare(
                self.root, "TASK-TEST", True, self.approval("tracked-untracked.yaml"),
                reuse_tracked_worktree=True, previous_process_exited=True,
            )

    def test_incremental_rework_context_prioritizes_previous_review(self):
        self.write_task(); self.commit()
        first = self.prepare()
        run_one = Path(first["run_dir"]) / "run.json"
        failed = json.loads(run_one.read_text(encoding="utf-8")); failed["phase"] = "LAUNCH_FAILED"; d.save(run_one, failed)
        with contextlib.redirect_stdout(io.StringIO()):
            d.ai.transition(self.root, "TASK-TEST", "BLOCKED")
            d.ai.transition(self.root, "TASK-TEST", "READY")
        self.folder = self.root / ".ai/tasks/queue/TASK-TEST"
        self.task = d.read_yaml(self.folder / "task.yaml")
        self.task.update(contract_revision=2, attempt=2)
        self.task["execution"]["context_budget"] = "incremental"
        review = self.folder / "history/attempt-1/review.yaml"
        review.parent.mkdir(parents=True)
        review.write_text("verdict: REWORK\nfindings:\n- issue: exact failure\n", encoding="utf-8")
        self.write_task(); self.commit()
        with contextlib.redirect_stdout(io.StringIO()):
            second = d.prepare(self.root, "TASK-TEST", True)
        context = (Path(second["run_dir"]) / "context.md").read_text(encoding="utf-8")
        self.assertIn("rework-delta.yaml", context)
        self.assertIn("exact failure", context)
        self.assertNotIn("## context.md", context)

    def test_reuse_terminal_worktree_rejects_manifest_drift(self):
        self.task["scope"]["writable"] = ["src/result.txt"]
        self.write_task(); self.commit()
        first = self.prepare()
        worktree = Path(first["worktree"])
        (worktree / "extra.txt").write_text("unexpected\n", encoding="utf-8")
        run_one = Path(first["run_dir"]) / "run.json"
        failed = json.loads(run_one.read_text(encoding="utf-8"))
        failed["phase"] = "LAUNCH_FAILED"
        d.save(run_one, failed)
        with contextlib.redirect_stdout(io.StringIO()):
            d.ai.transition(self.root, "TASK-TEST", "BLOCKED")
            d.ai.transition(self.root, "TASK-TEST", "READY")
        self.folder = self.root / ".ai/tasks/queue/TASK-TEST"
        self.task = d.read_yaml(self.folder / "task.yaml")
        self.task["contract_revision"] = 2
        self.task["attempt"] = 2
        self.task["isolation"]["reuse_terminal_worktree"] = True
        self.write_task(); self.commit()
        with self.assertRaisesRegex(ValueError, "manifest mismatch"):
            d.prepare(self.root, "TASK-TEST", True, reuse_terminal_worktree=True,
                      previous_process_exited=True)

    def test_reuse_failure_rolls_branch_and_record_back_consistently(self):
        self.task["scope"]["writable"] = ["src/result.txt"]
        self.write_task(); self.commit()
        first = self.prepare()
        worktree = Path(first["worktree"])
        candidate = worktree / "src/result.txt"
        candidate.parent.mkdir(parents=True)
        candidate.write_text("candidate\n", encoding="utf-8")
        run_one = Path(first["run_dir"]) / "run.json"
        failed = json.loads(run_one.read_text(encoding="utf-8"))
        failed["phase"] = "LAUNCH_FAILED"
        d.save(run_one, failed)
        with contextlib.redirect_stdout(io.StringIO()):
            d.ai.transition(self.root, "TASK-TEST", "BLOCKED")
            d.ai.transition(self.root, "TASK-TEST", "READY")
        self.folder = self.root / ".ai/tasks/queue/TASK-TEST"
        self.task = d.read_yaml(self.folder / "task.yaml")
        self.task["contract_revision"] = 2
        self.task["attempt"] = 2
        self.task["isolation"]["reuse_terminal_worktree"] = True
        self.write_task(); self.commit()
        with patch.object(d, "write_yaml", side_effect=OSError("forced write failure")):
            with self.assertRaisesRegex(OSError, "forced write failure"):
                d.prepare(self.root, "TASK-TEST", True,
                          reuse_terminal_worktree=True,
                          previous_process_exited=True)
        run_two = self.root / ".ai/runtime/logs/TASK-TEST/run-2/run.json"
        record = json.loads(run_two.read_text(encoding="utf-8"))
        self.assertEqual(record["phase"], "BLOCKED")
        self.assertEqual(record["branch"], first["branch"])
        self.assertTrue(record["reused_terminal_worktree"]["rolled_back"])
        self.assertEqual(d.git(worktree, "branch", "--show-current"), first["branch"])
        self.assertEqual(candidate.read_text(encoding="utf-8"), "candidate\n")

    def test_reuse_rejects_previous_record_identity_drift(self):
        self.task["scope"]["writable"] = ["src/result.txt"]
        self.write_task(); self.commit()
        first = self.prepare()
        worktree = Path(first["worktree"])
        candidate = worktree / "src/result.txt"
        candidate.parent.mkdir(parents=True)
        candidate.write_text("candidate\n", encoding="utf-8")
        run_one = Path(first["run_dir"]) / "run.json"
        failed = json.loads(run_one.read_text(encoding="utf-8"))
        failed.update(phase="LAUNCH_FAILED", task_id="TASK-OTHER")
        d.save(run_one, failed)
        with contextlib.redirect_stdout(io.StringIO()):
            d.ai.transition(self.root, "TASK-TEST", "BLOCKED")
            d.ai.transition(self.root, "TASK-TEST", "READY")
        self.folder = self.root / ".ai/tasks/queue/TASK-TEST"
        self.task = d.read_yaml(self.folder / "task.yaml")
        self.task["contract_revision"] = 2
        self.task["attempt"] = 2
        self.task["isolation"]["reuse_terminal_worktree"] = True
        self.write_task(); self.commit()
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            d.prepare(self.root, "TASK-TEST", True,
                      reuse_terminal_worktree=True,
                      previous_process_exited=True)

    def test_cli_prepare_is_single_json_document(self):
        cp = subprocess.run([sys.executable, str(REPO / ".agents/skills/antigravity-delegate/scripts/delegate.py"),
                             "--repo", str(self.root), "prepare", "TASK-TEST", "--approve"],
                            capture_output=True, text=True)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(json.loads(cp.stdout)["phase"], "PREPARED")

    def test_high_risk_core_flags_still_required(self):
        self.task["planning"]["risk"] = "high"
        self.write_task(); self.commit()
        self.assertEqual(d.route(self.task)["mode"], "approval_required")
        with self.assertRaisesRegex(ValueError, "Invalid task contract"):
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

    def test_permission_diagnostic_is_sanitized(self):
        log = self.root / "fake-cli.log"
        log.write_text('access_token=SECRET\nPrint mode: soft-denying tool confirmation "ViewFile" at step 2')
        self.assertEqual(diagnose(self.root / "absent.yaml", [log]), "PERMISSION_BLOCKED")
        log.write_text('jetski: no output produced — a tool required the "command" permission that headless mode cannot prompt for, so it was auto-denied.')
        self.assertEqual(diagnose(self.root / "absent.yaml", [log]), "PERMISSION_BLOCKED")
        log.write_text('jetski: no output produced')
        self.assertEqual(diagnose(self.root / "absent.yaml", [log]), "EMPTY_OUTPUT")
        log.write_text('You are not logged into Antigravity.')
        self.assertEqual(diagnose(self.root / "absent.yaml", [log]), "AUTH_REQUIRED")
        log.write_text('You are not logged into Antigravity.\nPrint mode: silent auth succeeded')
        self.assertEqual(diagnose(self.root / "absent.yaml", [log]), "RECEIPT_MISSING")

    def test_receipt_diagnostic_does_not_approve(self):
        p = self.root / "receipt.yaml"
        p.write_text('status: COMPLETE\n')
        self.assertEqual(diagnose(p, []), "RECEIPT_PRESENT_UNVERIFIED")
        p.write_text('[')
        self.assertEqual(diagnose(p, []), "RECEIPT_INVALID")
        p.write_text('x' * 128001)
        self.assertEqual(diagnose(p, []), "RECEIPT_INVALID")

    def test_interactive_requires_tty_before_state_mutation(self):
        self.prepare()
        with patch('antigravity_cli.sys.stdin.isatty', return_value=False):
            with self.assertRaisesRegex(ValueError, "real terminal"):
                d.launch(self.root, "TASK-TEST", AntigravityCLI(sys.executable, interactive=True), True)
        self.assertEqual(d.latest(self.root, "TASK-TEST")[1]["phase"], "PREPARED")

    def test_interactive_inherits_terminal_and_keeps_permissions(self):
        logs = self.root / ".ai/runtime/interactive"; logs.mkdir(parents=True)
        receipt = logs / "receipt.yaml"; receipt.write_text('status: COMPLETE\n')
        adapter = AntigravityCLI(sys.executable, interactive=True)
        with patch('antigravity_cli.sys.stdin.isatty', return_value=True), \
             patch('antigravity_cli.sys.stdout.isatty', return_value=True), \
             patch('antigravity_cli.subprocess.run') as run:
            run.return_value.returncode = 0
            run.return_value.stdout = '--mode Set mode (accept-edits, plan)\n--print Run a prompt\n-i Run interactive\n--dangerously-skip-permissions\n'
            result = adapter.launch(self.root, logs / "context.md", receipt, logs)
        argv = run.call_args.args[0]
        self.assertIn('-i', argv)
        self.assertIn('--add-dir', argv)
        self.assertNotIn('--dangerously-skip-permissions', argv)
        self.assertNotIn('stdin', run.call_args.kwargs)
        self.assertNotIn('stdout', run.call_args.kwargs)
        self.assertEqual(result['diagnostic'], 'RECEIPT_PRESENT_UNVERIFIED')

    def test_full_access_is_explicit_and_only_changes_argv(self):
        logs = self.root / ".ai/runtime/full-access"; logs.mkdir(parents=True)
        receipt = logs / "receipt.yaml"; receipt.write_text('status: COMPLETE\n')
        adapter = AntigravityCLI(sys.executable, interactive=True, full_access=True)
        with patch('antigravity_cli.sys.stdin.isatty', return_value=True), \
             patch('antigravity_cli.sys.stdout.isatty', return_value=True), \
             patch('antigravity_cli.subprocess.run') as run:
            run.return_value.returncode = 0
            run.return_value.stdout = '--mode Set mode (accept-edits, plan)\n--print Run a prompt\n-i Run interactive\n--dangerously-skip-permissions\n'
            adapter.launch(self.root, logs / "context.md", receipt, logs)
        argv = run.call_args.args[0]
        self.assertIn('--dangerously-skip-permissions', argv)
        self.assertIn('--add-dir', argv)
        self.assertNotIn('--sandbox', argv)

    def test_full_access_requires_approval_at_cli_boundary(self):
        self.prepare()
        cp = subprocess.run([sys.executable, str(REPO / '.agents/skills/antigravity-delegate/scripts/delegate.py'),
                             '--repo', str(self.root), 'launch', 'TASK-TEST', '--full-access'],
                            capture_output=True, text=True)
        self.assertEqual(cp.returncode, 2)
        self.assertIn('requires explicit --approve', cp.stderr)

    def test_auto_approve_requires_approval_at_cli_boundary(self):
        self.prepare()
        cp = subprocess.run([sys.executable, str(REPO / '.agents/skills/antigravity-delegate/scripts/delegate.py'),
                             '--repo', str(self.root), 'launch', 'TASK-TEST', '--auto-approve'],
                            capture_output=True, text=True)
        self.assertEqual(cp.returncode, 2)
        self.assertIn('requires explicit --approve', cp.stderr)

    def test_one_interactive_recovery_preserves_logs(self):
        self.prepare()
        d.launch(self.root, 'TASK-TEST', AntigravityCLI(sys.executable, ['-c', "print('first')"], 5), True)
        class InteractiveFixture:
            interactive = True
            def validate_launch(self): pass
            def launch(self, worktree, context, receipt, logs):
                (logs / 'launch.log').write_text('second')
                return {'exit_code': 0, 'diagnostic': 'NO_COMPLETION_EVIDENCE', 'log': str(logs / 'launch.log')}
        record = d.launch(self.root, 'TASK-TEST', InteractiveFixture(), True, recover=True)
        self.assertEqual(len(record['launch_history']), 2)
        self.assertIn('first', (Path(record['run_dir']) / 'launch-1/launch.log').read_text())
        self.assertEqual((Path(record['run_dir']) / 'launch-2/launch.log').read_text(), 'second')
        with self.assertRaisesRegex(ValueError, 'budget exhausted'):
            d.launch(self.root, 'TASK-TEST', InteractiveFixture(), True, recover=True)

    def test_recovery_cannot_be_unconfirmed_or_print(self):
        self.prepare()
        adapter = AntigravityCLI(sys.executable, ['-c', 'pass'], 5)
        d.launch(self.root, 'TASK-TEST', adapter, True)
        with self.assertRaisesRegex(ValueError, 'confirmation'):
            d.launch(self.root, 'TASK-TEST', adapter, recover=True)
        with self.assertRaisesRegex(ValueError, '--interactive'):
            d.launch(self.root, 'TASK-TEST', adapter, True, recover=True)

    def test_status_available_while_mutation_lock_held(self):
        self.prepare()
        with d.lock(self.root):
            cp = subprocess.run([sys.executable, str(REPO / '.agents/skills/antigravity-delegate/scripts/delegate.py'),
                                 '--repo', str(self.root), 'status', 'TASK-TEST'],
                                capture_output=True, text=True)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertEqual(json.loads(cp.stdout)['phase'], 'PREPARED')

    def test_print_no_receipt_cli_exits_nonzero(self):
        self.prepare()
        argsfile = self.root / '.ai/runtime/argv.json'
        argsfile.write_text(json.dumps(['-c', "print('not completion')"]))
        cp = subprocess.run([sys.executable, str(REPO / '.agents/skills/antigravity-delegate/scripts/delegate.py'),
                             '--repo', str(self.root), 'launch', 'TASK-TEST', '--approve',
                             '--executable', sys.executable, '--args-file', str(argsfile)],
                            capture_output=True, text=True)
        self.assertEqual(cp.returncode, 2, cp.stderr)
        self.assertEqual(json.loads(cp.stdout)['phase'], 'NEEDS_ATTENTION')

    def test_diagnose_recovered_auth_and_true_auth_failures(self):
        log = self.root / "auth-test.log"
        receipt = self.root / "receipt-auth-test.yaml"
        receipt.write_text("status: COMPLETE\n")

        # Recovered auth: earlier warning, later successful authorization + valid receipt -> RECEIPT_PRESENT_UNVERIFIED
        log.write_text("You are not logged into Antigravity.\nPrint mode: silent auth succeeded\n")
        self.assertEqual(diagnose(receipt, [log]), "RECEIPT_PRESENT_UNVERIFIED")

        # Recovered auth with explicit authorization succeeded message
        log.write_text("You are not logged into Antigravity.\nAuthorization succeeded\n")
        self.assertEqual(diagnose(receipt, [log]), "RECEIPT_PRESENT_UNVERIFIED")

        # Recovered auth but receipt missing -> RECEIPT_MISSING
        self.assertEqual(diagnose(self.root / "absent.yaml", [log]), "RECEIPT_MISSING")

        # True auth failure: warning without later successful auth -> AUTH_REQUIRED even if receipt valid
        log.write_text("You are not logged into Antigravity.\n")
        self.assertEqual(diagnose(receipt, [log]), "AUTH_REQUIRED")

        # True auth failure: auth success happened earlier, but warning happened later -> AUTH_REQUIRED
        log.write_text("Print mode: silent auth succeeded\nYou are not logged into Antigravity.\n")
        self.assertEqual(diagnose(receipt, [log]), "AUTH_REQUIRED")

    def test_collect_workspace_base_head_validation(self):
        record = self.prepare()
        p = self.finish(record)
        receipt = d.read_yaml(p)
        wt = Path(record["worktree"])
        head = d.git(wt, "rev-parse", "HEAD")
        valid_ws = {
            "path": str(wt),
            "branch": record["branch"],
            "base_commit": record["base_commit"],
            "head_commit": head,
        }

        # Wrong base commit in workspace
        receipt["workspace"] = {**valid_ws, "base_commit": "0" * 40}
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "base commit mismatch"):
            self.collect()

        # Wrong head commit in workspace
        receipt["workspace"] = {**valid_ws, "head_commit": "0" * 40}
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "head commit mismatch"):
            self.collect()

        # Wrong branch in workspace
        receipt["workspace"] = {**valid_ws, "branch": "wrong-branch"}
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "branch mismatch"):
            self.collect()

        # Wrong path in workspace
        receipt["workspace"] = {**valid_ws, "path": str(self.root / "wrong-path")}
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "path mismatch"):
            self.collect()

        # Null workspace
        receipt["workspace"] = None
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "Malformed workspace: expected mapping"):
            self.collect()

        # Empty dict workspace
        receipt["workspace"] = {}
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "Malformed workspace: path must be a nonempty string"):
            self.collect()

        # Partial workspace missing field
        receipt["workspace"] = {"path": str(wt), "branch": record["branch"], "base_commit": record["base_commit"]}
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "Malformed workspace: head_commit must be a nonempty string"):
            self.collect()

        # Null field in workspace
        receipt["workspace"] = {**valid_ws, "base_commit": None}
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "Malformed workspace: base_commit must be a nonempty string"):
            self.collect()

        # Empty string field in workspace
        receipt["workspace"] = {**valid_ws, "branch": "   "}
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "Malformed workspace: branch must be a nonempty string"):
            self.collect()

    def test_collect_rejects_malformed_completion_and_evidence(self):
        record = self.prepare()
        p = self.finish(record)
        receipt = d.read_yaml(p)

        # Malformed completion status: SUCCESS
        receipt["status"] = "SUCCESS"
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "status must be COMPLETE, BLOCKED, or FAILED"):
            self.collect()

        # Malformed completion status: COMPLETED
        receipt["status"] = "COMPLETED"
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "status must be COMPLETE, BLOCKED, or FAILED"):
            self.collect()

        # Malformed command result: PASSED
        receipt["status"] = "COMPLETE"
        receipt["commands"] = [{"command": "python -m unittest", "exit_code": 0, "result": "PASSED"}]
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "Malformed command result"):
            self.collect()

        # Malformed command evidence: status instead of result
        receipt["commands"] = [{"command": "python -m unittest", "exit_code": 0, "status": "PASS"}]
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "status field used instead of result"):
            self.collect()

        # Malformed acceptance evidence: id instead of acceptance_id
        receipt["commands"] = [{"command": "python -m unittest", "exit_code": 0, "result": "PASS"}]
        receipt["acceptance_evidence"] = [{"id": "AC-001", "result": "PASS", "evidence": "src/result.txt"}]
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "id field used instead of acceptance_id"):
            self.collect()

        # Malformed acceptance evidence: status instead of result
        receipt["acceptance_evidence"] = [{"acceptance_id": "AC-001", "status": "PASS", "evidence": "src/result.txt"}]
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "status field used instead of result"):
            self.collect()

        # Malformed acceptance evidence: result PASSED instead of PASS
        receipt["acceptance_evidence"] = [{"acceptance_id": "AC-001", "result": "PASSED", "evidence": "src/result.txt"}]
        p.write_text(yaml.safe_dump(receipt))
        with self.assertRaisesRegex(ValueError, "Malformed acceptance result"):
            self.collect()

    def test_collect_structured_optional_not_run_positive(self):
        self.task["checks"]["optional"] = [{"command": "flake8 .", "purpose": "linter"}]
        self.write_task(); self.commit()
        record = self.prepare()
        p = self.finish(record)
        receipt = d.read_yaml(p)
        receipt["unverified_items"] = [{"command": "flake8 .", "result": "NOT_RUN", "reason": "offline env"}]
        p.write_text(yaml.safe_dump(receipt))
        result = self.collect()
        self.assertEqual(result["task_state"], "REVIEW")

    def test_collect_unverified_required_blocks(self):
        self.task["checks"]["optional"] = [{"command": "flake8 .", "purpose": "linter"}]
        self.write_task(); self.commit()
        record = self.prepare()
        p = self.finish(record)
        receipt = d.read_yaml(p)
        receipt["unverified_items"] = [{"command": "python -m unittest", "result": "NOT_RUN", "reason": "skipped"}]
        p.write_text(yaml.safe_dump(receipt))
        result = self.collect()
        self.assertEqual(result["task_state"], "BLOCKED")

    def test_collect_unverified_unknown_blocks(self):
        self.task["checks"]["optional"] = [{"command": "flake8 .", "purpose": "linter"}]
        self.write_task(); self.commit()
        record = self.prepare()
        p = self.finish(record)
        receipt = d.read_yaml(p)
        receipt["unverified_items"] = [{"command": "unknown-check", "result": "NOT_RUN", "reason": "skipped"}]
        p.write_text(yaml.safe_dump(receipt))
        result = self.collect()
        self.assertEqual(result["task_state"], "BLOCKED")

    def test_collect_unverified_unstructured_blocks(self):
        self.task["checks"]["optional"] = [{"command": "flake8 .", "purpose": "linter"}]
        self.write_task(); self.commit()
        record = self.prepare()
        p = self.finish(record)
        receipt = d.read_yaml(p)
        receipt["unverified_items"] = ["flake8 ."]
        p.write_text(yaml.safe_dump(receipt))
        result = self.collect()
        self.assertEqual(result["task_state"], "BLOCKED")

    def test_collect_unverified_empty_reason_blocks(self):
        self.task["checks"]["optional"] = [{"command": "flake8 .", "purpose": "linter"}]
        self.write_task(); self.commit()
        record = self.prepare()
        p = self.finish(record)
        receipt = d.read_yaml(p)
        receipt["unverified_items"] = [{"command": "flake8 .", "result": "NOT_RUN", "reason": "   "}]
        p.write_text(yaml.safe_dump(receipt))
        result = self.collect()
        self.assertEqual(result["task_state"], "BLOCKED")

    def test_collect_known_issues_enter_review_with_marker(self):
        record = self.prepare()
        p = self.finish(record)
        receipt = d.read_yaml(p)
        issue_text = "performance warning on windows file lock"
        receipt["known_issues"] = [issue_text]
        p.write_text(yaml.safe_dump(receipt))

        result = self.collect()
        self.assertEqual(result["task_state"], "REVIEW")
        self.assertNotEqual(result.get("issue_marker"), "PASS")
        self.assertEqual(result.get("issue_marker"), "REPORTED")
        self.assertIn(issue_text, str(result["known_issues"]))

    def test_argv_prompt_and_no_default_disable_slash_commands(self):
        logs = self.root / ".ai/runtime/test-argv"
        logs.mkdir(parents=True, exist_ok=True)
        adapter = AntigravityCLI(sys.executable)
        with patch.object(adapter, "capabilities", return_value={
            "mode": True,
            "stream_json": True,
            "print_arg": "--print",
            "interactive_arg": "-i",
            "permission_bypass": False,
        }):
            argv = adapter.argv(self.root, self.root / "context.md", self.root / "receipt.yaml", logs)

        # 1. No default disable-slash-commands
        self.assertNotIn("--disable-slash-commands", argv)
        # 2. Capability-gated stream-json is added
        self.assertIn("--output-format", argv)
        self.assertIn("stream-json", argv)

        # 3. Prompt regression checks
        prompt_arg = [arg for arg in argv if arg.startswith("--print=")][0]
        self.assertIn("relative paths in worktree cwd", prompt_arg)
        self.assertIn("never absolute Windows drive paths in grep_search", prompt_arg)
        self.assertIn("Prefer synchronous bounded commands", prompt_arg)
        self.assertIn("Print-mode command workflow uses actual returned handle", prompt_arg)
        self.assertIn("TaskId", prompt_arg)
        self.assertIn("manage_task status", prompt_arg)
        self.assertIn("CommandId", prompt_arg)
        self.assertIn("command_status", prompt_arg)
        self.assertIn("Do not use schedule, timers, or passively narrate waiting", prompt_arg)
        self.assertIn("Read returned actual stdout/stderr; do not claim missing exit codes", prompt_arg)

        # 4. Explicit fallback when stream_json capability is not present
        with patch.object(adapter, "capabilities", return_value={
            "mode": True,
            "stream_json": False,
            "print_arg": "--print",
            "interactive_arg": "-i",
            "permission_bypass": False,
        }):
            argv_fallback = adapter.argv(self.root, self.root / "context.md", self.root / "receipt.yaml", logs)
        self.assertNotIn("--output-format", argv_fallback)
        self.assertNotIn("stream-json", argv_fallback)

    def test_tool_handle_diagnostic_real_and_unknown(self):
        # 1. Real TaskId handle from run_command background output
        real_task_output = 'Tool is running as a background task with task id: a742edb0/task-70'
        diag = diagnose_tool_handle(real_task_output)
        self.assertEqual(diag["status"], "VALID")
        self.assertEqual(diag["handle_type"], "task_id")
        self.assertEqual(diag["handle"], "a742edb0/task-70")
        self.assertEqual(diag["poll_tool"], "manage_task")
        self.assertEqual(diag["poll_action"], "status")

        # Dict TaskId
        diag_dict = diagnose_tool_handle({"TaskId": "task-42"})
        self.assertEqual(diag_dict["status"], "VALID")
        self.assertEqual(diag_dict["handle_type"], "task_id")
        self.assertEqual(diag_dict["handle"], "task-42")

        # 2. Real CommandId handle
        real_cmd_output = 'CommandId: cmd-999'
        diag_cmd = diagnose_tool_handle(real_cmd_output)
        self.assertEqual(diag_cmd["status"], "VALID")
        self.assertEqual(diag_cmd["handle_type"], "command_id")
        self.assertEqual(diag_cmd["handle"], "cmd-999")
        self.assertEqual(diag_cmd["poll_tool"], "command_status")

        # Dict CommandId
        diag_cmd_dict = diagnose_tool_handle({"CommandId": "cmd-888"})
        self.assertEqual(diag_cmd_dict["status"], "VALID")
        self.assertEqual(diag_cmd_dict["handle_type"], "command_id")
        self.assertEqual(diag_cmd_dict["handle"], "cmd-888")

        # 3. Synchronous command bounded exit code
        sync_output = 'The command exited with code 0.'
        diag_sync = diagnose_tool_handle(sync_output)
        self.assertEqual(diag_sync["status"], "COMPLETED")
        self.assertEqual(diag_sync["handle_type"], "synchronous")
        self.assertEqual(diag_sync["exit_code"], 0)

        # Dict synchronous exit code
        diag_sync_dict = diagnose_tool_handle({"exit_code": 0})
        self.assertEqual(diag_sync_dict["status"], "COMPLETED")
        self.assertEqual(diag_sync_dict["exit_code"], 0)

        # 4. Passive narration or schedule/timer waiting is blocked
        passive_cases = [
            "timer task-46 fired but agent passively narrated waiting",
            "I have set a schedule to check later",
            "Waiting for background task to complete...",
            "Still running, waiting",
        ]
        for case in passive_cases:
            with self.subTest(case=case):
                diag_p = diagnose_tool_handle(case)
                self.assertEqual(diag_p["status"], "BLOCKED")
                self.assertEqual(diag_p["handle_type"], "passive_waiting")

        # 5. Unknown handle formats preserved as blockers
        unknown_cases = [
            "random unparseable output without handle or code",
            {"unknown_key": "val"},
            "",
        ]
        for case in unknown_cases:
            with self.subTest(case=case):
                diag_u = diagnose_tool_handle(case)
                self.assertEqual(diag_u["status"], "BLOCKED")

        # 6. Null/empty/nonstring TaskId/CommandId must not be VALID
        invalid_handles = [
            {"TaskId": None},
            {"TaskId": ""},
            {"TaskId": 123},
            {"CommandId": None},
            {"CommandId": ""},
            {"CommandId": 456},
            "TaskId: null",
            "TaskId: none",
            "TaskId: ",
            "CommandId: null",
            "CommandId: none",
            "CommandId: ",
            None,
            123,
            ["TaskId"],
        ]
        for bad in invalid_handles:
            with self.subTest(bad=bad):
                diag_bad = diagnose_tool_handle(bad)
                self.assertEqual(diag_bad["status"], "BLOCKED")

    def test_stream_json_tool_events_and_malformed_handling(self):
        # Offline stream events
        offline_ndjson = "\n".join([
            '{"event":"init","init":{"cwd":"/repo","tools":["run_command"]}}',
            '{"event":"step_update","step_update":{"conversation_id":"c1","step_index":1,"state":"ACTIVE","step_type":"tool","tool_name":"run_command","tool_info":{"name":"run_command","parameters":{"CommandLine":"pytest"}}}}',
            '{"event":"step_update","step_update":{"conversation_id":"c1","step_index":1,"state":"DONE","step_type":"tool","tool_name":"run_command","duration_seconds":1.5,"tool_info":{"name":"run_command","result":"Tool is running as a background task with task id: t-1"}}}',
            '{"event":"result","result":{"conversation_id":"c1","status":"SUCCESS","duration_seconds":2.0}}',
        ])
        events = parse_stream_events(offline_ndjson)
        self.assertEqual(len(events), 3)

        # Tool start event
        start_ev = events[0]
        self.assertEqual(start_ev["event"], "tool_start")
        self.assertEqual(start_ev["tool_name"], "run_command")
        self.assertEqual(start_ev["state"], "ACTIVE")

        # Tool completion event
        comp_ev = events[1]
        self.assertEqual(comp_ev["event"], "tool_completion")
        self.assertEqual(comp_ev["tool_name"], "run_command")
        self.assertEqual(comp_ev["state"], "DONE")
        self.assertEqual(comp_ev["duration_seconds"], 1.5)
        self.assertEqual(comp_ev["handle"], "t-1")
        # Do not claim exit code when unavailable in tool event
        self.assertIsNone(comp_ev["exit_code"])

        # Session result event: records status SUCCESS, but text/session exit 0 is not task PASS
        res_ev = events[2]
        self.assertEqual(res_ev["event"], "session_result")
        self.assertEqual(res_ev["status"], "SUCCESS")

        # Actual tool_info.output regression event
        real_output_ndjson = (
            '{"event":"step_update","step_update":{"conversation_id":"c1","step_index":2,"state":"DONE",'
            '"step_type":"tool","tool_name":"run_command","duration_seconds":1.2,'
            '"tool_info":{"name":"run_command","output":"Tool is running as a background task with task id: t-2"}}}'
        )
        real_evs = parse_stream_events(real_output_ndjson)
        self.assertEqual(len(real_evs), 1)
        self.assertEqual(real_evs[0]["handle"], "t-2")
        self.assertEqual(real_evs[0]["output"], "Tool is running as a background task with task id: t-2")
        self.assertEqual(real_evs[0]["result"], "Tool is running as a background task with task id: t-2")
        self.assertEqual(real_evs[0]["timestamp"], "UNKNOWN")

        # Timestamp preserved when present
        timed_output_ndjson = (
            '{"event":"step_update","step_update":{"conversation_id":"c1","step_index":3,"state":"DONE",'
            '"step_type":"tool","tool_name":"run_command","timestamp":"2026-09-16T12:00:00Z",'
            '"tool_info":{"name":"run_command","output":"Exited with code 0."}}}'
        )
        timed_evs = parse_stream_events(timed_output_ndjson)
        self.assertEqual(timed_evs[0]["timestamp"], "2026-09-16T12:00:00Z")

        # Malformed step/tool_info/result types rejected without crash
        malformed_types = "\n".join([
            '{"event":"step_update","step_update":"not_a_dict"}',
            '{"event":"step_update","step_update":{"step_type":"tool","tool_info":"not_a_dict"}}',
            '{"event":"result","result":"not_a_dict"}',
        ])
        m_type_evs = parse_stream_events(malformed_types)
        self.assertTrue(all(e.get("status") == "MALFORMED" for e in m_type_evs))

        # Malformed or truncated events handling
        malformed_ndjson = "\n".join([
            '{"event":"step_update","step_update":{"conversation_id":"c1","step_index":1,"state":"ACTIVE","step_type":"tool","tool_name":"test"}}',
            'NOT_VALID_JSON_LINE',
            '{"truncated_json": ',
            '',
            '{"event":"result","result":{"status":"SUCCESS"}}',
        ])
        m_events = parse_stream_events(malformed_ndjson)
        # Does not crash, records malformed line or parses valid ones
        self.assertTrue(any(e.get("event") == "tool_start" for e in m_events))
        self.assertTrue(any(e.get("status") == "MALFORMED" for e in m_events))

        mixed_events = parse_stream_events('progress narration\n{"event":"result","result":{"status":"SUCCESS"}}')
        self.assertEqual(mixed_events[0]["status"], "MIXED_OUTPUT")
        self.assertEqual(mixed_events[1]["event"], "session_result")

    def test_managed_mixed_output_is_invalid_but_permission_has_precedence(self):
        logs = self.root / ".ai/runtime/mixed-output"
        logs.mkdir(parents=True)
        receipt = logs / "receipt.yaml"
        receipt.write_text("status: COMPLETE\n")
        adapter = AntigravityCLI(sys.executable)

        def fake_run(argv, **kwargs):
            if "--help" in argv:
                return type("Completed", (), {
                    "returncode": 0,
                    "stdout": "--mode Set mode (accept-edits, plan)\n--print Run a prompt\n-i Run interactive\n--output-format stream-json\n",
                })()
            kwargs["stdout"].write(b'progress narration\n{"event":"result","result":{"status":"SUCCESS"}}\n')
            return type("Completed", (), {"returncode": 0})()

        with patch("antigravity_cli.subprocess.run", side_effect=fake_run):
            result = adapter.launch(self.root, logs / "context.md", receipt, logs)
        self.assertEqual(result["output_format"], "INVALID")
        self.assertEqual(result["diagnostic"], "FORMAT_INVALID")

        permission_adapter = AntigravityCLI(sys.executable)

        def fake_permission_run(argv, **kwargs):
            if "--help" in argv:
                return type("Completed", (), {
                    "returncode": 0,
                    "stdout": "--mode Set mode (accept-edits, plan)\n--print Run a prompt\n-i Run interactive\n--output-format stream-json\n",
                })()
            kwargs["stdout"].write(
                b'jetski: no output produced - a permission that headless mode cannot prompt for was auto-denied.\n'
                b'{"event":"result","result":{"status":"SUCCESS"}}\n'
            )
            return type("Completed", (), {"returncode": 0})()

        with patch("antigravity_cli.subprocess.run", side_effect=fake_permission_run):
            permission_result = permission_adapter.launch(self.root, logs / "context.md", receipt, logs)
        self.assertEqual(permission_result["diagnostic"], "PERMISSION_BLOCKED")
        self.assertEqual(permission_result["secondary_diagnostic"], "FORMAT_INVALID")

    def test_self_repair_scope_exception_positive_and_negatives(self):
        # Only the actual executing controller repository qualifies.
        controller_repo = REPO

        task_repair = {
            "id": "TASK-ROUTE-001-END-TO-END",
            "contract_revision": 2,
            "scope": {
                "writable": [
                    ".agents/skills/antigravity-delegate/scripts/adapters/antigravity_cli.py",
                    ".agents/skills/antigravity-delegate/scripts/delegate.py",
                    ".agents/skills/antigravity-delegate/scripts/task_data.py",
                    ".agents/skills/antigravity-delegate/templates/task/receipt.executor.yaml",
                    ".agents/skills/antigravity-delegate/templates/task/receipt.qa.yaml",
                    ".agents/skills/antigravity-delegate/references/receipt-protocol.md",
                    ".agents/skills/antigravity-delegate/references/workflow.md",
                ],
                "protected": [
                    ".ai/project/ARCHITECTURE.md",
                ],
            },
        }
        valid_pre_review = {
            "task_id": "TASK-ROUTE-001-END-TO-END",
            "contract_sha256": d.digest(task_repair),
            "result": "APPROVED",
            "approved_by": "gpt-5.6-sol",
            "evidence": "Observed route failure repair approved",
        }

        # 1. Positive case: approved task revision, controller repo, valid pre_review, 7 allowed paths
        files_allowed = list(d.ALLOWED_SELF_REPAIR_PATHS)
        violations = d.scope_violations(files_allowed, task_repair, root=controller_repo, pre_review=valid_pre_review)
        self.assertEqual(violations, [])

        # 2. Negative: wrong task ID (e.g. TASK-TEST)
        task_wrong_id = copy.deepcopy(task_repair)
        task_wrong_id["id"] = "TASK-TEST"
        wrong_pre = copy.deepcopy(valid_pre_review)
        wrong_pre["task_id"] = "TASK-TEST"
        wrong_pre["contract_sha256"] = d.digest(task_wrong_id)
        v_wrong_task = d.scope_violations(files_allowed, task_wrong_id, root=controller_repo, pre_review=wrong_pre)
        self.assertEqual(len(v_wrong_task), len(files_allowed))

        # 3. Negative: wrong contract revision (1 and 99)
        for bad_rev in (1, 99):
            task_wrong_rev = copy.deepcopy(task_repair)
            task_wrong_rev["contract_revision"] = bad_rev
            wrong_rev_pre = copy.deepcopy(valid_pre_review)
            wrong_rev_pre["contract_sha256"] = d.digest(task_wrong_rev)
            v_wrong_rev = d.scope_violations(files_allowed, task_wrong_rev, root=controller_repo, pre_review=wrong_rev_pre)
            self.assertEqual(len(v_wrong_rev), len(files_allowed))

        # 4. Negative: missing or unapproved pre_review
        v_no_pre = d.scope_violations(files_allowed, task_repair, root=controller_repo, pre_review=None)
        self.assertEqual(len(v_no_pre), len(files_allowed))

        bad_pre = copy.deepcopy(valid_pre_review)
        bad_pre["result"] = "REJECTED"
        v_bad_pre = d.scope_violations(files_allowed, task_repair, root=controller_repo, pre_review=bad_pre)
        self.assertEqual(len(v_bad_pre), len(files_allowed))

        # 5. Negative: wrong repository
        wrong_repo = Path(self.temp.name) / "unrelated-repo"
        v_wrong_repo = d.scope_violations(files_allowed, task_repair, root=wrong_repo, pre_review=valid_pre_review)
        self.assertEqual(len(v_wrong_repo), len(files_allowed))

        # 5b. Negative: directory-name substring repo
        sub_repo = Path(self.temp.name) / "fake-gpt-antigravity-control-ascii"
        v_sub_repo = d.scope_violations(files_allowed, task_repair, root=sub_repo, pre_review=valid_pre_review)
        self.assertEqual(len(v_sub_repo), len(files_allowed))

        # 6. Negative: extra path in .agents
        extra_file = ".agents/skills/antigravity-delegate/scripts/extra.py"
        v_extra = d.scope_violations([extra_file], task_repair, root=controller_repo, pre_review=valid_pre_review)
        self.assertIn(extra_file, v_extra)

        # 7. Negative: explicit protected pattern always wins
        task_explicit = copy.deepcopy(task_repair)
        task_explicit["scope"]["protected"].append(".agents/skills/antigravity-delegate/scripts/delegate.py")
        v_explicit = d.scope_violations([".agents/skills/antigravity-delegate/scripts/delegate.py"], task_explicit, root=controller_repo, pre_review=valid_pre_review)
        self.assertIn(".agents/skills/antigravity-delegate/scripts/delegate.py", v_explicit)

        # 8. Negative: fixed protected .ai/**, AGENTS.md, GEMINI.md always win
        for fixed in [".ai/project/ARCHITECTURE.md", "AGENTS.md", "GEMINI.md"]:
            v_fixed = d.scope_violations([fixed], task_repair, root=controller_repo, pre_review=valid_pre_review)
            self.assertIn(fixed, v_fixed)


    def test_controller_identity_actual_repository_and_own_worktree(self):
        self.assertTrue(d.is_controller_repo(REPO))
        common = Path(d.git(REPO, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        self.assertTrue(d.is_controller_repo(common.parent))
        self.assertFalse(d.is_controller_repo(REPO / "tests"))

    def test_controller_identity_same_name_non_git_or_missing(self):
        fake = self.root / "gpt-antigravity-control-ascii"
        self.assertFalse(d.is_controller_repo(fake))
        fake.mkdir()
        self.assertFalse(d.is_controller_repo(fake))
        self.assertFalse(d.is_controller_repo(None))

    def test_controller_identity_same_name_fake_git_repository(self):
        fake = self.root / "gpt-antigravity-control-ascii"
        fake.mkdir()
        d.git(fake, "init", "-b", "main")
        self.assertFalse(d.is_controller_repo(fake))

    def test_controller_identity_foreign_common_dir_with_trusted_history(self):
        foreign = self.root / "gpt-antigravity-control-ascii"
        d.git(self.root, "clone", "--shared", "--no-checkout", str(REPO), str(foreign))
        d.git(foreign, "merge-base", "--is-ancestor", d.CONTROLLER_COMMIT_ANCHOR, "HEAD")
        self.assertFalse(d.is_controller_repo(foreign))

    def test_controller_identity_missing_anchor_and_git_error_fail_closed(self):
        with patch.object(d, "CONTROLLER_COMMIT_ANCHOR", "0" * 40):
            self.assertFalse(d.is_controller_repo(REPO))
        with patch.object(d, "git", side_effect=OSError("git unavailable")):
            self.assertFalse(d.is_controller_repo(REPO))


if __name__ == "__main__":
    unittest.main()
