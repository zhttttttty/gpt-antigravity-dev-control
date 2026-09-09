# Quick Start

## 1. Install and inspect

```sh
python -m pip install -r .ai/scripts/requirements-local.txt
python .ai/scripts/control.py status
python .ai/scripts/control.py probe
```

Probe verifies CLI discovery/help, not authentication or a successful model call.

## 2. Create a task

Copy `.ai/templates/task/` to `.ai/tasks/queue/TASK-001/`. Fill its objective,
scope, risk, acceptance evidence, checks, and `execution.mode`.

```sh
python .ai/scripts/control.py validate TASK-001
python .ai/scripts/control.py route TASK-001
```

## 3A. Direct task

Use `direct` when delegation overhead exceeds implementation effort:

```sh
python .ai/scripts/control.py start TASK-001 --worktree
```

Implement within scope, record the Executor Receipt, then independently review
the exact diff and evidence.

## 3B. Delegated task

Use `delegated` for bounded implementation that local agy can verify:

```sh
python .ai/scripts/control.py prepare TASK-001 --approve
python .ai/scripts/control.py launch TASK-001 --approve --interactive --executable /absolute/path/to/agy
python .ai/scripts/control.py status TASK-001
python .ai/scripts/control.py collect TASK-001
```

Collection moves complete evidence to REVIEW, not DONE. Codex independently
checks relevant diffs and tests; a human merges.

## 3C. Approval-required task

High-risk or architecture-authority tasks resolve to `approval_required`. Create
the contract-bound approval artifact described in
[Local Delegation Operations](LOCAL_DELEGATION.md), then pass it to `prepare`.

## 4. Review and close

After writing `receipt.qa.yaml` and `review.yaml`:

```sh
python .ai/scripts/control.py transition TASK-001 DONE
```

Only do this after the required Risk Gates pass. Reconcile project state and
merge explicitly; the controller does neither automatically.
