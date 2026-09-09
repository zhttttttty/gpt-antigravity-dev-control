#!/usr/bin/env python3
"""Unified local control CLI for task protocol and Antigravity delegation."""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
CORE_COMMANDS = {
    "validate",
    "transition",
    "start",
    "worktree-create",
    "worktree-remove",
}
DELEGATION_COMMANDS = {
    "probe",
    "route",
    "prepare",
    "launch",
    "collect",
    "diagnose",
}


HELP = """usage: control.py [--repo PATH] COMMAND [ARGS...]

Unified local AI development control plane.

Task protocol commands:
  status                         list task states
  validate TASK                 validate a task contract
  start TASK [--worktree]       start a direct/manual task
  transition TASK STATE         apply a reviewed state transition
  worktree-create TASK          create a protocol worktree
  worktree-remove TASK [--force]

Local delegation commands:
  probe [--executable PATH]      inspect the local agy CLI
  route TASK                    resolve execution.mode
  prepare TASK --approve        prepare an isolated delegation attempt
  launch TASK --approve [...]   launch agy in the prepared worktree
  status TASK                   show the latest delegation run
  diagnose TASK                 classify a stopped/failed run
  collect TASK                  validate and collect executor evidence

Use `control.py COMMAND --help` for command-specific options.
The legacy ai.py and delegate.py entry points remain compatible.
"""


def parse_global(argv: list[str]) -> tuple[Path, list[str]]:
    """Extract --repo from either side of COMMAND without consuming child args."""
    repo = Path.cwd()
    rest: list[str] = []
    index = 0
    while index < len(argv):
        value = argv[index]
        if value == "--repo":
            index += 1
            if index >= len(argv):
                raise ValueError("--repo requires a path")
            repo = Path(argv[index])
        elif value.startswith("--repo="):
            repo = Path(value.split("=", 1)[1])
        else:
            rest.append(value)
        index += 1
    return repo, rest


def target_for(arguments: list[str]) -> Path:
    command = arguments[0]
    if command == "status":
        # `status` lists protocol state with no task and shows delegation state
        # when a task identifier is supplied.
        positional = [value for value in arguments[1:] if not value.startswith("-")]
        name = "delegate.py" if positional else "ai.py"
    elif command in CORE_COMMANDS:
        name = "ai.py"
    elif command in DELEGATION_COMMANDS:
        name = "delegate.py"
    else:
        raise ValueError(f"unknown command: {command}")
    return SCRIPT_DIR / name


def run_entry(entry: Path, arguments: list[str], repo: Path) -> int:
    previous_argv = sys.argv
    previous_cwd = Path.cwd()
    try:
        os.chdir(repo)
        sys.argv = [str(entry), *arguments]
        try:
            runpy.run_path(str(entry), run_name="__main__")
        except SystemExit as exc:
            if exc.code is None:
                return 0
            if isinstance(exc.code, int):
                return exc.code
            print(exc.code, file=sys.stderr)
            return 2
        return 0
    finally:
        sys.argv = previous_argv
        os.chdir(previous_cwd)


def main(argv: list[str] | None = None) -> int:
    try:
        repo, arguments = parse_global(list(sys.argv[1:] if argv is None else argv))
        if not arguments or arguments == ["--help"] or arguments == ["-h"]:
            print(HELP, end="")
            return 0
        repo = repo.expanduser().resolve()
        if not repo.is_dir():
            raise ValueError(f"repository path is not a directory: {repo}")
        return run_entry(target_for(arguments), arguments, repo)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Run control.py --help for usage.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
