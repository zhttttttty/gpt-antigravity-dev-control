#!/usr/bin/env python3
"""Initialize the minimal runtime state used by antigravity-delegate."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import stat
import subprocess


SKILL_ROOT = Path(__file__).resolve().parents[1]
TASK_TEMPLATE = SKILL_ROOT / "templates" / "task"
PROJECT_TEMPLATE = SKILL_ROOT / "templates" / "project"
STATE_DIRS = ("queue", "active", "review", "blocked", "done", "archive")


def profile_plan(repo: Path, overwrite: bool) -> list[tuple[Path, Path]]:
    """Preflight the entire profile before changing any target files."""
    source = SKILL_ROOT / "templates" / "codex"
    canonical = SKILL_ROOT / "templates" / "project-config.yaml"
    if not source.is_dir() or not canonical.is_file():
        raise ValueError("Bundled Codex profile or project configuration is missing")
    files = [(p, repo / ".codex" / p.relative_to(source))
             for p in sorted(source.rglob("*")) if p.is_file()]
    files.append((canonical, repo / ".ai/config.yaml"))
    conflicts = []
    for src, target in files:
        for path in (target, *target.parents):
            if path == repo:
                break
            attributes = getattr(path.lstat(), "st_file_attributes", 0) if path.exists() else 0
            if path.is_symlink() or attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
                raise ValueError(f"Profile target must not traverse a link: {path}")
            if path.exists() and path != target and not path.is_dir():
                raise ValueError(f"Profile parent is not a directory: {path}")
        if target.exists():
            if not target.is_file():
                raise ValueError(f"Profile target is not a file: {target}")
            if src.read_bytes() != target.read_bytes() and not overwrite:
                conflicts.append(target.relative_to(repo).as_posix())
    if conflicts:
        raise ValueError("Existing configuration differs: " + ", ".join(conflicts)
                         + "; inspect the diff before using --overwrite-codex-profile")
    return files


def init_project(repo: Path, install_codex_profile: bool = False,
                 overwrite_codex_profile: bool = False) -> None:
    repo = repo.resolve()
    actual = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=repo,
                            capture_output=True, text=True, check=True)
    if Path(actual.stdout.strip()).resolve() != repo:
        raise ValueError(f"init requires a Git repository root: {repo}")
    if overwrite_codex_profile and not install_codex_profile:
        raise ValueError("--overwrite-codex-profile requires --install-codex-profile")
    profile = profile_plan(repo, overwrite_codex_profile) if install_codex_profile else []
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
    for source, target in profile:
        if not target.exists() or source.read_bytes() != target.read_bytes():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    print(f"INITIALIZED {repo}")
    print("Runtime: .ai/  Templates: .ai/templates/task  Project docs: .ai/project/")
    if profile:
        print("Profile: .codex/  Configuration: .ai/config.yaml (offline defaults only)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--install-codex-profile", action="store_true")
    parser.add_argument("--overwrite-codex-profile", action="store_true",
                        help="Explicitly replace conflicting profile/config files after reviewing differences")
    args = parser.parse_args()
    init_project(args.repo, args.install_codex_profile, args.overwrite_codex_profile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
