# Current limitations

[中文](LIMITATIONS.zh-CN.md)

The control plane is intentionally local and human-supervised rather
than a distributed automation platform.

- A working local agy installation, login, and tool permissions are required.
- Probe/help success does not prove authentication or successful model execution.
- Worktrees isolate Git state but are not an operating-system security sandbox.
- Scope validation is post-execution and cannot prevent all out-of-scope access.
- The controller does not automatically merge, independently rerun tests, or
  declare a task DONE.
- Single-task recovery is explicit. The local multi-agent launcher permits only
  one automatic retry and then stops; there is no unattended retry loop.
- Runtime cleanup, crash-safe multi-file transactions, automatic backup, metrics
  ingestion, and unattended batch scheduling are not implemented. Local parallel
  dispatch is limited to two agents and does not coordinate remote workers.
- Full-access mode skips agy confirmations and therefore belongs only in a
  disposable trusted worktree; it does not grant administrator rights.
- Compact receipts report observed Git state and executor claims. Codex still
  needs to inspect the relevant diff and independently verify acceptance.
- No fixed token, time, or cost reduction is guaranteed. Measure real tasks.

Detailed operational failure handling is in [Local Delegation](LOCAL_DELEGATION.md).
