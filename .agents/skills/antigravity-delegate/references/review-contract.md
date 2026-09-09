# Review contract

Antigravity output is evidence, not an acceptance decision. Every run must leave a compact report in the caller-selected output directory and keep full stdout, stderr, and CLI logs beside it.

The report must identify:

- task name, worktree, base commit, head commit, and final status;
- changed files and tests (`passed`, `failed`, and `not_run`);
- acceptance checks with `passed` and `total` counts;
- coverage counts: text files semantically read plus non-text files type/size/hash/use checked;
- known issues and paths to full logs.

Codex independently verifies every P0/P1 finding with `rg -n -C` or source reads, checks that paths and line numbers still match, runs the repository test command, and verifies the worktree state. Mark evidence as `CONFIRMED`, `CONDITIONAL`, or `HYPOTHESIS`; merge duplicates and downgrade findings whose severity depends on deployment or data assumptions. Collection therefore leads to `REVIEW`, never directly to `DONE` or merge.

## Launcher contract

`launch_agents.ps1` accepts a JSON object with a `tasks` array. Each task has a
stable `name`, an absolute `worktree`, a bounded `prompt`, and optionally
`mode` (`plan` or `accept-edits`), `depends_on`, `max_retries`,
`timeout_seconds`, `auto_approve`, `effort`, `model`, and `attempt`.
Recommended shards are `full`, `backend`, `frontend`, and `opsdocs`. The
dependency DAG, concurrency limit, and Worktree writer lock are defined in the
[coordination protocol](coordination-protocol.md).
