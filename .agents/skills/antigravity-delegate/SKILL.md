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
4. Prefer `launch TASK-ID --approve --interactive --executable <path>` in a real
   terminal/PTY. It inherits the terminal for scoped approvals; do not redirect
   stdin/stdout. User consent is needed for terms/privacy choices; never select
   data sharing or global permission bypass on their behalf. Exit the executor
   after it writes the receipt. Outer timeout should be at least 1260 seconds.
   Without --interactive the CLI uses print mode, which can silently deny tools.
   A zero exit without a final receipt now returns NEEDS_ATTENTION and exit 2.
   Run `diagnose TASK-ID`. Once the process has stopped, one explicit
   `launch TASK-ID --approve --interactive --recover --executable <path>` is
   permitted; it preserves the first launch's logs. Do not loop retries.
   For a deliberately trusted disposable worktree, add `--full-access` together
   with `--approve`. This forwards agy's `--dangerously-skip-permissions`; it is
   opt-in, recorded, and still subject to receipt, scope and review checks. It
   does not grant Windows administrator rights or sandbox other directories.
5. Run `collect TASK-ID`. Read the compact receipt first. Follow
   [receipt protocol](references/receipt-protocol.md) for missing evidence,
   targeted diffs, review and rework. Do not read full logs by default.

Run from the target repository: `python .ai/scripts/delegate.py <command>`.
The optional skill wrapper accepts `--repo <absolute-repository-path>` and
forwards to that repository's CLI; inspect a new repository before executing it.
Do not merge/release automatically. Full usage values remain unknown unless
measured; this skill does not promise savings.

Keep executor file/search paths inside the exact worktree. Deny requests for
user-home/parent access unrelated to the task and steer back to the contract.
Prefer native file tools on Windows; shell quoting failed during real testing.
After the receipt is written, stop executor exploration: QA and review belong
to Codex. Reports must distinguish interactive-assisted success from unattended
execution, and tests from model-written claims.
