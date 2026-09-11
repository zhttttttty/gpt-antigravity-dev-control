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
        print("usage: control.py [--repo PATH] COMMAND [ARGS...]\n\nCommands: init, create, validate, route, prepare, launch, collect, status, transition, probe, diagnose")
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
        raise SystemExit(f"ERROR: unknown command: {command}")
    old_argv, old_cwd = sys.argv, Path.cwd()
    try:
        os.chdir(repo)
        sys.argv = [str(entry), *child]
        runpy.run_path(str(entry), run_name="__main__")
    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
