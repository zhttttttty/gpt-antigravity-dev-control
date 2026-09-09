# Failure recovery

Recover from the first concrete failure instead of looping:

1. Invalid or unsupported argument: stop, re-run the capability probe, and remap only to advertised flags.
2. Worktree path mismatch: discard guessed paths and read the path returned by `git worktree list --porcelain` or `create_review_worktree.ps1`.
3. Permission or terms prompt: keep the session interactive; do not infer login or consent from a successful help command.
4. Concurrent session failure: the launcher retries at most once, reduces effective concurrency to one, and preserves the first attempt's logs. A second failure is final.
5. Truncated stdout or missing report: use the fixed report path and session registry; never treat an exit code alone as success.
6. Dirty cleanup: refuse removal without explicit `-Force`; inspect the diff before any forced cleanup.

Every retry receives a new attempt number and keeps the previous execution log. Do not start a second controller for the same task, silently replace Antigravity with an ordinary Codex subtask, or merge without the independent review contract.
