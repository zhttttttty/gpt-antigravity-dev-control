# Context

Baseline controller commit is `e55f40f` in an ASCII-path clone of the named control repo;
the original control repository remains unmerged. Current `delegate.collect()` blocks any
known_issues/unverified_items and overwrites receipt.workspace after collection. Current
`task_data.done_errors()` requires unverified_items empty. `antigravity_cli.diagnose()`
can classify a recovered-auth session as AUTH_REQUIRED from an earlier warning.

Protocol invariant: `status: COMPLETE`, required command `result: PASS` with exit_code 0,
AC `acceptance_id/result: PASS`, and observed workspace/base/head must match. Structured
optional NOT_RUN must retain exact optional command and nonempty reason. Reported issues
must survive into QA; only independent evidence review and risk-owner approval can mark
accepted residual risk. Required gaps, architecture deviations, scope violations and
unreviewed/blocking issues remain blockers. Do not accept legacy malformed fields.

The user authorized this repair and one further business rework attempt per task, but not
automatic merging. Child Antigravity auto-approval is scoped to isolated worktrees only;
it does not relax the task contract or human acceptance gates.
