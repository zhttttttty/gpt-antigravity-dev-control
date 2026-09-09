# Unified Operating Workflow

[中文](WORKFLOW.zh-CN.md)

## 1. Plan

Codex reads canonical project/state artifacts, defines one bounded task, selects
risk and authority, sets scope and acceptance evidence, and chooses
`execution.mode`.

```sh
python .ai/scripts/control.py validate TASK-001
python .ai/scripts/control.py route TASK-001
```

## 2. Execute

- `direct`: Codex or a human implements under the task contract.
- `delegated`: local agy implements in the prepared task worktree.
- `approval_required`: contract-bound approval precedes local delegation.

```sh
# direct
python .ai/scripts/control.py start TASK-001 --worktree

# delegated
python .ai/scripts/control.py prepare TASK-001 --approve
python .ai/scripts/control.py launch TASK-001 --approve --interactive
python .ai/scripts/control.py collect TASK-001
```

The executor modifies only writable scope, runs required checks, writes the
Executor Receipt, and never self-approves or merges.

## 3. Review

Codex independently reviews the exact diff/commit range and evidence. Allowed
verdicts are `PASS`, `PASS_WITH_NOTES`, `REWORK`, and `BLOCKED`. Missing evidence
does not become an inferred PASS.

## 4. Close

After QA/review artifacts and Risk Gates pass:

```sh
python .ai/scripts/control.py transition TASK-001 DONE
```

Reconcile project state and merge explicitly. Preserve attempt evidence for
REWORK. A new session resumes from repository artifacts and Git, not chat memory.
