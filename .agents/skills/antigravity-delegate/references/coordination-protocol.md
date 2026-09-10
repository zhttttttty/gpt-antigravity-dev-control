# Multi-agent coordination protocol

[中文](coordination-protocol.zh-CN.md)

Codex is the coordinator. Antigravity agents do not chat with each other; they
coordinate through explicit dependencies, shared Git state when intentionally
serialized, and report paths recorded in `sessions.json`.

## Configuration

`launch_agents.ps1` accepts a JSON object with a `tasks` array:

    {
      "tasks": [
        {
          "name": "full",
          "worktree": "C:/repo-review",
          "mode": "plan",
          "prompt": "Review the full repository",
          "max_retries": 0
        },
        {
          "name": "backend",
          "worktree": "C:/repo-backend",
          "mode": "accept-edits",
          "prompt": "Implement the backend contract",
          "depends_on": ["full"],
          "timeout_seconds": 1260
        }
      ]
    }

Optional task fields are `depends_on`, `max_retries` (zero or one),
`timeout_seconds`, `auto_approve`, `effort`, `model`, and initial `attempt`.

## Scheduling invariants

- The default concurrency is two and the hard maximum is four.
- Requests above two start with two agents and ramp to the target only after the
  first successful completion. Large read-only/document workloads may use three
  or four. Workloads containing writers are capped at two unless
  `-AllowHighWriteConcurrency` is explicit; independent writer Worktrees remain
  required.
- A user-local exclusive lock prevents two launcher processes from consuming
  the same agy capacity at once.
- Dependencies form a validated DAG and determine `planned_wave` ordering.
- Read-only `plan` agents may share a worktree concurrently. If either agent can
  write, that worktree is exclusive until the process exits.
- A failed or timed-out task retries at most once. The first failure immediately
  aborts ramp-up and lowers effective concurrency to one for the rest of the run.
- stdout and stderr are drained asynchronously to prevent pipe-buffer deadlock.
- A dependent task receives the stable paths of completed dependency reports.

Use separate worktrees for independent implementation shards. Use the same
worktree plus `depends_on` only when later work must see earlier changes and
serial execution is intended. No task automatically merges another branch.

## Outputs

Each attempt has separate report, execution log, and stderr files. The latest
report is also copied to `<name>.md`. `sessions.json` records the dependency
graph, attempts, status, timeout, prompt hash, and effective concurrency.
`collect_reports.ps1` writes `summary.json` and `handoff.md`; Codex then performs
the independent verification and merges duplicate findings.
