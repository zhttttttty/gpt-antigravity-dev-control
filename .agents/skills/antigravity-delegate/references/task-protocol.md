# Task routing

Preserve `schema_version: 2` for file compatibility and all Core Protocol fields.
Set execution routing with:

```yaml
execution:
  mode: delegated
  adapter: antigravity_cli
  model: configured_default
  context_budget: compact
  report_level: summary
  max_execution_attempts: 2
  escalation: codex_review
```

Missing execution means direct (legacy compatibility). Supported modes are
direct, delegated, approval_required. High risk or any enabled authority flag
requires pre-review even if the planner chose delegated. All delegation requires
worktree: true. Context is capped at 32KB; split/reduce it, never drop acceptance
or risk constraints. Code is read on demand in the worktree, not copied into the
prompt. The single-task lifecycle has no automatic retry or dependency scheduler.
The optional multi-agent launcher has a separate in-run dependency DAG and one
bounded retry; it does not change durable task state or merge authority.

For gated tasks, `route` reports a contract hash. A human creates an approval
YAML outside versioned task files with task_id, contract_sha256,
result: APPROVED, approved_by and evidence (ADR/review reference). Pass its path
to prepare using --approval-file. This records pre-review, not merge approval
and not a cryptographic proof of identity. Keep Core Protocol merge gates intact.
