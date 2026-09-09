---
name: antigravity-delegate
description: "Run the repository's complete Codex-controlled AI development workflow: plan a task, choose direct or local Antigravity execution, prepare an isolated worktree, collect compact evidence, and review the result. Use for bounded implementation or when the user asks Codex to operate the control plane end to end."
---

# Codex-controlled development

Codex owns the plan, task contract, routing decision, independent review, and
final recommendation. Antigravity is only a local implementation subprocess
started by Codex through the repository CLI. Do not introduce Hermes, a remote
orchestrator, a reviewer API, a background scheduler, or automatic merge.

Use the unified entry point from the target repository:

    python .ai/scripts/control.py <command>

The older ai.py and delegate.py files are compatibility modules behind this
entry point. Read [the Codex workflow reference](references/codex-workflow.md)
for the full lifecycle and [the task protocol reference](references/task-protocol.md)
when creating or editing a contract.

## Select an execution mode

- direct: small edits, documentation, configuration, or work where delegation
  overhead is larger than implementation effort.
- delegated: bounded multi-file implementation, tests, or refactors that can
  be checked in an isolated worktree.
- approval_required: architecture, authentication, security, migrations,
  deployment, billing, destructive operations, or any task whose risk/authority
  fields require human approval.

Missing execution defaults to direct. Never upgrade a task's authority or expand
its writable scope to make delegation easier.

## Codex-only operating procedure

1. Read the repository instructions and inspect the task/project artifacts.
2. Create or update a bounded task contract, acceptance checks, and execution
   mode. Validate and route it:

       python .ai/scripts/control.py validate TASK-ID
       python .ai/scripts/control.py route TASK-ID

3. For direct work, use the control-plane state/worktree commands and implement
   within the contract.
4. For delegated work, obtain confirmation immediately before mutation, then:

       python .ai/scripts/control.py prepare TASK-ID --approve
       python .ai/scripts/control.py launch TASK-ID --approve --interactive --executable PATH

   Run the command from a real Codex terminal/PTY so scoped prompts, terms,
   privacy choices, and folder trust remain visible. Do not redirect the
   interactive terminal. Probe/help success proves discovery only, not login.
5. After the executor writes its receipt, collect the compact result:

       python .ai/scripts/control.py status TASK-ID
       python .ai/scripts/control.py collect TASK-ID

   Read the summary first. Inspect full logs only when the summary or review
   identifies a specific question.
6. Codex independently checks the exact diff, receipt, required commands, and
   acceptance evidence. Collection leads to REVIEW, never directly to DONE.
   Write QA/review artifacts, apply the state transition, and leave merge as an
   explicit human action.

## Recovery and full access

If a launch exits without a valid receipt, treat it as NEEDS_ATTENTION:

    python .ai/scripts/control.py diagnose TASK-ID

Inspect the run and worktree before one explicitly confirmed interactive
recovery. Do not loop retries or infer success from exit code 0.

For a disposable trusted worktree only, --full-access --approve may be added to
the interactive launch. It forwards agy's permission-bypass flag; it does not
grant administrator rights, constrain filesystem access, or remove scope,
receipt, review, or merge gates. Never enable it silently.

Use [the receipt protocol reference](references/receipt-protocol.md) for missing
evidence, scope failures, REWORK, BLOCKED tasks, and review handoff. Keep all
runtime logs, context packs, and credentials local; never put secrets in task
contracts or receipts.
