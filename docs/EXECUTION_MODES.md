# Execution Modes

[中文](EXECUTION_MODES.zh-CN.md)

Execution routing is part of the task contract. It lets the planner choose the
cheapest execution path while preserving the same evidence and review rules.

```yaml
execution:
  mode: direct
  adapter: antigravity_cli
  model: configured_default
  context_budget: compact
  report_level: summary
  max_execution_attempts: 2
  escalation: codex_review
```

## `direct`

Best for small changes, immediate reasoning work, and tasks where coordination
cost would exceed implementation cost. Use the Core Protocol state machine,
receipts, evidence, and review exactly as for delegated work.

## `delegated`

Best for independently reviewable multi-file implementation, tests, and bounded
refactors. The local controller creates an isolated worktree, starts agy, retains
full evidence locally, and collects a compact receipt.

## `approval_required`

Used for high risk or architecture authority. Routing automatically upgrades a
task when its risk/authority fields require approval. A contract-bound approval
artifact is required before preparation; review and human merge remain separate.

## Shared guarantees

| Concern | All modes |
|---|---|
| Contract | Structured `task.yaml` |
| Task state | Repository folders |
| Risk controls | Risk Gate rules |
| Evidence | Executor/QA Receipts and review artifact |
| REWORK | Previous attempt evidence preserved |
| Acceptance | Independent review |
| Merge | Human-controlled |
