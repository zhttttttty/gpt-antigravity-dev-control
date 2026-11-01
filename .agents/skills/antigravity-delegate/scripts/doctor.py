"""Read-only readiness report. Does not launch prompts or create project state."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys


def inspect(root: Path, executable="agy") -> dict:
    checks = []

    def add(name, ok, detail, action=""):
        checks.append({"name": name, "status": "PASS" if ok else "BLOCKED",
                       "detail": detail, "next_step": "" if ok else action})

    add("python", sys.version_info >= (3, 11), sys.version.split()[0], "Use Python 3.11 or newer")
    dependencies = importlib.util.find_spec("yaml") is not None
    requirement = Path(__file__).with_name("requirements-local.txt")
    add("dependencies", dependencies, "PyYAML available" if dependencies else "PyYAML missing",
        f'"{sys.executable}" -m pip install -r "{requirement}"')
    found_git = shutil.which("git")
    add("git", bool(found_git), found_git or "Git missing", "Install Git and add it to PATH")
    repository = None
    if found_git:
        try:
            def git(*args):
                return subprocess.run([found_git, *args], cwd=root, check=True,
                                      capture_output=True, text=True, encoding="utf-8",
                                      errors="replace", timeout=15).stdout.strip()
            repository = str(Path(git("rev-parse", "--show-toplevel")).resolve())
            add("repository", Path(repository) == root.resolve(), repository,
                "Run from the Git root or provide --repo with that exact path")
            try:
                head = git("rev-parse", "--verify", "HEAD^{commit}")
                add("commit", True, head)
            except subprocess.CalledProcessError:
                add("commit", False, "Repository has no commit", "Review and create an initial commit before run")
            dirty = git("status", "--porcelain=v1", "--untracked-files=all")
            add("source", not bool(dirty), dirty.splitlines()[:20] if dirty else "Clean",
                "Review git status; preserve your edits explicitly. Only committed files enter the worktree")
        except (OSError, subprocess.SubprocessError) as exc:
            add("repository", False, str(exc), "Select an accessible Git repository with --repo")
    if dependencies:
        from adapters.antigravity_cli import AntigravityCLI
        adapter = AntigravityCLI(executable)
        try:
            adapter.validate_launch()  # only --help; no model, login or prompt
            add("agy", True, {"executable": adapter.resolve(), "capabilities": adapter.capabilities()})
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            add("agy", False, str(exc), "Use --executable with a compatible native agy executable; login separately if needed")
    return {"status": "READY" if all(c["status"] == "PASS" for c in checks) else "BLOCKED",
            "repository": repository, "checks": checks, "login": "UNKNOWN", "headless": "UNVERIFIED",
            "next_step": "Preview with run REQUEST --allow PATH --dry-run, then remove --dry-run to execute"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", default="agy")
    args = parser.parse_args()
    result = inspect(Path.cwd(), args.executable)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
