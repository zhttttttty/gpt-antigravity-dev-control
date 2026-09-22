#!/usr/bin/env python3
"""Local single-task delegation (compatibility entry point)."""
from __future__ import annotations

import argparse
import contextlib
import fnmatch
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import yaml
import ai
from task_data import read_yaml, digest, task_id, require_approval, evidence_counts, write_yaml, validate_unverified_items

sys.path.insert(0, str(Path(__file__).resolve().parent / "adapters"))
from antigravity_cli import AntigravityCLI, diagnose
from executor_interface import Executor


def template_dir(root):
    local = root / ".ai/templates/task"
    bundled = Path(__file__).resolve().parents[1] / "templates/task"
    return local if local.exists() else bundled


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(value)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def save(path, value):
    atomic(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, check=True,
                          capture_output=True, text=True, encoding="utf-8").stdout.strip()


def transition(root, ident, target):
    # The core helper is chatty; preserve one JSON document on this CLI's stdout.
    with contextlib.redirect_stdout(io.StringIO()):
        return ai.transition(root, ident, target)


@contextlib.contextmanager
def lock(root):
    path = root / ".ai/runtime/delegation.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError("Delegation is locked; if interrupted, inspect running processes before removing the stale lock")
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        path.unlink()


def load_task(root, ident):
    task_id(ident)
    state, folder = ai.find_task(root, ident)
    if not ai.validate_task(root, ident, quiet=True):
        raise ValueError("Invalid task contract; run control.py validate")
    return state, folder, read_yaml(folder / "task.yaml")


def route(task):
    execution = task.get("execution", {})
    if not isinstance(execution, dict):
        raise ValueError("execution must be a mapping")
    mode = execution.get("mode", "direct")
    if mode not in {"direct", "delegated", "approval_required"}:
        raise ValueError("Invalid execution.mode")
    gated = task["planning"]["risk"] == "high" or any(task.get("authority", {}).values())
    if gated:
        mode = "approval_required"
    return {"mode": mode, "reason": "risk/architecture gate" if gated else "planner selection (legacy defaults to direct)"}


def _reuse_terminal_worktree(root, ident, task, previous_record, previous_run_dir,
                             previous_run_number, planning_base, next_branch,
                             previous_process_exited):
    """Validate and retarget one terminal worktree without moving its candidate."""
    if task["isolation"].get("reuse_terminal_worktree") is not True:
        raise ValueError("Reuse requires isolation.reuse_terminal_worktree: true")
    if previous_process_exited is not True:
        raise ValueError("Reuse requires explicit confirmation that the previous process tree exited")
    if previous_record.get("phase") not in {"LAUNCH_FAILED", "NEEDS_ATTENTION"}:
        raise ValueError("Reuse requires a terminal unsuccessful previous run")
    if previous_record.get("task_id") != ident or previous_record.get("attempt") != previous_run_number:
        raise ValueError("Previous run identity mismatch")
    recorded_run_dir = Path(previous_record.get("run_dir", ""))
    if recorded_run_dir.resolve() != previous_run_dir.resolve():
        raise ValueError("Previous run directory identity mismatch")
    old_hash = previous_record.get("contract_sha256")
    if not isinstance(old_hash, str) or len(old_hash) != 64:
        raise ValueError("Previous contract identity is missing or malformed")
    worktree = Path(previous_record.get("worktree", ""))
    if not worktree.is_dir():
        raise ValueError("Previous worktree is missing; refuse candidate reconstruction")
    actual_top = Path(git(worktree, "rev-parse", "--show-toplevel")).resolve()
    if actual_top != worktree.resolve():
        raise ValueError("Previous worktree identity mismatch")
    managed_root = (root / ".worktrees").resolve()
    try:
        common_path = Path(os.path.commonpath([str(actual_top), str(managed_root)]))
    except ValueError as exc:
        raise ValueError("Previous worktree is outside the managed worktree root") from exc
    if common_path != managed_root:
        raise ValueError("Previous worktree is outside the managed worktree root")
    root_common = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    worktree_common = Path(git(worktree, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    if root_common != worktree_common:
        raise ValueError("Previous worktree belongs to a different Git common directory")
    registered = {
        Path(line.removeprefix("worktree ")).resolve()
        for line in git(root, "worktree", "list", "--porcelain").splitlines()
        if line.startswith("worktree ")
    }
    if actual_top not in registered:
        raise ValueError("Previous worktree is not registered with the controller repository")
    old_branch = previous_record.get("branch")
    if git(worktree, "branch", "--show-current") != old_branch:
        raise ValueError("Previous worktree branch changed")
    base = previous_record.get("base_commit")
    if git(worktree, "rev-parse", "HEAD") != base:
        raise ValueError("Reuse requires HEAD to remain at the previous immutable base")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base, planning_base],
        cwd=root, check=False, capture_output=True,
    ).returncode == 0
    if not ancestor:
        raise ValueError("Previous candidate base is not an ancestor of the current planning base")

    raw = git(worktree, "status", "--porcelain=v1", "--untracked-files=all", "-z")
    entries = [entry for entry in raw.split("\0") if entry]
    if any(not entry.startswith("?? ") for entry in entries):
        raise ValueError("Reuse forbids tracked, staged, deleted, or renamed candidate changes")
    actual = sorted(entry[3:].replace("\\", "/") for entry in entries)
    expected = sorted(task["scope"].get("writable", []))
    if not expected or any(any(c in path for c in "*?[") for path in expected):
        raise ValueError("Reuse requires an exact, non-glob writable manifest")
    if actual != expected:
        raise ValueError(f"Reuse candidate manifest mismatch: expected {expected!r}, got {actual!r}")
    branch_exists = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{next_branch}"],
        cwd=root, check=False, capture_output=True,
    ).returncode == 0
    if branch_exists:
        raise ValueError("Reuse target branch already exists")
    return worktree, old_branch, base, actual


def prepare(root, ident, approved=False, approval=None, reuse_terminal_worktree=False,
            previous_process_exited=False):
    state, folder, task = load_task(root, ident)
    if state != "READY":
        raise ValueError("prepare requires READY")
    for dependency in task["planning"].get("depends_on", []):
        dep_state, _, _ = load_task(root, dependency)
        if dep_state not in {"DONE", "ARCHIVED"}:
            raise ValueError(f"Dependency not completed: {dependency}")
    routing = route(task)
    if routing["mode"] == "direct":
        raise ValueError("Direct task: Codex should execute without delegation")
    if not approved:
        raise ValueError("Human confirmation required: --approve")
    execution = task["execution"]
    if execution.get("adapter") != "antigravity_cli":
        raise ValueError("Unsupported adapter")
    if execution.get("model", "configured_default") != "configured_default":
        raise ValueError("Model selection must remain configured_default until CLI support is verified")
    if execution.get("context_budget", "compact") != "compact" or execution.get("report_level", "summary") != "summary":
        raise ValueError("Phase one supports compact context and summary reports only")
    attempts = execution.get("max_execution_attempts", 2)
    if type(attempts) is not int or not 1 <= attempts <= 10:
        raise ValueError("max_execution_attempts must be 1..10")
    contract_hash = digest(task)
    approval_data = None
    if routing["mode"] == "approval_required":
        approval_data = require_approval(task, ident, approval)
    if git(root, "status", "--porcelain"):
        raise ValueError("Commit or stash workspace changes, including task contract, before prepare")
    if task["isolation"].get("worktree") is not True:
        raise ValueError("Local delegation requires isolation.worktree: true")
    contract_reuse = task["isolation"].get("reuse_terminal_worktree") is True
    if contract_reuse != reuse_terminal_worktree:
        raise ValueError(
            "Terminal worktree reuse requires both isolation.reuse_terminal_worktree: true "
            "and --reuse-terminal-worktree"
        )
    base_ref = task["isolation"].get("base_branch", "HEAD")
    planning_base = git(root, "rev-parse", "--verify", f"{base_ref}^{{commit}}")
    if planning_base != git(root, "rev-parse", "HEAD"):
        raise ValueError("Configured base must equal current HEAD containing the committed task; no silent fallback")
    logs = root / ".ai/runtime/logs" / ident
    previous = sorted(
        logs.glob("run-*"), key=lambda path: int(path.name.split("-")[-1])
    ) if logs.exists() else []
    if len(previous) >= attempts:
        raise ValueError("Attempt budget exhausted; escalate to Codex review")
    number = len(previous) + 1
    run_dir = logs / f"run-{number}"
    worktree = root / ".worktrees" / f"{ident}-{number}"
    branch = f"ai/local/{ident}-{number}"
    base = planning_base
    reuse = None
    if reuse_terminal_worktree:
        if not previous:
            raise ValueError("Reuse requires a previous run")
        previous_record = json.loads((previous[-1] / "run.json").read_text(encoding="utf-8"))
        worktree, old_branch, base, candidate_files = _reuse_terminal_worktree(
            root, ident, task, previous_record, previous[-1], number - 1,
            planning_base, branch, previous_process_exited
        )
        reuse = {
            "from_run": int(previous[-1].name.split("-")[-1]),
            "old_branch": old_branch,
            "candidate_files": candidate_files,
            "previous_process_exit_confirmed": True,
        }
    chunks = []
    for name in ("task.yaml", "brief.md", "context.md", "rollback.md"):
        path = folder / name
        if path.stat().st_size > 32_000:
            raise ValueError(f"Context file too large: {name}; planner must reduce it")
        chunks.append(f"\n## {name}\n{path.read_text(encoding='utf-8')}")
    pack = ("Implement this one contract in this worktree. Do not alter task/control files, merge, or self-approve. "
            "Read relevant GEMINI.md and .ai/rules as needed. Run required checks; record actual evidence. "
            "Commit implementation changes only. Write the executor receipt to .ai/runtime/delegation/receipt.executor.yaml. "
            "A CLI launch is not task completion. Stop on architecture decisions.\n" + "".join(chunks))
    if len(pack.encode("utf-8")) > 32_000:
        raise ValueError("Compact context exceeds 32KB; split/reduce task without truncating its contract")
    run_dir.mkdir(parents=True)
    record = {"task_id": ident, "attempt": number, "contract_revision": task["contract_revision"],
              "task_attempt": task["attempt"], "contract_sha256": contract_hash,
              "base_commit": base, "branch": branch, "worktree": str(worktree),
              "run_dir": str(run_dir), "created_at": time.time(), "phase": "PREPARING",
              "pre_review": approval_data}
    if reuse:
        record["reused_terminal_worktree"] = reuse
    save(run_dir / "run.json", record)
    renamed = False
    try:
        if reuse:
            checked_worktree, _, checked_base, checked_files = _reuse_terminal_worktree(
                root, ident, task, previous_record, previous[-1], number - 1,
                planning_base, branch, previous_process_exited
            )
            if (checked_worktree != worktree or checked_base != base
                    or checked_files != candidate_files):
                raise ValueError("Reuse candidate changed during final pre-rename validation")
            git(worktree, "branch", "-m", branch)
            renamed = True
        else:
            worktree.parent.mkdir(exist_ok=True)
            git(root, "worktree", "add", "-b", branch, str(worktree), base)
        runtime = worktree / ".ai/runtime/delegation"
        runtime.mkdir(parents=True, exist_ok=True)
        atomic(runtime / "context.md", pack)
        template = read_yaml(template_dir(root) / "receipt.executor.yaml")
        template.update(task_id=ident, attempt=task["attempt"], contract_revision=task["contract_revision"])
        write_yaml(runtime / "receipt.executor.yaml", template)
        write_yaml(run_dir / "contract.yaml", task)
        atomic(run_dir / "context.md", pack)
        transition(root, ident, "IN_PROGRESS")
        record["phase"] = "PREPARED"
    except BaseException as exc:
        record.update(phase="BLOCKED", error=str(exc))
        if renamed:
            try:
                git(worktree, "branch", "-m", reuse["old_branch"])
                record["branch"] = reuse["old_branch"]
                record["reused_terminal_worktree"]["rolled_back"] = True
            except (OSError, subprocess.SubprocessError):
                record["branch_rollback_error"] = "manual inspection required"
        raise
    finally:
        save(run_dir / "run.json", record)
    return record


def latest(root, ident):
    task_id(ident)
    files = list((root / ".ai/runtime/logs" / ident).glob("run-*/run.json"))
    if not files:
        raise ValueError("No local run found")
    path = max(files, key=lambda p: int(p.parent.name.split("-")[-1]))
    return path, json.loads(path.read_text(encoding="utf-8"))


def launch(root, ident, adapter: Executor, approved=False, recover=False):
    if not approved:
        raise ValueError("Launch confirmation required: --approve")
    path, record = latest(root, ident)
    if recover:
        if not getattr(adapter, "interactive", False):
            raise ValueError("Recovery requires --interactive; no automatic print retry")
        if record["phase"] not in {"NEEDS_ATTENTION", "LAUNCH_FAILED"}:
            raise ValueError("Recovery requires a stopped, unsuccessful launch")
        if len(record.get("launch_history", [record.get("launch")])) >= 2:
            raise ValueError("Interactive recovery budget exhausted; escalate to review")
    elif record["phase"] != "PREPARED":
        raise ValueError("Launch only once per prepared run; inspect logs instead of duplicate dispatch")
    state, _, task = load_task(root, ident)
    if state != "IN_PROGRESS" or digest(task) != record["contract_sha256"]:
        raise ValueError("Task state/contract changed")
    worktree = Path(record["worktree"])
    if git(worktree, "branch", "--show-current") != record["branch"]:
        raise ValueError("Worktree branch changed")
    adapter.validate_launch()
    history = record.setdefault("launch_history", [])
    if not history and record.get("launch"):
        history.append(record["launch"])
    launch_dir = path.parent / f"launch-{len(history) + 1}"
    launch_dir.mkdir(exist_ok=False)
    record["phase"] = "LAUNCHING"
    save(path, record)
    try:
        result = adapter.launch(worktree, worktree / ".ai/runtime/delegation/context.md",
                                worktree / ".ai/runtime/delegation/receipt.executor.yaml", launch_dir)
        phase = "LAUNCH_FAILED" if result["exit_code"] != 0 else (
            "AWAITING_RECEIPT" if result.get("diagnostic") == "RECEIPT_PRESENT_UNVERIFIED" else "NEEDS_ATTENTION")
        history.append(result)
        record.update(launch=result, phase=phase)
    except BaseException as exc:
        record.update(phase="LAUNCH_FAILED", error=str(exc))
        failure = {"exit_code": None, "error": str(exc), "completion": "UNKNOWN", "log": str(launch_dir / "launch.log")}
        record["launch"] = failure
        history.append(failure)
        raise
    finally:
        save(path, record)
    return record


ALLOWED_SELF_REPAIR_TASKS = {
    ("TASK-ROUTE-001-END-TO-END", 2),
}

ALLOWED_SELF_REPAIR_PATHS = {
    ".agents/skills/antigravity-delegate/scripts/adapters/antigravity_cli.py",
    ".agents/skills/antigravity-delegate/scripts/delegate.py",
    ".agents/skills/antigravity-delegate/scripts/task_data.py",
    ".agents/skills/antigravity-delegate/templates/task/receipt.executor.yaml",
    ".agents/skills/antigravity-delegate/templates/task/receipt.qa.yaml",
    ".agents/skills/antigravity-delegate/references/receipt-protocol.md",
    ".agents/skills/antigravity-delegate/references/workflow.md",
}


CONTROLLER_COMMIT_ANCHOR = "e55f40f82168dcf2c0aeb2b927a5783473f78d0e"


def is_controller_repo(root):
    """Identify this controller's Git repository, never a directory-name lookalike."""
    if root is None:
        return False
    try:
        target = Path(root).resolve(strict=True)
        if not target.is_dir():
            return False
        top = Path(git(target, "rev-parse", "--show-toplevel")).resolve(strict=True)
        if target != top:
            return False
        source = Path(__file__).resolve(strict=True).parent
        source_common = Path(git(source, "rev-parse", "--path-format=absolute",
                                 "--git-common-dir")).resolve(strict=True)
        target_common = Path(git(target, "rev-parse", "--path-format=absolute",
                                 "--git-common-dir")).resolve(strict=True)
        if source_common != target_common:
            return False
        git(target, "merge-base", "--is-ancestor", CONTROLLER_COMMIT_ANCHOR, "HEAD")
        return True
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError):
        return False


def is_valid_pre_review(task, pre_review):
    if not isinstance(pre_review, dict):
        return False
    return (
        pre_review.get("task_id") == task.get("id")
        and pre_review.get("contract_sha256") == digest(task)
        and pre_review.get("result") == "APPROVED"
        and bool(pre_review.get("approved_by"))
        and bool(pre_review.get("evidence"))
    )


def scope_violations(files, task, root=None, pre_review=None):
    writable = task["scope"].get("writable", [])
    explicit_protected = task["scope"].get("protected", [])
    fixed_protected = [".ai/**", "AGENTS.md", "GEMINI.md"]

    task_tuple = (task.get("id"), task.get("contract_revision"))
    self_repair_ok = (
        task_tuple in ALLOWED_SELF_REPAIR_TASKS
        and is_controller_repo(root)
        and is_valid_pre_review(task, pre_review)
    )

    violations = []
    for p_raw in files:
        p = p_raw.replace("\\", "/")
        if any(fnmatch.fnmatchcase(p, pat) for pat in explicit_protected):
            violations.append(p_raw)
            continue
        if any(fnmatch.fnmatchcase(p, pat) for pat in fixed_protected):
            violations.append(p_raw)
            continue
        if fnmatch.fnmatchcase(p, ".agents/**"):
            if self_repair_ok and p in ALLOWED_SELF_REPAIR_PATHS:
                pass
            else:
                violations.append(p_raw)
                continue
        if not any(fnmatch.fnmatchcase(p, pat) for pat in writable):
            violations.append(p_raw)
            continue
    return violations


def collect(root, ident):
    path, record = latest(root, ident)
    if record["phase"] == "COLLECTED":
        return json.loads((path.parent / "receipt.compact.json").read_text(encoding="utf-8"))
    if record["phase"] not in {"PREPARED", "AWAITING_RECEIPT", "LAUNCH_FAILED", "NEEDS_ATTENTION"}:
        raise ValueError("Run is not ready for collection; inspect run.json")
    state, folder, task = load_task(root, ident)
    if state != "IN_PROGRESS" or digest(task) != record["contract_sha256"]:
        raise ValueError("Task state/contract changed; review before collecting")
    worktree = Path(record["worktree"])
    if git(worktree, "rev-parse", "--show-toplevel").replace("\\", "/") != worktree.as_posix():
        raise ValueError("Worktree identity mismatch")
    if git(worktree, "branch", "--show-current") != record["branch"]:
        raise ValueError("Worktree branch changed")
    if git(worktree, "status", "--porcelain"):
        raise ValueError("Executor must commit changes before collect; untracked/dirty files remain")
    git(worktree, "merge-base", "--is-ancestor", record["base_commit"], "HEAD")
    head = git(worktree, "rev-parse", "HEAD")
    names = subprocess.run(["git", "diff", "--no-renames", "--name-only", "-z", record["base_commit"], head],
                           cwd=worktree, check=True, capture_output=True).stdout.decode("utf-8")
    files = sorted(filter(None, names.split("\0")))
    violations = scope_violations(files, task, root=root, pre_review=record.get("pre_review"))
    receipt_path = worktree / ".ai/runtime/delegation/receipt.executor.yaml"
    receipt = read_yaml(receipt_path)
    if any(receipt.get(k) != v for k, v in {"task_id": ident, "attempt": task["attempt"],
                                           "contract_revision": task["contract_revision"], "schema_version": 2}.items()):
        raise ValueError("Receipt identity/revision mismatch")
    if receipt.get("status") not in {"COMPLETE", "BLOCKED", "FAILED"}:
        raise ValueError(f"Receipt is not complete; status must be COMPLETE, BLOCKED, or FAILED, got {receipt.get('status')!r}")

    ws = receipt.get("workspace")
    if not isinstance(ws, dict):
        raise ValueError("Malformed workspace: expected mapping")
    for field in ("path", "branch", "base_commit", "head_commit"):
        val = ws.get(field)
        if not isinstance(val, str) or not val.strip():
            raise ValueError(f"Malformed workspace: {field} must be a nonempty string")
    claimed_p = os.path.normcase(os.path.abspath(str(ws["path"])))
    actual_p = os.path.normcase(os.path.abspath(str(worktree)))
    if claimed_p != actual_p:
        raise ValueError(f"Workspace path mismatch: claimed {ws['path']!r} != actual {str(worktree)!r}")
    if ws["branch"] != record["branch"]:
        raise ValueError(f"Workspace branch mismatch: claimed {ws['branch']!r} != actual {record['branch']!r}")
    if ws["base_commit"] != record["base_commit"]:
        raise ValueError(f"Workspace base commit mismatch: claimed {ws['base_commit']!r} != actual {record['base_commit']!r}")
    if ws["head_commit"] != head:
        raise ValueError(f"Workspace head commit mismatch: claimed {ws['head_commit']!r} != actual {head!r}")

    passed, required_count, ac_passed, acceptance_count = evidence_counts(task, receipt)
    issues = []
    if violations:
        issues.append("Out-of-scope changes; inspect local full evidence")
    if passed != required_count or ac_passed != acceptance_count:
        issues.append("Required evidence missing or failed")
    unverified_errors = validate_unverified_items(task, receipt.get("unverified_items") or [])
    if unverified_errors:
        issues.extend(unverified_errors)
    if (receipt.get("architecture_deviation") or {}).get("result") != "NONE":
        issues.append("Architecture deviation needs review")
    target = "REVIEW" if receipt["status"] == "COMPLETE" and not issues else "BLOCKED"

    executor_known_issues = receipt.get("known_issues") or []
    if not isinstance(executor_known_issues, list):
        executor_known_issues = [executor_known_issues]

    summary_known_issues = []
    for item in executor_known_issues:
        if isinstance(item, str):
            summary_known_issues.append({"issue": item, "text": item, "marker": "REPORTED", "result": "REPORTED"})
        elif isinstance(item, dict):
            d = dict(item)
            text = d.get("issue") or d.get("text") or d.get("description") or str(d)
            marker = d.get("marker") or d.get("status") or d.get("result") or "REPORTED"
            d["issue"] = text
            d["text"] = text
            d["marker"] = marker
            d["result"] = marker
            summary_known_issues.append(d)
        else:
            summary_known_issues.append({"issue": str(item), "text": str(item), "marker": "REPORTED", "result": "REPORTED"})

    issue_marker = "REPORTED" if executor_known_issues else "NONE"
    if issues:
        issue_marker = "BLOCKING"

    summary = {"task_id": ident, "status": "COMPLETE" if target == "REVIEW" else "BLOCKED",
               "task_state": target, "base_commit": record["base_commit"], "head_commit": head,
               "changed_files": len(files), "changed_files_preview": files[:20],
               "scope_check": "FAIL" if violations else "PASS",
               "known_issues": issues if issues else summary_known_issues,
               "issue_marker": issue_marker,
               "checks": {"reported_passed": passed, "required": required_count},
               "acceptance": {"reported_passed": ac_passed, "total": acceptance_count},
               "evidence_trust": "executor_reported; independent review pending",
               "review_verdict": "PENDING", "elapsed_seconds": round(time.time() - record["created_at"], 2),
               "usage": {"codex_tokens": None, "antigravity_tokens": None},
               "logs": {"directory": str(path.parent), "diff": str(path.parent / "changes.diff")}}
    with (path.parent / "changes.diff").open("wb") as stream:
        subprocess.run(["git", "diff", "--binary", record["base_commit"], head], cwd=worktree, stdout=stream, check=True)
    save(path.parent / "changed-files.json", {"files": files, "violations": violations})
    atomic(path.parent / "receipt.executor.yaml", receipt_path.read_text(encoding="utf-8"))
    # Git observations replace executor claims; no invented test totals or PASS verdict.
    receipt["workspace"] = {"path": str(worktree), "branch": record["branch"], "base_commit": record["base_commit"], "head_commit": head}
    receipt["changed_files"] = files
    receipt["scope_check"] = {"result": summary["scope_check"], "out_of_scope_files": violations}
    write_yaml(folder / "receipt.executor.yaml", receipt)
    save(path.parent / "receipt.compact.json", summary)
    transition(root, ident, target)
    record.update(phase="COLLECTED", head_commit=head)
    save(path, record)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("probe")
    p.add_argument("--executable", default="agy")
    for command in ("route", "prepare", "launch", "collect", "status", "diagnose"):
        p = sub.add_parser(command)
        p.add_argument("task_id")
        if command in {"prepare", "launch"}:
            p.add_argument("--approve", action="store_true")
        if command == "prepare":
            p.add_argument("--approval-file")
            p.add_argument("--reuse-terminal-worktree", action="store_true",
                           help="Reuse the immediately previous terminal worktree after exact-manifest validation")
            p.add_argument("--confirm-previous-process-exited", action="store_true",
                           help="Record operator confirmation that the previous executor process tree exited")
        if command == "launch":
            p.add_argument("--executable", default="agy")
            p.add_argument("--args-file", type=Path)
            p.add_argument("--timeout", type=int, default=1260)
            p.add_argument("--interactive", action="store_true", help="Inherit a real terminal for scoped approvals (recommended)")
            p.add_argument("--recover", action="store_true", help="One explicitly confirmed interactive recovery after a stopped launch")
            p.add_argument("--full-access", action="store_true", help="Pass agy --dangerously-skip-permissions; requires --approve")
            p.add_argument("--mode", choices=("accept-edits", "plan"), default="accept-edits",
                           help="agy mode; direct/delegated are controller routes, not agy modes")
    args = parser.parse_args()
    try:
        root = Path(git(args.repo.resolve(), "rev-parse", "--show-toplevel")).resolve()
        # Atomic run records can be observed while an interactive launch holds
        # the mutation lock; status/diagnostics must not block behind the TUI.
        guard = contextlib.nullcontext() if args.command in {"route", "status", "diagnose"} else lock(root)
        with guard:
            if args.command == "probe":
                result = AntigravityCLI(args.executable).probe(root / ".ai/runtime/logs/probe")
            elif args.command == "route":
                _, _, task = load_task(root, args.task_id)
                result = {**route(task), "contract_sha256": digest(task)}
            elif args.command == "prepare":
                result = prepare(root, args.task_id, args.approve, args.approval_file,
                                 args.reuse_terminal_worktree,
                                 args.confirm_previous_process_exited)
            elif args.command == "launch":
                if args.full_access and not args.approve:
                    raise ValueError("--full-access requires explicit --approve")
                argv = json.loads(args.args_file.read_text(encoding="utf-8")) if args.args_file else None
                result = launch(root, args.task_id, AntigravityCLI(args.executable, argv, args.timeout, args.interactive, args.full_access, args.mode), args.approve, args.recover)
            elif args.command == "collect":
                result = collect(root, args.task_id)
            elif args.command == "diagnose":
                _, record = latest(root, args.task_id)
                last_launch = record.get("launch", {})
                logs = [Path(last_launch[k]) for k in ("log", "cli_log") if last_launch.get(k)]
                result = {"task_id": args.task_id, "phase": record["phase"],
                          "diagnostic": diagnose(Path(record["worktree"]) / ".ai/runtime/delegation/receipt.executor.yaml", logs),
                          "next_step": "Collect completed evidence, or inspect local logs and use confirmed interactive recovery; never infer success from exit 0"}
            else:
                if ai.task_locations(root, args.task_id):
                    state, folder, task = load_task(root, args.task_id)
                    result = {"task_id": args.task_id, "task_state": state,
                              "task_folder": str(folder), "execution": task.get("execution", {})}
                    if list((root / ".ai/runtime/logs" / args.task_id).glob("run-*/run.json")):
                        _, record = latest(root, args.task_id)
                        result.update(record, task_state=state)
                else:
                    _, result = latest(root, args.task_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if result.get("available") is False or result.get("phase") in {"LAUNCH_FAILED", "NEEDS_ATTENTION"} or result.get("status") == "BLOCKED" else 0
    except (ValueError, OSError, subprocess.SubprocessError, yaml.YAMLError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
