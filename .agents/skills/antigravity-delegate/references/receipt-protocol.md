# Compact-first review

Executor writes the existing V2 receipt schema at the absolute path in the
context/launch prompt. Commit implementation only. Do not edit task state files.
The controller owns root task transitions; task copies on the execution branch
are historical contracts, not a second active queue.

`collect` validates identity/revision and required reported evidence, observes
Git changes and protected scope, preserves the full executor receipt and diff
locally, then prints a compact JSON receipt. Counts are required **commands**,
not invented individual test totals. Acceptance is executor-reported; no
independent PASS is generated. A successful collection moves the root task to
REVIEW, not DONE; failed gates move it to BLOCKED.

Read summary, selected diff, relevant tests and evidence only. Independently
verify critical claims. Write V2 review.yaml and receipt.qa.yaml, then use V2
state transitions. Human merge/release remains explicit. Merge implementation
branch only after review; do not replace controller task state with old branch
copies. Reconcile PROJECT_STATE.yaml manually as required by V2.

For REWORK use ai.py transition TASK-ID READY from REVIEW (archives V2 receipts
and increments the contract attempt). For BLOCKED use the documented V2
recovery flow. Commit controller artifacts before preparing a new worktree.
Each preparation consumes the local attempt budget, including failed setups.
At the limit, stop and ask Codex/human to revise the plan; do not delete history
to reset it. No automatic merge, retry, test rerun or remote API call occurs.
