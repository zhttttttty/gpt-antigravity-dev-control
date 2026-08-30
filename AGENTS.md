# Agent Control Plane — Generic Adapter

> Canonical source: `.ai/`. If this file conflicts with `.ai/`, follow `.ai/`.

## Roles

- **GPT-5.6 Sol**: PM / Architect / Planner / Reviewer / acceptance owner.
- **Antigravity / Gemini**: Executor / Developer / Test Agent / evidence producer.
- **Human**: final authority.

## Required Reading

Before work, read:

1. `AGENTS.md`
2. `.ai/config.yaml`
3. `.ai/project/PROJECT.md`
4. `.ai/project/REQUIREMENTS.md`
5. `.ai/project/ARCHITECTURE.md`
6. `.ai/project/ACCEPTANCE.md`
7. `.ai/state/PROJECT_STATE.yaml`
8. the assigned task folder
9. relevant ADRs and code/tests

## Non-Negotiable Rules

1. The executor implements **exactly one task contract** at a time.
2. The executor may not rewrite `task.yaml` to widen its own authority.
3. Architecture-gated changes require GPT-5.6 Sol / human approval first.
4. A claim is not evidence. Record commands, results and changed files.
5. `COMPLETE` from the executor is not `PASS` from the reviewer.
6. High-risk work requires the high-risk gate defined in `.ai/rules/RISK_GATES.md`.
7. Prefer a fresh executor context for each task/attempt.
8. Use Git worktree isolation when `task.yaml` requires it.
9. If required evidence is unavailable, fail closed: record `NOT_RUN`, `UNKNOWN` or `BLOCKED`; do not infer success.
10. Important decisions must be written to repository artifacts, not left only in chat.

## Architecture Gate

If implementation requires changing any of the following without explicit authorization, stop:

- database schema / migration strategy;
- public API contract;
- authentication / authorization;
- security or secret boundary;
- core framework / runtime / storage engine;
- deployment topology;
- new external service;
- persistent state semantics;
- major dependency;
- broad cross-module rewrite;
- backward compatibility policy.

Return:

```text
ARCHITECTURE_DECISION_REQUIRED
Task: <TASK-ID>
Reason: ...
Options: ...
Recommendation: ...
Impact: ...
```

## Task State Machine

```text
READY(queue)
   ↓
IN_PROGRESS(active)
   ↓
REVIEW(review)
   ├─ PASS / PASS_WITH_NOTES → DONE(done)
   ├─ REWORK → READY(queue)
   └─ BLOCKED → BLOCKED(blocked)

BLOCKED → READY
DONE → ARCHIVED(archive)
```

## Definition of Done

A task is DONE only if:

- objective is satisfied;
- acceptance criteria have evidence;
- required gates pass;
- scope is clean;
- no unauthorized architecture change occurred;
- executor receipt exists;
- reviewer verdict is `PASS` or `PASS_WITH_NOTES`;
- project state is reconciled.
