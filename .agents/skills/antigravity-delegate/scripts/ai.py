#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import subprocess
import sys
from pathlib import Path

from task_data import (read_yaml, write_yaml, parse_yaml, task_id as checked_id,
                       done_errors, require_approval)

STATES = {
    "READY": ".ai/tasks/queue",
    "IN_PROGRESS": ".ai/tasks/active",
    "REVIEW": ".ai/tasks/review",
    "BLOCKED": ".ai/tasks/blocked",
    "DONE": ".ai/tasks/done",
    "ARCHIVED": ".ai/tasks/archive",
}
ALLOWED = {
    "READY": {"IN_PROGRESS", "BLOCKED"},
    "IN_PROGRESS": {"REVIEW", "BLOCKED"},
    "REVIEW": {"DONE", "READY", "BLOCKED"},
    "BLOCKED": {"READY"},
    "DONE": {"ARCHIVED"},
    "ARCHIVED": set(),
}
RISK = {"low", "medium", "high"}


def template_dir(root):
    """Use project templates when initialized, otherwise bundled Skill templates."""
    local = root / ".ai/templates/task"
    bundled = Path(__file__).resolve().parents[1] / "templates/task"
    return local if local.exists() else bundled


def run(cmd, cwd=None, check=True):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check)


def repo_root(start=None):
    cwd = (start or Path.cwd()).resolve()
    try:
        return Path(run(["git", "rev-parse", "--show-toplevel"], cwd=cwd).stdout.strip()).resolve()
    except Exception:
        cur = cwd
        while cur != cur.parent:
            if (cur / ".ai").exists():
                return cur
            cur = cur.parent
        raise SystemExit("ERROR: not inside a Git repository or control-plane root")


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def task_locations(root, task_id):
    checked_id(task_id)
    out = []
    for state, rel in STATES.items():
        p = root / rel / task_id
        if p.is_dir():
            out.append((state, p))
    return out


def find_task(root, task_id):
    locs = task_locations(root, task_id)
    if not locs:
        raise SystemExit(f"ERROR: task not found: {task_id}")
    if len(locs) > 1:
        raise SystemExit(f"ERROR: task exists in multiple state folders: {locs}")
    return locs[0]


def read_text(path):
    return path.read_text(encoding="utf-8")


def top_scalar(src, key):
    return parse_yaml(src).get(key)


def nested_scalar(src, section, key):
    value = parse_yaml(src).get(section)
    return value.get(key) if isinstance(value, dict) else None


def replace_top(path, key, value):
    data = read_yaml(path)
    if key not in data:
        raise SystemExit(f"ERROR: missing top-level key '{key}' in {path}")
    data[key] = value
    write_yaml(path, data)


def replace_nested(path, section, key, value):
    data = read_yaml(path)
    if not isinstance(data.get(section), dict) or key not in data[section]:
        raise SystemExit(f"ERROR: missing nested key '{section}.{key}' in {path}")
    data[section][key] = value
    write_yaml(path, data)


def validate_task(root, task_id, quiet=False):
    folder_state, p = find_task(root, task_id)
    y = p / "task.yaml"
    errors = []
    if not y.exists():
        errors.append("missing task.yaml")
    else:
        try:
            data = read_yaml(y)
        except (ValueError, OSError) as exc:
            if not quiet:
                print(f"INVALID {task_id}: {exc}")
            return False
        for key in ["schema_version", "id", "title", "status", "contract_revision", "attempt", "objective"]:
            if not data.get(key):
                errors.append(f"missing top-level key: {key}")
        for key in ("schema_version", "contract_revision", "attempt"):
            if type(data.get(key)) is not int or data[key] < 1:
                errors.append(f"{key} must be a positive integer")
        if data.get("schema_version") != 2:
            errors.append("schema_version must be 2")
        sections = ["planning", "roles", "scope", "authority", "isolation", "checks", "risk_controls", "artifacts", "metadata"]
        for section in sections:
            if not isinstance(data.get(section), dict):
                errors.append(f"missing/invalid mapping: {section}")
        if any(not isinstance(data.get(section), dict) for section in sections):
            if not quiet:
                print(f"INVALID {task_id}: " + "; ".join(errors))
            return False
        actual_id = data.get("id")
        status = data.get("status")
        risk = data["planning"].get("risk")
        worktree = data["isolation"].get("worktree")
        if actual_id and actual_id != task_id:
            errors.append(f"task id mismatch: folder={task_id}, task.yaml={actual_id}")
        if not isinstance(status, str) or status not in STATES:
            errors.append(f"invalid status: {status}")
        if status and status != folder_state:
            errors.append(f"folder/status mismatch: folder={folder_state}, task.yaml={status}")
        if not isinstance(risk, str) or risk not in RISK:
            errors.append(f"invalid/missing planning.risk: {risk}")
        if risk in ("medium", "high") and worktree is not True:
            errors.append(f"{risk} risk requires isolation.worktree: true")
        for key in ["planner", "executor", "reviewer"]:
            if not isinstance(data["roles"].get(key), str) or not data["roles"][key].strip():
                errors.append(f"missing roles.{key}")
        acceptance = data.get("acceptance")
        if not isinstance(acceptance, list) or not acceptance or not all(
                isinstance(item, dict) and isinstance(item.get("id"), str)
                and item["id"].startswith("AC-") and item.get("criterion") and item.get("evidence")
                for item in acceptance):
            errors.append("acceptance requires AC-* items with criterion/evidence")
        elif len({item["id"] for item in acceptance}) != len(acceptance):
            errors.append("acceptance IDs must be unique")
        required = data["checks"].get("required")
        if not isinstance(required, list) or not all(isinstance(item, dict) and
                isinstance(item.get("command"), str) and item["command"].strip() for item in required):
            errors.append("checks.required must contain command mappings")
        for section in ("authority", "risk_controls"):
            if any(type(value) is not bool for value in data[section].values()):
                errors.append(f"{section} values must be booleans")
        if type(worktree) is not bool:
            errors.append("isolation.worktree must be boolean")
        execution = data.get("execution", {})
        if not isinstance(execution, dict) or execution.get("mode", "direct") not in ("direct", "delegated", "approval_required"):
            errors.append("invalid execution.mode")
        for key in ("writable", "protected"):
            values = data["scope"].get(key)
            if not isinstance(values, list) or not all(isinstance(value, str) and value for value in values):
                errors.append(f"scope.{key} must be a list of paths")
        dependencies = data["planning"].get("depends_on", [])
        if not isinstance(dependencies, list) or not all(isinstance(value, str) for value in dependencies):
            errors.append("planning.depends_on must be a list of task IDs")
        if risk == "high":
            for key in ["rollback_plan_required", "cross_family_review_required", "human_merge_approval_required"]:
                if data["risk_controls"].get(key) is not True:
                    errors.append(f"high risk requires risk_controls.{key}: true")
    for f in ["brief.md", "context.md", "receipt.executor.yaml", "receipt.qa.yaml", "review.yaml", "rollback.md"]:
        if not (p / f).exists():
            errors.append(f"missing artifact: {f}")
    if errors:
        if not quiet:
            print(f"INVALID {task_id}")
            for e in errors:
                print(f"  - {e}")
        return False
    if not quiet:
        print(f"VALID {task_id} [{folder_state}]")
    return True


def archive_attempt(task_dir, attempt):
    hist = task_dir / "history" / f"attempt-{attempt}"
    hist.mkdir(parents=True, exist_ok=True)
    for name in ["receipt.executor.yaml", "receipt.qa.yaml", "review.yaml"]:
        src = task_dir / name
        if src.exists():
            shutil.copy2(src, hist / name)


def reset_receipts(root, task_dir, task_id, attempt, contract_rev):
    template = template_dir(root)
    for name in ["receipt.executor.yaml", "receipt.qa.yaml", "review.yaml"]:
        shutil.copy2(template / name, task_dir / name)
        replace_top(task_dir / name, "task_id", task_id)
        replace_top(task_dir / name, "attempt", attempt)
        if name != "review.yaml":
            replace_top(task_dir / name, "contract_revision", contract_rev)


def transition(root, task_id, target):
    target = target.upper()
    if target not in STATES:
        raise SystemExit(f"ERROR: unknown target state {target}")
    current, src = find_task(root, task_id)
    if target not in ALLOWED[current]:
        raise SystemExit(f"ERROR: illegal transition {current} -> {target}")
    if not validate_task(root, task_id, quiet=True):
        raise SystemExit("ERROR: task validation failed; run validate for details")
    task_yaml = src / "task.yaml"

    if current == "REVIEW" and target == "DONE":
        try:
            errors = done_errors(read_yaml(task_yaml), src)
        except (ValueError, OSError, TypeError, KeyError) as exc:
            raise SystemExit(f"ERROR: invalid acceptance evidence: {exc}") from exc
        if errors:
            raise SystemExit("ERROR: DONE rejected: " + "; ".join(errors))

    attempt = int(top_scalar(read_text(task_yaml), "attempt") or "1")
    contract_rev = int(top_scalar(read_text(task_yaml), "contract_revision") or "1")
    if current == "REVIEW" and target == "READY":
        archive_attempt(src, attempt)
        attempt += 1
        replace_top(task_yaml, "attempt", attempt)
        reset_receipts(root, src, task_id, attempt, contract_rev)

    data = read_yaml(task_yaml)
    data["status"] = target
    data["metadata"]["updated_at"] = now()
    write_yaml(task_yaml, data)
    dest_parent = root / STATES[target]
    dest_parent.mkdir(parents=True, exist_ok=True)
    dest = dest_parent / task_id
    shutil.move(str(src), str(dest))
    print(f"{task_id}: {current} -> {target}")
    print(dest)
    return dest


def worktree_create(root, task_id):
    if not validate_task(root, task_id, quiet=True):
        raise ValueError("Invalid task contract")
    _, task = find_task(root, task_id)
    src = read_text(task / "task.yaml")
    base = nested_scalar(src, "isolation", "base_branch") or "main"
    branch = nested_scalar(src, "isolation", "branch") or f"ai/{task_id}"
    if run(["git", "rev-parse", "--git-dir"], cwd=root, check=False).returncode != 0:
        raise SystemExit("ERROR: worktree requires Git repository")
    if run(["git", "status", "--porcelain"], cwd=root).stdout.strip():
        raise ValueError("Commit or stash workspace changes, including task contract, before creating a worktree")
    base_commit = run(["git", "rev-parse", "--verify", f"{base}^{{commit}}"], cwd=root).stdout.strip()
    if base_commit != run(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip():
        raise ValueError("Configured base must equal current HEAD containing the committed task; no silent fallback")
    wtroot = root / ".worktrees"
    wtroot.mkdir(exist_ok=True)
    dest = wtroot / task_id
    if dest.exists():
        raise SystemExit(f"ERROR: worktree path already exists: {dest}")
    ignored = run(["git", "check-ignore", "-q", ".worktrees"], cwd=root, check=False).returncode == 0
    if not ignored:
        print("WARNING: .worktrees is not ignored. Add '.worktrees/' to .gitignore.", file=sys.stderr)
    branch_exists = run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=root, check=False).returncode == 0
    cmd = ["git", "worktree", "add"]
    if branch_exists:
        raise ValueError("Task branch already exists; inspect it and choose a fresh contract branch")
    else:
        cmd += ["-b", branch, str(dest), base]
    cp = run(cmd, cwd=root, check=False)
    if cp.returncode != 0:
        raise SystemExit(f"ERROR: git worktree add failed\n{cp.stdout}\n{cp.stderr}")
    print(f"WORKTREE {task_id}: {dest}")
    print(f"BRANCH: {branch}")
    return dest


def worktree_remove(root, task_id, force=False):
    checked_id(task_id)
    dest = root / ".worktrees" / task_id
    if not dest.exists():
        raise SystemExit(f"ERROR: worktree not found: {dest}")
    cmd = ["git", "worktree", "remove"]
    if force:
        cmd.append("--force")
    cmd.append(str(dest))
    cp = run(cmd, cwd=root, check=False)
    if cp.returncode != 0:
        raise SystemExit(f"ERROR: git worktree remove failed\n{cp.stdout}\n{cp.stderr}")
    print(f"REMOVED {dest}")


def start(root, task_id, with_worktree, approval=None):
    state, folder = find_task(root, task_id)
    if state != "READY":
        raise SystemExit(f"ERROR: start requires READY task, got {state}")
    if not validate_task(root, task_id):
        raise SystemExit(2)
    task = read_yaml(folder / "task.yaml")
    mode = task.get("execution", {}).get("mode", "direct")
    if mode == "delegated":
        raise ValueError("Delegated task: use prepare instead of start")
    for dependency in task["planning"].get("depends_on", []):
        dep_state, _ = find_task(root, dependency)
        if dep_state not in {"DONE", "ARCHIVED"} or not validate_task(root, dependency, quiet=True):
            raise ValueError(f"Dependency not completed: {dependency}")
    if mode == "approval_required" or task["planning"]["risk"] == "high" or any(task["authority"].values()):
        require_approval(task, task_id, approval)
    if task["isolation"]["worktree"] and not with_worktree:
        raise ValueError("Task requires --worktree isolation")
    if with_worktree:
        dest = worktree_create(root, task_id)
        print(f"EXECUTION WORKSPACE: {dest}")
    active = transition(root, task_id, "IN_PROGRESS")
    print(f"CONTROLLER RECEIPT: {active / 'receipt.executor.yaml'}")
    return active


def create(root, ident, title, objective, risk="low", mode="direct"):
    checked_id(ident)
    if task_locations(root, ident):
        raise ValueError(f"Task already exists: {ident}")
    if not title.strip() or not objective.strip() or risk not in RISK or mode not in {"direct", "delegated", "approval_required"}:
        raise ValueError("Nonempty title/objective and valid risk/mode required")
    folder = root / STATES["READY"] / ident
    shutil.copytree(template_dir(root), folder)
    task = read_yaml(folder / "task.yaml")
    task.update(id=ident, title=title, objective=objective)
    task["planning"]["risk"] = risk
    task["execution"]["mode"] = mode
    task["roles"]["executor"] = "codex" if mode == "direct" else "antigravity"
    task["isolation"].update(branch=f"ai/{ident}", worktree=True)
    task["metadata"].update(created_at=now(), updated_at=now())
    if risk == "high":
        task["risk_controls"] = dict.fromkeys(task["risk_controls"], True)
    # An empty acceptance list keeps a scaffold invalid until a planner fills it.
    task["acceptance"] = []
    task["checks"]["required"] = []
    task["scope"]["writable"] = []
    write_yaml(folder / "task.yaml", task)
    reset_receipts(root, folder, ident, 1, 1)
    print(f"CREATED {folder}; fill scope, acceptance and checks before validate/start")
    return folder


def status(root):
    for state, rel in STATES.items():
        base = root / rel
        tasks = sorted(p.name for p in base.iterdir() if p.is_dir()) if base.exists() else []
        print(f"{state:12} {', '.join(tasks) if tasks else '-'}")


def main():
    ap = argparse.ArgumentParser(description="Core task protocol helper (compatibility entry point)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create"); p.add_argument("task_id")
    p.add_argument("--title", required=True); p.add_argument("--objective", required=True)
    p.add_argument("--risk", choices=sorted(RISK), default="low")
    p.add_argument("--mode", choices=["direct", "delegated", "approval_required"], default="direct")
    p = sub.add_parser("validate"); p.add_argument("task_id")
    p = sub.add_parser("transition"); p.add_argument("task_id"); p.add_argument("state", choices=list(STATES))
    p = sub.add_parser("start"); p.add_argument("task_id"); p.add_argument("--worktree", action="store_true")
    p.add_argument("--approval-file")
    p = sub.add_parser("worktree-create"); p.add_argument("task_id")
    p = sub.add_parser("worktree-remove"); p.add_argument("task_id"); p.add_argument("--force", action="store_true")
    sub.add_parser("status")
    ns = ap.parse_args()
    root = repo_root()
    if ns.cmd == "validate":
        return 0 if validate_task(root, ns.task_id) else 2
    if ns.cmd == "create": create(root, ns.task_id, ns.title, ns.objective, ns.risk, ns.mode)
    elif ns.cmd == "transition": transition(root, ns.task_id, ns.state)
    elif ns.cmd == "start": start(root, ns.task_id, ns.worktree, ns.approval_file)
    elif ns.cmd == "worktree-create": worktree_create(root, ns.task_id)
    elif ns.cmd == "worktree-remove": worktree_remove(root, ns.task_id, ns.force)
    elif ns.cmd == "status": status(root)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
