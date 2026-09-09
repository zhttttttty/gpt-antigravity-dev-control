# Quick Start

`main` uses V3.1 local delegation. It needs Git, Python, PyYAML, and a working
local agy login; it does not need remote reviewer API keys or a scheduler.

## 1. Install and probe

```bash
python -m pip install -r .ai/scripts/requirements-local.txt
python .ai/scripts/delegate.py probe
```

## 2. Initialize project context

Ask Codex to read `AGENTS.md` and initialize `.ai/project/*` plus
`.ai/state/PROJECT_STATE.yaml` for the real project.

## 3. Create and validate a task

Copy `.ai/templates/task/` to `.ai/tasks/queue/TASK-001/`, then fill the scope,
risk, acceptance criteria, tests, and `execution` routing block.

```bash
python .ai/scripts/ai.py validate TASK-001
python .ai/scripts/delegate.py route TASK-001
```

## 4. Delegate locally

```bash
python .ai/scripts/delegate.py prepare TASK-001 --approve
python .ai/scripts/delegate.py launch TASK-001 --approve --interactive --executable /absolute/path/to/agy
python .ai/scripts/delegate.py status TASK-001
python .ai/scripts/delegate.py collect TASK-001
```

`collect` validates the branch, ancestry, scope, receipt, reported checks, and
acceptance evidence. It moves a complete result to REVIEW, not DONE. Codex must
independently inspect the relevant diff/tests; merge remains a human action.

For a disposable trusted worktree, add `--full-access` to the interactive launch.
This requires `--approve` and only skips agy confirmations.

See [Local Delegation](LOCAL_DELEGATION.md) for approval files, recovery, compact
receipts, and failure handling.

## 5. Manual V2-compatible flow

Tasks that should not be delegated can use the existing helper directly:

```bash
python .ai/scripts/ai.py start TASK-001 --worktree
python .ai/scripts/ai.py transition TASK-001 REVIEW
python .ai/scripts/ai.py transition TASK-001 DONE
```

## 6. High-risk work

High-risk tasks remain fail-closed. Required review artifacts and human approval
must exist before the final gate can pass.
