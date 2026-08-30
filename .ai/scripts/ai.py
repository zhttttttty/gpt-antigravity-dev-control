#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path

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
        raise SystemExit("ERROR: not inside a Git repository or V2 template root")


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def task_locations(root, task_id):
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


def clean_scalar(value):
    return value.strip().strip("\"'")


def top_scalar(src, key):
    m = re.search(rf"(?m)^{re.escape(key)}:\s*([^#\n]+?)\s*$", src)
    return clean_scalar(m.group(1)) if m else None


def nested_scalar(src, section, key):
    lines = src.splitlines()
    sec_i = None
    sec_indent = 0
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)" + re.escape(section) + r":\s*$", line)
        if m:
            sec_i = i
            sec_indent = len(m.group(1))
            break
    if sec_i is None:
        return None
    for line in lines[sec_i + 1:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= sec_indent:
            break
        m = re.match(r"^\s*" + re.escape(key) + r":\s*([^#\n]+?)\s*$", line)
        if m:
            return clean_scalar(m.group(1))
    return None


def replace_top(path, key, value):
    src = read_text(path)
    pat = re.compile(rf"(?m)^({re.escape(key)}:\s*).*$")
    if not pat.search(src):
        raise SystemExit(f"ERROR: missing top-level key '{key}' in {path}")
    src = pat.sub(lambda m: f"{m.group(1)}{value}", src, count=1)
    path.write_text(src, encoding="utf-8")


def replace_nested(path, section, key, value):
    lines = read_text(path).splitlines()
    sec_i = None
    sec_indent = 0
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)" + re.escape(section) + r":\s*$", line)
        if m:
            sec_i = i
            sec_indent = len(m.group(1))
            break
    if sec_i is None:
        raise SystemExit(f"ERROR: missing section '{section}' in {path}")
    for i in range(sec_i + 1, len(lines)):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= sec_indent:
            break
        m = re.match(r"^(\s*)" + re.escape(key) + r":", line)
        if m:
            lines[i] = f"{m.group(1)}{key}: {value}"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return
    raise SystemExit(f"ERROR: missing nested key '{section}.{key}' in {path}")


def validate_task(root, task_id, quiet=False):
    folder_state, p = find_task(root, task_id)
    y = p / "task.yaml"
    errors = []
    if not y.exists():
        errors.append("missing task.yaml")
    else:
        src = read_text(y)
        for key in ["schema_version", "id", "title", "status", "contract_revision", "attempt", "objective"]:
            if top_scalar(src, key) is None:
                errors.append(f"missing top-level key: {key}")
        actual_id = top_scalar(src, "id")
        status = top_scalar(src, "status")
        risk = nested_scalar(src, "planning", "risk")
        worktree = nested_scalar(src, "isolation", "worktree")
        if actual_id and actual_id != task_id:
            errors.append(f"task id mismatch: folder={task_id}, task.yaml={actual_id}")
        if status and status not in STATES:
            errors.append(f"invalid status: {status}")
        if status and status != folder_state:
            errors.append(f"folder/status mismatch: folder={folder_state}, task.yaml={status}")
        if risk not in RISK:
            errors.append(f"invalid/missing planning.risk: {risk}")
        if risk in {"medium", "high"} and str(worktree).lower() != "true":
            errors.append(f"{risk} risk requires isolation.worktree: true")
        for section in ["planning", "roles", "scope", "authority", "isolation", "acceptance", "checks", "risk_controls", "artifacts", "metadata"]:
            if not re.search(rf"(?m)^{re.escape(section)}:\s*$", src):
                errors.append(f"missing section: {section}")
        for key in ["planner", "executor", "reviewer"]:
            if nested_scalar(src, "roles", key) is None:
                errors.append(f"missing roles.{key}")
        if not re.search(r"(?m)^\s+-\s+id:\s*AC-", src):
            errors.append("at least one acceptance item with id AC-* is required")
        if risk == "high":
            for key in ["rollback_plan_required", "cross_family_review_required", "human_merge_approval_required"]:
                if str(nested_scalar(src, "risk_controls", key)).lower() != "true":
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
    template = root / ".ai/templates/task"
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
        rv = top_scalar(read_text(src / "review.yaml"), "verdict")
        if rv not in {"PASS", "PASS_WITH_NOTES"}:
            raise SystemExit(f"ERROR: DONE requires review.yaml verdict PASS/PASS_WITH_NOTES, got {rv}")
        task_src = read_text(task_yaml)
        risk = nested_scalar(task_src, "planning", "risk")
        if risk == "high":
            qa_src = read_text(src / "receipt.qa.yaml")
            risk_result = nested_scalar(qa_src, "risk_gate", "result")
            cross_result = nested_scalar(qa_src, "cross_family_review", "result")
            human_result = nested_scalar(qa_src, "human_approval", "result")
            rollback = src / "rollback.md"
            if risk_result != "PASS":
                raise SystemExit(f"ERROR: high-risk DONE requires risk_gate.result PASS, got {risk_result}")
            if cross_result not in {"PASS", "WAIVED"}:
                raise SystemExit(f"ERROR: high-risk DONE requires cross-family review PASS/WAIVED, got {cross_result}")
            if human_result != "APPROVED":
                raise SystemExit(f"ERROR: high-risk DONE requires human_approval.result APPROVED, got {human_result}")
            if not rollback.exists() or not rollback.read_text(encoding="utf-8").strip():
                raise SystemExit("ERROR: high-risk DONE requires non-empty rollback.md")

    attempt = int(top_scalar(read_text(task_yaml), "attempt") or "1")
    contract_rev = int(top_scalar(read_text(task_yaml), "contract_revision") or "1")
    if current == "REVIEW" and target == "READY":
        archive_attempt(src, attempt)
        attempt += 1
        replace_top(task_yaml, "attempt", attempt)
        reset_receipts(root, src, task_id, attempt, contract_rev)

    replace_top(task_yaml, "status", target)
    replace_nested(task_yaml, "metadata", "updated_at", now())
    dest_parent = root / STATES[target]
    dest_parent.mkdir(parents=True, exist_ok=True)
    dest = dest_parent / task_id
    shutil.move(str(src), str(dest))
    print(f"{task_id}: {current} -> {target}")
    print(dest)
    return dest


def worktree_create(root, task_id):
    _, task = find_task(root, task_id)
    src = read_text(task / "task.yaml")
    base = nested_scalar(src, "isolation", "base_branch") or "main"
    branch = nested_scalar(src, "isolation", "branch") or f"ai/{task_id}"
    if run(["git", "rev-parse", "--git-dir"], cwd=root, check=False).returncode != 0:
        raise SystemExit("ERROR: worktree requires Git repository")
    base_exists = run(["git", "rev-parse", "--verify", base], cwd=root, check=False).returncode == 0
    if not base_exists:
        current = run(["git", "branch", "--show-current"], cwd=root, check=False).stdout.strip()
        base = current or "HEAD"
        print(f"WARNING: configured base branch not found; using {base}", file=sys.stderr)
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
        cmd += [str(dest), branch]
    else:
        cmd += ["-b", branch, str(dest), base]
    cp = run(cmd, cwd=root, check=False)
    if cp.returncode != 0:
        raise SystemExit(f"ERROR: git worktree add failed\n{cp.stdout}\n{cp.stderr}")
    print(f"WORKTREE {task_id}: {dest}")
    print(f"BRANCH: {branch}")
    return dest


def worktree_remove(root, task_id, force=False):
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


def start(root, task_id, with_worktree):
    state, _ = find_task(root, task_id)
    if state != "READY":
        raise SystemExit(f"ERROR: start requires READY task, got {state}")
    if not validate_task(root, task_id):
        raise SystemExit(2)
    if with_worktree:
        dest = worktree_create(root, task_id)
        transition(dest, task_id, "IN_PROGRESS")
        print("NOTE: active state is task-branch local until the branch is integrated.")
    else:
        transition(root, task_id, "IN_PROGRESS")


def status(root):
    for state, rel in STATES.items():
        base = root / rel
        tasks = sorted(p.name for p in base.iterdir() if p.is_dir()) if base.exists() else []
        print(f"{state:12} {', '.join(tasks) if tasks else '-'}")


def main():
    ap = argparse.ArgumentParser(description="GPT-5.6 Sol × Antigravity V2 task helper")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("validate"); p.add_argument("task_id")
    p = sub.add_parser("transition"); p.add_argument("task_id"); p.add_argument("state", choices=list(STATES))
    p = sub.add_parser("start"); p.add_argument("task_id"); p.add_argument("--worktree", action="store_true")
    p = sub.add_parser("worktree-create"); p.add_argument("task_id")
    p = sub.add_parser("worktree-remove"); p.add_argument("task_id"); p.add_argument("--force", action="store_true")
    sub.add_parser("status")
    ns = ap.parse_args()
    root = repo_root()
    if ns.cmd == "validate":
        return 0 if validate_task(root, ns.task_id) else 2
    if ns.cmd == "transition": transition(root, ns.task_id, ns.state)
    elif ns.cmd == "start": start(root, ns.task_id, ns.worktree)
    elif ns.cmd == "worktree-create": worktree_create(root, ns.task_id)
    elif ns.cmd == "worktree-remove": worktree_remove(root, ns.task_id, ns.force)
    elif ns.cmd == "status": status(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
