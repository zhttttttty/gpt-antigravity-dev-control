#!/usr/bin/env python3
"""Single entry point shipped with the antigravity-delegate Skill."""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
CORE = {"create", "validate", "transition", "start", "worktree-create", "worktree-remove"}
DELEGATION = {"probe", "route", "prepare", "launch", "verify", "collect", "diagnose"}
HELP = """usage: control.py [--repo PATH] COMMAND [ARGS...]

Unified local AI development control plane.

Daily delegation:
  run "REQUEST" [--check CMD]    isolated agy run without task scaffolding

Task protocol commands:
  init                          initialize minimal target project state
  create, validate, transition, start, worktree-create, worktree-remove
  status [--json]               list live task state (JSON when requested)

Configuration checks:
  check-orchestration           validate installed project model configuration

Local delegation commands:
  probe, route, prepare, launch, verify, collect, status TASK-ID, diagnose
"""


def _main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    repo = Path.cwd()
    rest: list[str] = []
    explicit_repo = False
    i = 0
    while i < len(args):
        if args[i] == "--repo":
            i += 1
            if i >= len(args) or not args[i] or args[i].startswith("-"):
                raise ValueError("--repo requires a nonempty path")
            if explicit_repo:
                raise ValueError("--repo may only be specified once")
            repo = Path(args[i])
            explicit_repo = True
        elif args[i].startswith("--repo="):
            value = args[i].split("=", 1)[1]
            if not value:
                raise ValueError("--repo requires a nonempty path")
            if explicit_repo:
                raise ValueError("--repo may only be specified once")
            repo = Path(value)
            explicit_repo = True
        else:
            rest.append(args[i])
        i += 1
    if not rest or rest[0] in {"-h", "--help"}:
        print(HELP)
        return 0
    command = rest[0]
    # Resolve before chdir: a relative init path must not be applied twice.
    repo = repo.expanduser().resolve()
    if command == "run":
        entry, child = SCRIPT_DIR / "quick_run.py", rest[1:]
    elif command == "init":
        entry = SCRIPT_DIR / "init_project.py"
        child = ["--repo", str(repo)] + rest[1:]
    elif command == "check-orchestration":
        entry, child = SCRIPT_DIR / "check_orchestration.py", rest[1:]
    elif command == "status" and any(not x.startswith("-") for x in rest[1:]):
        entry, child = SCRIPT_DIR / "delegate.py", rest
    elif command == "status" or command in CORE:
        entry, child = SCRIPT_DIR / "ai.py", rest
    elif command in DELEGATION:
        entry, child = SCRIPT_DIR / "delegate.py", rest
    else:
        print(f"ERROR: unknown command: {command}", file=sys.stderr)
        return 2
    if (explicit_repo and command in CORE | DELEGATION | {"status", "run"}
            and not any(arg in {"-h", "--help"} for arg in rest[1:])):
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=repo,
                                capture_output=True, text=True, check=True)
        actual = Path(result.stdout.strip()).resolve()
        if actual != repo:
            raise ValueError(f"--repo must name the Git repository root; {repo} belongs to {actual}")
    old_argv, old_cwd = sys.argv, Path.cwd()
    try:
        os.chdir(repo)
        sys.argv = [str(entry), *child]
        try:
            runpy.run_path(str(entry), run_name="__main__")
        except SystemExit as exc:
            if exc.code is None:
                return 0
            if isinstance(exc.code, int):
                return exc.code
            if exc.code:
                print(exc.code, file=sys.stderr)
            return 2
        except (ValueError, OSError, RuntimeError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
