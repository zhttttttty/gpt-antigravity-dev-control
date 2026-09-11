#!/usr/bin/env python3
"""Initialize the minimal runtime state used by antigravity-delegate."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil


SKILL_ROOT = Path(__file__).resolve().parents[1]
TASK_TEMPLATE = SKILL_ROOT / "templates" / "task"
PROJECT_TEMPLATE = SKILL_ROOT / "templates" / "project"
STATE_DIRS = ("queue", "active", "review", "blocked", "done", "archive")


def init_project(repo: Path, install_codex_profile: bool = False) -> None:
    repo = repo.resolve()
    if not (repo / ".git").exists():
        raise SystemExit(f"ERROR: target is not a Git repository: {repo}")
    ai = repo / ".ai"
    templates = ai / "templates" / "task"
    templates.mkdir(parents=True, exist_ok=True)
    for state in STATE_DIRS:
        folder = ai / "tasks" / state
        folder.mkdir(parents=True, exist_ok=True)
        (folder / ".gitkeep").touch(exist_ok=True)
    (ai / "runtime" / "logs").mkdir(parents=True, exist_ok=True)
    for source in TASK_TEMPLATE.iterdir():
        target = templates / source.name
        if not target.exists():
            shutil.copy2(source, target)
    project = ai / "project"
    project.mkdir(parents=True, exist_ok=True)
    for source in PROJECT_TEMPLATE.iterdir():
        target = project / source.name
        if not target.exists():
            shutil.copy2(source, target)
    state = ai / "state" / "PROJECT_STATE.yaml"
    state.parent.mkdir(parents=True, exist_ok=True)
    if not state.exists():
        state.write_text("schema_version: 1\nstatus: READY\nactive_tasks: []\n", encoding="utf-8")
    gitignore = repo / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    additions = [".ai/runtime/", ".worktrees/"]
    missing = [line for line in additions if line not in existing.splitlines()]
    if missing:
        suffix = "\n" if existing and not existing.endswith("\n") else ""
        gitignore.write_text(existing + suffix + "\n".join(missing) + "\n", encoding="utf-8")
    if install_codex_profile:
        source = SKILL_ROOT / "templates" / "codex"
        if source.exists():
            shutil.copytree(source, repo / ".codex", dirs_exist_ok=True)
    print(f"INITIALIZED {repo}")
    print("Runtime: .ai/  Templates: .ai/templates/task  Project docs: .ai/project/")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--install-codex-profile", action="store_true")
    args = parser.parse_args()
    init_project(args.repo, args.install_codex_profile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
