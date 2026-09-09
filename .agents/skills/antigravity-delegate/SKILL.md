---
name: antigravity-delegate
description: "Delegate bounded coding, review, testing, or repository-analysis tasks to the locally installed Antigravity CLI in an isolated Git worktree. Use when the user explicitly requests Antigravity or when Antigravity delegation is part of the requested workflow; do not use as a silent replacement for ordinary Codex subtasks."
---

# Antigravity delegation controller

Codex owns planning, routing, scope, acceptance, and independent verification. This Skill supplies a deterministic local execution protocol; it is not a remote scheduler and it must not silently replace ordinary Codex subtasks.

## Required protocol

1. Probe the actual executable before every run:

       powershell -NoProfile -ExecutionPolicy Bypass -File .agents/skills/antigravity-delegate/scripts/probe_agy.ps1 -Executable agy -OutputDir .ai/runtime/logs/probe

   Read `capabilities.json`. Do not assume a flag, mode, login state, or agent-list command. The controller routes `direct`, `delegated`, and `approval_required` are not `agy --mode` values. Map full access to omitted `--sandbox`, automatic approval to `--dangerously-skip-permissions`, read-only review to `--mode plan`, and implementation to an advertised edit mode. Full access never expands the task contract.
2. Create isolation with `create_review_worktree.ps1`. Read its JSON path and branch instead of guessing temporary paths. Refuse a dirty base unless the task explicitly allows it.
3. For one task, use the repository control CLI. For several bounded review shards, create a JSON config and call `launch_agents.ps1` with `-MaxConcurrency 2`. Use one full-coverage shard plus one focused shard, then queue the remaining shards. Retry at most once and lower concurrency to one after a concurrent failure.
4. Use a fixed output directory. The launcher writes `sessions.json`, one report per agent, stderr, execution logs, and the capability record. Call `collect_reports.ps1` and read its compact summary before opening full evidence.
5. Apply the independent Codex review contract: verify all P0/P1 paths and lines, run tests, check acceptance and coverage counts, classify findings as confirmed/conditional/hypothesis, and verify the worktree state. Collection is never an automatic merge or DONE transition.
6. Clean only through `cleanup_worktree.ps1`; removal is allowed only when the worktree is clean unless an explicit forced cleanup is approved.

## Repository entry point

For normal task lifecycle operations, use:

    python .ai/scripts/control.py <command>

Read [execution modes](references/execution-modes.md), [review contract](references/review-contract.md), and [failure recovery](references/failure-recovery.md). The existing [task protocol](references/task-protocol.md), [receipt protocol](references/receipt-protocol.md), and [Codex workflow](references/codex-workflow.md) define the repository state machine and compact receipt format.
