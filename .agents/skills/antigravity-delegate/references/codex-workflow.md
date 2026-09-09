# Codex workflow reference

This reference describes the end-to-end operation of the repository skill. All
control-plane commands are issued by Codex in the target repository; the local
agy process is an implementation child process, not a second controller.

## Starting a task

1. Read AGENTS.md, .ai/config.yaml, project architecture, current project
   state, and the requested task context.
2. Copy .ai/templates/task/ into .ai/tasks/queue/TASK-ID/.
3. Fill objective, writable/protected scope, risk, checks, acceptance evidence,
   isolation, and execution routing.
4. Commit the task contract before preparing a worktree.
5. Run:

       python .ai/scripts/control.py validate TASK-ID
       python .ai/scripts/control.py route TASK-ID

## Direct execution

Use direct mode for small or immediately reviewable changes:

    python .ai/scripts/control.py start TASK-ID --worktree

The implementer writes the executor receipt, runs the required checks, and
returns control to Codex for review. State transitions and merge remain explicit.

## Local delegation

Use delegated mode for bounded work with clear automated checks:

    python .ai/scripts/control.py prepare TASK-ID --approve
    python .ai/scripts/control.py launch TASK-ID --approve --interactive --executable PATH
    python .ai/scripts/control.py status TASK-ID
    python .ai/scripts/control.py collect TASK-ID

Prepare creates one isolated worktree, records the base commit and contract
digest, and writes a compact context pack. Launch starts agy in that worktree.
Collect checks ancestry, branch state, changed-file scope, receipt identity,
reported checks, and acceptance evidence.

For high-risk or architecture-authority work, create the contract-bound approval
file required by the task protocol and pass --approval-file to prepare. This
approval is not merge approval.

## Review and closeout

The executor's COMPLETE is evidence for review, not an acceptance verdict.
Codex reads the compact receipt first, then targeted diffs and test output.
Write receipt.qa.yaml and review.yaml with a verdict of PASS,
PASS_WITH_NOTES, REWORK, or BLOCKED.

Only after the required gates pass:

    python .ai/scripts/control.py transition TASK-ID DONE

The controller does not merge branches, call a reviewer model, or update
project-level knowledge automatically.

## Continue/resume behavior

When the user says “continue”, inspect the task folder, status, latest run
record, worktree, and Git state before taking another action. Resume the first
unfinished phase; do not repeat a successful launch or create a second controller
for the same task. If a run is NEEDS_ATTENTION, diagnose it and require one
explicit recovery confirmation.
