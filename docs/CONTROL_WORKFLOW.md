# Unified Local Control Workflow

[中文](CONTROL_WORKFLOW.zh-CN.md)

## Roles

- **Codex**: requirements, architecture, task contracts, routing, and independent review.
- **Antigravity / Gemini**: bounded local implementation and execution evidence.
- **Human**: high-risk approval and final merge authority.

## Phase 1 — Plan

Create the smallest independently reviewable task. Define writable/protected
scope, risk, acceptance evidence, checks, and one of the three execution modes.

```sh
python .ai/scripts/control.py validate TASK-001
python .ai/scripts/control.py route TASK-001
```

## Phase 2 — Execute

For `direct`, start the task and implement within its contract:

```sh
python .ai/scripts/control.py start TASK-001 --worktree
```

For `delegated`, prepare and launch local agy:

```sh
python .ai/scripts/control.py prepare TASK-001 --approve
python .ai/scripts/control.py launch TASK-001 --approve --interactive
python .ai/scripts/control.py collect TASK-001
```

For `approval_required`, bind human approval to the current contract digest
before preparation. Any scope/architecture change requires a revised contract.

## Phase 3 — Review

Codex independently reads the intended contract, exact commit range/diff,
Executor Receipt, test evidence, architecture, and ADRs. Allowed verdicts are
`PASS`, `PASS_WITH_NOTES`, `REWORK`, and `BLOCKED`.

The reviewer does not silently implement fixes. REWORK identifies bounded
findings and preserves the earlier attempt evidence.

## Phase 4 — Close

After required QA/review artifacts and Risk Gates exist:

```sh
python .ai/scripts/control.py transition TASK-001 DONE
```

Reconcile `.ai/state/PROJECT_STATE.yaml`, preserve durable evidence, and merge
the reviewed commit explicitly.

## Resume and recovery

A fresh session reconstructs state from:

1. `.ai/state/PROJECT_STATE.yaml`;
2. the current task folder and contract;
3. receipts/review;
4. Git branches, worktrees, and commits;
5. relevant architecture decisions;
6. local delegation records/logs when applicable.

The original chat is never required for safe recovery.
