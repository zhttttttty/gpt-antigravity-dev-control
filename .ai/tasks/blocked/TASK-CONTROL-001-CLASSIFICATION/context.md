# Context

## Revision2 rework authorized by user

Implement Sol's strengthened AC-C001/C002/C004 and new AC-C005 in task.yaml. Preserve
all original nine-file boundaries; no permissions or business changes. Attempt1 Luna
confirmed missing/null/empty workspace bypass and security issue accepted using unrelated
cosmetic QA plus arbitrary approval string. Fix by complete fail-closed identity and exact
unique issue_id/text binding plus structured approval and remaining-risk evidence.
The self-repair .agents exception is narrow to this approved task/revision and exact seven
paths, actual controller repository, verified pre_review; explicit protected always wins.
Add independent-style negative cases, not just happy-path tests. One launch only, 1260s.
Read the actual runtime receipt template; status COMPLETE, commands result PASS/exit_code0,
acceptance_id/result PASS/evidence, immutable recorded base and committed head. Do not edit
history/attempt-1 or old runtime receipts. Do not activate this controller or self-approve.

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
