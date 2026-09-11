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
from task_data import read_yaml, digest, task_id, require_approval, evidence_counts, write_yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "adapters"))
from antigravity_cli import AntigravityCLI, diagnose
from executor_interface import Executor


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


def prepare(root, ident, approved=False, approval=None):
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
    base_ref = task["isolation"].get("base_branch", "HEAD")
    base = git(root, "rev-parse", "--verify", f"{base_ref}^{{commit}}")
    if base != git(root, "rev-parse", "HEAD"):
        raise ValueError("Configured base must equal current HEAD containing the committed task; no silent fallback")
    logs = root / ".ai/runtime/logs" / ident
    previous = list(logs.glob("run-*")) if logs.exists() else []
    if len(previous) >= attempts:
        raise ValueError("Attempt budget exhausted; escalate to Codex review")
    number = len(previous) + 1
    run_dir = logs / f"run-{number}"
    worktree = root / ".worktrees" / f"{ident}-{number}"
    branch = f"ai/local/{ident}-{number}"
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
    save(run_dir / "run.json", record)
    try:
        worktree.parent.mkdir(exist_ok=True)
        git(root, "worktree", "add", "-b", branch, str(worktree), base)
        runtime = worktree / ".ai/runtime/delegation"
        runtime.mkdir(parents=True, exist_ok=True)
        atomic(runtime / "context.md", pack)
        template = read_yaml(root / ".ai/templates/task/receipt.executor.yaml")
        template.update(task_id=ident, attempt=task["attempt"], contract_revision=task["contract_revision"])
        write_yaml(runtime / "receipt.executor.yaml", template)
        write_yaml(run_dir / "contract.yaml", task)
        atomic(run_dir / "context.md", pack)
        transition(root, ident, "IN_PROGRESS")
        record["phase"] = "PREPARED"
    except BaseException as exc:
        record.update(phase="BLOCKED", error=str(exc))
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


def scope_violations(files, task):
    writable = task["scope"].get("writable", [])
    protected = task["scope"].get("protected", []) + [".ai/**", ".agents/**", "AGENTS.md", "GEMINI.md"]
    return [p for p in files if any(fnmatch.fnmatchcase(p, pat) for pat in protected)
            or not any(fnmatch.fnmatchcase(p, pat) for pat in writable)]


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
    violations = scope_violations(files, task)
    receipt_path = worktree / ".ai/runtime/delegation/receipt.executor.yaml"
    receipt = read_yaml(receipt_path)
    if any(receipt.get(k) != v for k, v in {"task_id": ident, "attempt": task["attempt"],
                                           "contract_revision": task["contract_revision"], "schema_version": 2}.items()):
        raise ValueError("Receipt identity/revision mismatch")
    if receipt.get("status") not in {"COMPLETE", "BLOCKED", "FAILED"}:
        raise ValueError("Receipt is not complete; launcher exit is not evidence")
    passed, required_count, ac_passed, acceptance_count = evidence_counts(task, receipt)
    issues = []
    if violations:
        issues.append("Out-of-scope changes; inspect local full evidence")
    if passed != required_count or ac_passed != acceptance_count:
        issues.append("Required evidence missing or failed")
    if receipt.get("known_issues") or receipt.get("unverified_items"):
        issues.append("Executor reports issues or unverified items")
    if (receipt.get("architecture_deviation") or {}).get("result") != "NONE":
        issues.append("Architecture deviation needs review")
    target = "REVIEW" if receipt["status"] == "COMPLETE" and not issues else "BLOCKED"
    summary = {"task_id": ident, "status": "COMPLETE" if target == "REVIEW" else "BLOCKED",
               "task_state": target, "base_commit": record["base_commit"], "head_commit": head,
               "changed_files": len(files), "changed_files_preview": files[:20],
               "scope_check": "FAIL" if violations else "PASS", "known_issues": issues,
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
                result = prepare(root, args.task_id, args.approve, args.approval_file)
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
