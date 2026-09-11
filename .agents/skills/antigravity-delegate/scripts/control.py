#!/usr/bin/env python3
"""Single entry point shipped with the antigravity-delegate Skill."""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
CORE = {"create", "validate", "transition", "start", "worktree-create", "worktree-remove"}
DELEGATION = {"probe", "route", "prepare", "launch", "collect", "diagnose"}
HELP = """usage: control.py [--repo PATH] COMMAND [ARGS...]

Unified local AI development control plane.

Task protocol commands:
  init                          initialize minimal target project state
  create, validate, transition, start, worktree-create, worktree-remove

Local delegation commands:
  probe, route, prepare, launch, collect, status, diagnose
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    repo = Path.cwd()
    rest: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--repo":
            i += 1
            repo = Path(args[i])
        elif args[i].startswith("--repo="):
            repo = Path(args[i].split("=", 1)[1])
        else:
            rest.append(args[i])
        i += 1
    if not rest or rest[0] in {"-h", "--help"}:
        print(HELP)
        return 0
    command = rest[0]
    if command == "init":
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
    old_argv, old_cwd = sys.argv, Path.cwd()
    try:
        os.chdir(repo)
        sys.argv = [str(entry), *child]
        try:
            runpy.run_path(str(entry), run_name="__main__")
        except SystemExit as exc:
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


if __name__ == "__main__":
    raise SystemExit(main())
