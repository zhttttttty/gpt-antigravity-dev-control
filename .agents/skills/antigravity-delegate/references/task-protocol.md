# Task routing

Preserve schema_version 2 and all existing V2 fields. Add:

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
prompt. No automatic retries or dependency scheduler in phase one.

For gated tasks, `route` reports a contract hash. A human creates an approval
YAML outside versioned task files with task_id, contract_sha256,
result: APPROVED, approved_by and evidence (ADR/review reference). Pass its path
to prepare using --approval-file. This records pre-review, not merge approval
and not a cryptographic proof of identity. Keep V2 merge gates intact.
