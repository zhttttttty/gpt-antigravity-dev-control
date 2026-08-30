# V2 Operating Workflow

## Phase 0 — Intake

Human gives an objective, brief, issue, spec or change request.

GPT-5.6 Sol converts it into repository artifacts. Chat is temporary; artifacts are durable.

## Phase 1 — Planning

GPT-5.6 Sol:

1. Reads canonical project/state artifacts.
2. Resolves requirement and architecture implications.
3. Splits work into the smallest independently reviewable task.
4. Sets task risk independently from executor capability.
5. Sets writable/protected scope.
6. Defines objective acceptance evidence.
7. Creates the task under `.ai/tasks/queue/<TASK-ID>/`.

A task cannot become READY without a valid contract.

## Phase 2 — Dispatch

Before execution:

- validate task;
- check dependencies;
- create worktree when required;
- record base commit;
- give Antigravity only the relevant task + architecture context.

Recommended:

```bash
python .ai/scripts/ai.py validate TASK-001
python .ai/scripts/ai.py start TASK-001 --worktree
```

## Phase 3 — Execution

Antigravity:

1. starts from a fresh task context where practical;
2. implements only the task;
3. runs required checks;
4. fills `receipt.executor.yaml`;
5. hands off without self-approval.

If the task contract cannot be satisfied without an architecture or scope change, stop and escalate.

## Phase 4 — Review

GPT-5.6 Sol independently reads:

- immutable/intended task contract;
- exact task diff or commit range;
- executor receipt;
- test evidence;
- architecture and ADRs.

Reviewer checks:

1. objective;
2. scope;
3. acceptance evidence;
4. regression risk;
5. architecture compliance;
6. security;
7. maintainability;
8. unverified claims.

Allowed verdicts:

- `PASS`
- `PASS_WITH_NOTES`
- `REWORK`
- `BLOCKED`

The reviewer should not silently edit the implementation. For REWORK, state concrete findings and either transition the same task back to READY with incremented attempt or create a bounded fix task.

## Phase 5 — Closeout

On PASS/PASS_WITH_NOTES:

- fill `receipt.qa.yaml` and `review.yaml`;
- transition to DONE;
- reconcile `.ai/state/PROJECT_STATE.yaml`;
- update feature ledger / API surface / decisions if durable knowledge changed;
- merge only after required risk gates are satisfied.

## Phase 6 — Resume / Recovery

A new model/session should recover from artifacts:

1. `.ai/state/PROJECT_STATE.yaml`
2. current task folder
3. receipts/review
4. Git branch/worktree and commits
5. relevant ADR/memory

Never require the original conversation to resume safely.
