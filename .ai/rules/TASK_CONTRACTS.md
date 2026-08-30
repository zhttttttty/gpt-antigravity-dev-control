# Task Contract Rules

The task folder is the unit of work and evidence.

## Required Files

```text
<TASK-ID>/
├─ task.yaml
├─ brief.md
├─ context.md
├─ receipt.executor.yaml
├─ receipt.qa.yaml
├─ review.yaml
└─ rollback.md
```

## Contract Immutability

After execution begins, the executor may not widen scope, lower risk, change authority flags or weaken acceptance criteria.

If the contract must change, planner/reviewer/human must explicitly revise it and increment the task `contract_revision`.

## Task Sizing

A good task has one primary outcome and is independently reviewable.

Split tasks that combine unrelated modules, architecture migration + feature implementation, or several independent acceptance paths.
