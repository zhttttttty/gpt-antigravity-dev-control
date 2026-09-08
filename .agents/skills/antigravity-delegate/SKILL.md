---
name: antigravity-delegate
description: Delegate a bounded implementation task in this control-plane repository to local Antigravity CLI, then inspect compact evidence for independent review. Use for explicit local delegation or larger independently testable implementation work, not trivial edits.
---

# Local delegation

Codex owns planning and acceptance; Antigravity implements once. Do not repeat
its implementation. Keep small edits direct. Choose `approval_required` for
architecture, auth, migration, deployment, billing or destructive work.

Use the repository CLI, not a second orchestrator or remote reviewer API:

1. Prepare a V2 task with the optional execution block described in
   [task protocol](references/task-protocol.md). Commit the task and use a clean
   checkout whose HEAD equals its configured base. Run `route TASK-ID`.
2. Run `probe --executable <native-agy-path>` and inspect its help/version logs.
   Existence and help success do not verify login. The shipped print-mode args
   were checked against agy 1.0.10; verify when versions change. Never enable
   permission bypass just to make noninteractive execution work.
3. Obtain user confirmation before `prepare TASK-ID --approve`, and a recorded
   contract-bound pre-review approval for gated work. `prepare` creates an
   isolated worktree and a compact context file without a model call.
4. With user confirmation, run `launch TASK-ID --approve --executable <path>`.
   Let the command run (outer timeout at least 1260 seconds). It uses `-p`,
   not Hermes tool syntax. If authentication/permissions block it, ask the user
   to resolve those interactively. Never interpret process exit as completion.
5. Run `collect TASK-ID`. Read the compact receipt first. Follow
   [receipt protocol](references/receipt-protocol.md) for missing evidence,
   targeted diffs, review and rework. Do not read full logs by default.

Run from the target repository: `python .ai/scripts/delegate.py <command>`.
The optional skill wrapper accepts `--repo <absolute-repository-path>` and
forwards to that repository's CLI; inspect a new repository before executing it.
Do not merge/release automatically. Full usage values remain unknown unless
measured; this skill does not promise savings.
