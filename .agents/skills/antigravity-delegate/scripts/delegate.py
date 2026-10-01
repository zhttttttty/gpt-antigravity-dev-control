#!/usr/bin/env python3
"""Local single-task delegation (compatibility entry point)."""
from __future__ import annotations

import argparse
import contextlib
import fnmatch
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
import time

import yaml
import ai
from task_data import (CHECK_STAGES, digest, evidence_counts,
                       implementation_attempt_limit, read_yaml,
                       required_check_items, require_approval, task_id,
                       validate_unverified_items, write_yaml)

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
    selected = execution.get("mode", "direct")
    if selected not in {"direct", "delegated", "approval_required"}:
        raise ValueError("Invalid execution.mode")
    gated = task["planning"]["risk"] == "high" or any(task.get("authority", {}).values())
    planning = task.get("planning", {})
    adaptive_fields_present = any(key in planning for key in (
        "work_type", "judgment", "context_continuity", "acceptance_determinism"
    ))
    high_judgment = adaptive_fields_present and (
        planning.get("work_type") in {"semantic", "security", "architecture"}
        or planning.get("judgment") == "high"
        or planning.get("context_continuity") == "high"
        or planning.get("acceptance_determinism") == "low"
    )
    override = execution.get("routing_override") or {}
    overridden = override.get("result") == "APPROVED"
    if high_judgment:
        backend = "antigravity" if overridden else "direct"
        mode = "approval_required" if overridden or gated else "direct"
        reason = ("approved adaptive override requires independent approval"
                  if overridden else
                  "high-judgment or continuity-sensitive work defaults to direct")
    elif selected == "direct":
        backend = "direct"
        mode = "approval_required" if gated else "direct"
        reason = "planner selected direct"
    else:
        backend = "antigravity"
        mode = "approval_required" if gated else selected
        reason = "approved adaptive override" if high_judgment else (
            "risk/architecture gate" if gated else "bounded deterministic delegation"
        )
    return {
        "mode": mode,
        "backend": backend,
        "selected_mode": selected,
        "high_judgment": high_judgment,
        "override_applied": overridden and high_judgment,
        "reason": reason,
    }


def _reuse_terminal_worktree(root, ident, task, previous_record, previous_run_dir,
                             previous_run_number, planning_base, next_branch,
                             previous_process_exited, allow_tracked=False):
    """Validate and retarget one terminal worktree without moving its candidate."""
    contract_flag = "reuse_tracked_worktree" if allow_tracked else "reuse_terminal_worktree"
    if task["isolation"].get(contract_flag) is not True:
        raise ValueError(f"Reuse requires isolation.{contract_flag}: true")
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
    candidate_hash = None
    if allow_tracked:
        status_codes = [entry[:2] for entry in entries]
        if any(code == "??" or any(flag in code for flag in "DRCU")
               or any(flag not in " MA" for flag in code)
               for code in status_codes):
            raise ValueError(
                "Tracked reuse only permits already-tracked scoped added/modified candidate files"
            )
        actual = sorted(entry[2:].lstrip().replace("\\", "/") for entry in entries)
        candidate_diff = subprocess.run(
            ["git", "diff", "--binary", "HEAD"], cwd=worktree, check=True,
            capture_output=True,
        ).stdout
        candidate_hash = hashlib.sha256(candidate_diff).hexdigest()
    else:
        if any(not entry.startswith("?? ") for entry in entries):
            raise ValueError("Reuse forbids tracked, staged, deleted, or renamed candidate changes")
        actual = sorted(entry[2:].lstrip().replace("\\", "/") for entry in entries)
    expected = sorted(task["scope"].get("writable", []))
    if not expected or any(any(c in path for c in "*?[") for path in expected):
        raise ValueError("Reuse requires an exact, non-glob writable manifest")
    if allow_tracked and (not actual or any(path not in expected for path in actual)):
        raise ValueError(f"Tracked reuse candidate exceeds exact writable manifest: {actual!r}")
    if not allow_tracked and actual != expected:
        raise ValueError(f"Reuse candidate manifest mismatch: expected {expected!r}, got {actual!r}")
    branch_exists = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{next_branch}"],
        cwd=root, check=False, capture_output=True,
    ).returncode == 0
    if branch_exists:
        raise ValueError("Reuse target branch already exists")
    return worktree, old_branch, base, actual, candidate_hash


def prepare(root, ident, approved=False, approval=None, reuse_terminal_worktree=False,
            reuse_tracked_worktree=False, previous_process_exited=False):
    state, folder, task = load_task(root, ident)
    if state != "READY":
        raise ValueError("prepare requires READY")
    for dependency in task["planning"].get("depends_on", []):
        dep_state, _, _ = load_task(root, dependency)
        if dep_state not in {"DONE", "ARCHIVED"}:
            raise ValueError(f"Dependency not completed: {dependency}")
    routing = route(task)
    if routing["backend"] != "antigravity":
        raise ValueError("Direct task: Codex should execute without delegation")
    if not approved:
        raise ValueError("Human confirmation required: --approve")
    execution = task["execution"]
    if execution.get("adapter") != "antigravity_cli":
        raise ValueError("Unsupported adapter")
    if execution.get("model", "configured_default") != "configured_default":
        raise ValueError("Model selection must remain configured_default until CLI support is verified")
    if execution.get("context_budget", "compact") not in {"compact", "incremental"} or execution.get("report_level", "summary") != "summary":
        raise ValueError("Supported context budgets are compact/incremental with summary reports")
    attempts = implementation_attempt_limit(execution)
    contract_hash = digest(task)
    approval_data = None
    if routing["mode"] == "approval_required" or reuse_tracked_worktree:
        approval_data = require_approval(task, ident, approval)
    if git(root, "status", "--porcelain"):
        raise ValueError("Commit or stash workspace changes, including task contract, before prepare")
    if task["isolation"].get("worktree") is not True:
        raise ValueError("Local delegation requires isolation.worktree: true")
    if reuse_terminal_worktree and reuse_tracked_worktree:
        raise ValueError("Choose untracked or tracked terminal worktree reuse, not both")
    contract_reuse = task["isolation"].get("reuse_terminal_worktree") is True
    contract_tracked_reuse = task["isolation"].get("reuse_tracked_worktree") is True
    if contract_reuse != reuse_terminal_worktree:
        raise ValueError(
            "Terminal worktree reuse requires both isolation.reuse_terminal_worktree: true "
            "and --reuse-terminal-worktree"
        )
    if contract_tracked_reuse != reuse_tracked_worktree:
        raise ValueError(
            "Tracked worktree reuse requires both isolation.reuse_tracked_worktree: true "
            "and --reuse-tracked-worktree"
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
    if reuse_terminal_worktree or reuse_tracked_worktree:
        if not previous:
            raise ValueError("Reuse requires a previous run")
        previous_record = json.loads((previous[-1] / "run.json").read_text(encoding="utf-8"))
        worktree, old_branch, base, candidate_files, candidate_hash = _reuse_terminal_worktree(
            root, ident, task, previous_record, previous[-1], number - 1,
            planning_base, branch, previous_process_exited,
            allow_tracked=reuse_tracked_worktree
        )
        reuse = {
            "from_run": int(previous[-1].name.split("-")[-1]),
            "old_branch": old_branch,
            "candidate_files": candidate_files,
            "candidate_kind": "tracked" if reuse_tracked_worktree else "untracked",
            "candidate_diff_sha256": candidate_hash,
            "previous_process_exit_confirmed": True,
        }
        if reuse_tracked_worktree:
            expected_binding = {
                "previous_contract_sha256": previous_record.get("contract_sha256"),
                "candidate_diff_sha256": candidate_hash,
                "contract_sha256": contract_hash,
            }
            if any(approval_data.get(key) != value for key, value in expected_binding.items()):
                raise ValueError(
                    "Tracked reuse approval must bind previous/current contracts and candidate diff"
                )
    incremental = execution.get("context_budget") == "incremental" and number > 1
    context_names = ("task.yaml", "brief.md", "rollback.md") if incremental else (
        "task.yaml", "brief.md", "context.md", "rollback.md"
    )
    chunks = []
    if incremental:
        previous_review = folder / "history" / f"attempt-{task['attempt'] - 1}" / "review.yaml"
        if previous_review.exists():
            if previous_review.stat().st_size > 12_000:
                raise ValueError("Previous review is too large for incremental context")
            chunks.append(
                "\n## rework-delta.yaml\n"
                "Previous candidate failed independent review. Address only these findings first; "
                "the current task.yaml remains authoritative.\n"
                + previous_review.read_text(encoding="utf-8")
            )
        else:
            # A missing structured review makes omission of context unsafe.
            context_names = ("task.yaml", "brief.md", "context.md", "rollback.md")
    for name in context_names:
        path = folder / name
        if path.stat().st_size > 32_000:
            raise ValueError(f"Context file too large: {name}; planner must reduce it")
        chunks.append(f"\n## {name}\n{path.read_text(encoding='utf-8')}")
    pack = ("Implement this one contract in this worktree. Do not alter task/control files, merge, or self-approve. "
            "Read relevant GEMINI.md and .ai/rules as needed. Run focused checks needed while coding, but the "
            "controller owns the authoritative contract check matrix. Commit implementation changes only. "
            "Set the executor receipt status to IMPLEMENTED and fill actual executor identity, acceptance evidence, "
            "architecture deviations, known issues, and unverified items. Do not invent command evidence; the "
            "controller verify phase fills it. A CLI launch is not task completion. Stop on architecture decisions.\n"
            + "".join(chunks))
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
            checked_worktree, _, checked_base, checked_files, checked_hash = _reuse_terminal_worktree(
                root, ident, task, previous_record, previous[-1], number - 1,
                planning_base, branch, previous_process_exited,
                allow_tracked=reuse_tracked_worktree
            )
            if (checked_worktree != worktree or checked_base != base
                    or checked_files != candidate_files or checked_hash != candidate_hash):
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
        _, _, recovery_task = load_task(root, ident)
        infra_retries = recovery_task.get("execution", {}).get("max_infra_retries", 1)
        if type(infra_retries) is not int or not 0 <= infra_retries <= 3:
            raise ValueError("max_infra_retries must be 0..3")
        if len(record.get("launch_history", [record.get("launch")])) >= infra_retries + 1:
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
        receipt_path = worktree / ".ai/runtime/delegation/receipt.executor.yaml"
        receipt_status = None
        if receipt_path.exists():
            try:
                receipt_status = read_yaml(receipt_path).get("status")
            except (OSError, ValueError, yaml.YAMLError):
                receipt_status = None
        phase = "LAUNCH_FAILED" if result["exit_code"] != 0 else (
            "AWAITING_VERIFICATION" if receipt_status == "IMPLEMENTED" else
            "AWAITING_RECEIPT" if result.get("diagnostic") == "RECEIPT_PRESENT_UNVERIFIED" else
            "NEEDS_ATTENTION"
        )
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


def _staged_checks(task):
    checks = task.get("checks") or {}
    out = []
    seen = set()
    for stage in (*CHECK_STAGES, "required"):
        for item in checks.get(stage, []) or []:
            command = item.get("command")
            if command not in seen:
                out.append((stage, item))
                seen.add(command)
    return out


def _utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _terminate_process_tree(process):
    """Best-effort bounded teardown for a timed-out verification command."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False, capture_output=True,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def verify(root, ident, approved=False, timeout=600, total_timeout=1800, approval=None):
    """Run the contract check matrix outside the model session and fill evidence."""
    if not approved:
        raise ValueError("Verification runs contract commands and requires --approve")
    if type(timeout) is not int or timeout <= 0:
        raise ValueError("Verification timeout must be a positive integer")
    if type(total_timeout) is not int or total_timeout <= 0:
        raise ValueError("Verification total timeout must be a positive integer")
    path, record = latest(root, ident)
    if record["phase"] not in {
        "AWAITING_VERIFICATION", "AWAITING_RECEIPT", "NEEDS_ATTENTION", "LAUNCH_FAILED"
    }:
        raise ValueError("Run is not awaiting deterministic verification")
    state, _, task = load_task(root, ident)
    if state != "IN_PROGRESS" or digest(task) != record["contract_sha256"]:
        raise ValueError("Task state/contract changed")
    worktree = Path(record["worktree"])
    if Path(git(worktree, "rev-parse", "--show-toplevel")).resolve() != worktree.resolve():
        raise ValueError("Verification worktree identity mismatch")
    managed_root = (root / ".worktrees").resolve()
    try:
        if Path(os.path.commonpath([str(worktree.resolve()), str(managed_root)])) != managed_root:
            raise ValueError("Verification worktree is outside the managed root")
    except ValueError as exc:
        raise ValueError("Verification worktree is outside the managed root") from exc
    root_common = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    worktree_common = Path(git(worktree, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()
    if root_common != worktree_common:
        raise ValueError("Verification worktree belongs to a different Git repository")
    if git(worktree, "branch", "--show-current") != record["branch"]:
        raise ValueError("Worktree branch changed")
    if git(worktree, "status", "--porcelain"):
        raise ValueError("Commit implementation changes before deterministic verification")
    git(worktree, "merge-base", "--is-ancestor", record["base_commit"], "HEAD")
    head = git(worktree, "rev-parse", "HEAD")
    raw_names = subprocess.run(
        ["git", "diff", "--no-renames", "--name-only", "-z", record["base_commit"], head],
        cwd=worktree, check=True, capture_output=True,
    ).stdout.decode("utf-8")
    changed = sorted(filter(None, raw_names.split("\0")))
    violations = scope_violations(changed, task, root=root, pre_review=record.get("pre_review"))

    receipt_path = worktree / ".ai/runtime/delegation/receipt.executor.yaml"
    receipt = read_yaml(receipt_path)
    expected = {
        "schema_version": 2,
        "task_id": ident,
        "attempt": task["attempt"],
        "contract_revision": task["contract_revision"],
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError("Receipt identity/revision mismatch before verification")
    if receipt.get("status") != "IMPLEMENTED":
        raise ValueError("Executor must set receipt status IMPLEMENTED before verification")
    if not receipt.get("executor"):
        raise ValueError("Executor identity is required before verification")

    staged = _staged_checks(task)
    require_approval(task, ident, approval)
    verify_dir = path.parent / "verify"
    verify_dir.mkdir(exist_ok=False)
    results = []
    failed = bool(violations)
    verify_started = time.monotonic()
    for index, (stage, item) in enumerate(staged, start=1):
        command = item["command"]
        log_path = verify_dir / f"{index:02d}-{stage}.log"
        if failed:
            result = {
                "command": command, "exit_code": None, "result": "NOT_RUN",
                "reason": "earlier verification gate failed", "log": str(log_path),
            }
            atomic(log_path, "NOT_RUN: earlier verification gate failed\n")
            results.append(result)
            continue
        command_timeout = item.get("timeout_seconds", timeout)
        if type(command_timeout) is not int or command_timeout <= 0:
            raise ValueError(f"Invalid timeout_seconds for check: {command}")
        remaining = total_timeout - (time.monotonic() - verify_started)
        if remaining <= 0:
            atomic(log_path, "TIMEOUT: total verification deadline exhausted\n")
            results.append({
                "command": command, "exit_code": 124, "result": "FAIL",
                "reason": "total verification deadline exhausted",
                "log": str(log_path), "stage": stage,
            })
            failed = True
            continue
        effective_timeout = min(command_timeout, remaining)
        use_shell = item.get("shell") is True
        argv = command if use_shell else shlex.split(command, posix=True)
        if not argv:
            raise ValueError("Verification command cannot be empty")
        popen_options = {"start_new_session": True} if os.name != "nt" else {
            "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP
        }
        try:
            with log_path.open("w", encoding="utf-8", errors="replace") as stream:
                process = subprocess.Popen(
                    argv, cwd=worktree, shell=use_shell, stdout=stream,
                    stderr=subprocess.STDOUT, text=True, **popen_options,
                )
                try:
                    exit_code = process.wait(timeout=effective_timeout)
                except subprocess.TimeoutExpired:
                    _terminate_process_tree(process)
                    stream.write("\nTIMEOUT\n")
                    exit_code = 124
        except subprocess.TimeoutExpired:
            exit_code = 124
        workspace_reason = None
        if git(worktree, "branch", "--show-current") != record["branch"]:
            workspace_reason = "verification command changed branch"
        elif git(worktree, "rev-parse", "HEAD") != head:
            workspace_reason = "verification command changed HEAD"
        elif git(worktree, "status", "--porcelain"):
            workspace_reason = "verification command dirtied worktree"
        if workspace_reason:
            exit_code = exit_code if exit_code != 0 else 125
        outcome = "PASS" if exit_code == 0 else "FAIL"
        result = {
            "command": command, "exit_code": exit_code, "result": outcome,
            "log": str(log_path), "stage": stage, "shell": use_shell,
        }
        if workspace_reason:
            result["reason"] = workspace_reason
        results.append(result)
        if outcome == "FAIL":
            failed = True

    receipt.update(
        status="FAILED" if failed else "COMPLETE",
        workspace={
            "path": str(worktree), "branch": record["branch"],
            "base_commit": record["base_commit"], "head_commit": head,
        },
        ended_at=_utc_now(), changed_files=changed, commands=results,
        scope_check={"result": "FAIL" if violations else "PASS", "out_of_scope_files": violations},
    )
    if not receipt.get("started_at"):
        receipt["started_at"] = _utc_now()
    write_yaml(receipt_path, receipt)
    record.update(
        phase="VERIFICATION_FAILED" if failed else "VERIFIED",
        verification={
            "status": "FAIL" if failed else "PASS", "commands": len(results),
            "violations": violations, "directory": str(verify_dir),
        },
    )
    save(path, record)
    return {
        "task_id": ident, "status": record["verification"]["status"],
        "phase": record["phase"], "commands": results,
        "changed_files": changed, "scope_violations": violations,
    }


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
    if record["phase"] not in {
        "PREPARED", "AWAITING_RECEIPT", "LAUNCH_FAILED", "NEEDS_ATTENTION",
        "VERIFIED", "VERIFICATION_FAILED"
    }:
        raise ValueError("Run is not ready for collection; inspect run.json")
    state, folder, task = load_task(root, ident)
    if state != "IN_PROGRESS" or digest(task) != record["contract_sha256"]:
        raise ValueError("Task state/contract changed; review before collecting")
    has_staged_checks = any(
        task.get("checks", {}).get(stage) for stage in CHECK_STAGES
    )
    if has_staged_checks and record["phase"] not in {"VERIFIED", "VERIFICATION_FAILED"}:
        raise ValueError("Staged-check contracts require controller verification before collection")
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
    if record["phase"] == "VERIFIED" and receipt.get("status") != "COMPLETE":
        raise ValueError("Verified run requires a COMPLETE controller-updated receipt")
    if record["phase"] == "VERIFICATION_FAILED" and receipt.get("status") != "FAILED":
        raise ValueError("Failed verification requires a FAILED controller-updated receipt")

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
    for command in ("route", "prepare", "launch", "verify", "collect", "status", "diagnose"):
        p = sub.add_parser(command)
        p.add_argument("task_id")
        if command in {"prepare", "launch"}:
            p.add_argument("--approve", action="store_true")
        if command == "prepare":
            p.add_argument("--approval-file")
            p.add_argument("--reuse-terminal-worktree", action="store_true",
                           help="Reuse the immediately previous terminal worktree after exact-manifest validation")
            p.add_argument("--reuse-tracked-worktree", action="store_true",
                           help="Explicitly reuse scoped tracked partial changes after terminal-process validation")
            p.add_argument("--confirm-previous-process-exited", action="store_true",
                           help="Record operator confirmation that the previous executor process tree exited")
        if command == "launch":
            p.add_argument("--executable", default="agy")
            p.add_argument("--args-file", type=Path)
            p.add_argument("--timeout", type=int, default=1260)
            p.add_argument("--interactive", action="store_true", help="Inherit a real terminal for scoped approvals (recommended)")
            p.add_argument("--recover", action="store_true", help="One explicitly confirmed interactive recovery after a stopped launch")
            p.add_argument(
                "--auto-approve", "--full-access", dest="auto_approve", action="store_true",
                help="Auto-approve agy tool calls with --dangerously-skip-permissions; requires --approve. "
                     "--full-access is a deprecated compatibility alias.",
            )
            p.add_argument("--mode", choices=("accept-edits", "plan"), default="accept-edits",
                           help="agy mode; direct/delegated are controller routes, not agy modes")
        if command == "verify":
            p.add_argument("--approve", action="store_true",
                           help="Approve execution of the exact contract check commands")
            p.add_argument("--approval-file", type=Path,
                           help="Contract-bound approval for the exact verification command matrix")
            p.add_argument("--timeout", type=int, default=600,
                           help="Default per-command timeout in seconds")
            p.add_argument("--total-timeout", type=int, default=1800,
                           help="Total verification deadline in seconds")
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
                                 args.reuse_tracked_worktree,
                                 args.confirm_previous_process_exited)
            elif args.command == "launch":
                if args.auto_approve and not args.approve:
                    raise ValueError("--auto-approve/--full-access requires explicit --approve")
                argv = json.loads(args.args_file.read_text(encoding="utf-8")) if args.args_file else None
                result = launch(root, args.task_id, AntigravityCLI(args.executable, argv, args.timeout, args.interactive, args.auto_approve, args.mode), args.approve, args.recover)
            elif args.command == "verify":
                result = verify(
                    root, args.task_id, args.approve, args.timeout,
                    args.total_timeout, args.approval_file,
                )
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
        return 2 if result.get("available") is False or result.get("phase") in {
            "LAUNCH_FAILED", "NEEDS_ATTENTION", "VERIFICATION_FAILED"
        } or result.get("status") in {"BLOCKED", "FAIL"} else 0
    except (ValueError, OSError, subprocess.SubprocessError, yaml.YAMLError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
