# Risk Gates

Risk is based on potential impact, not model strength or confidence.

## Low

Typical: local bug fix, isolated refactor, documentation, non-critical test improvement.

Required:

- bounded scope check;
- executor receipt;
- targeted checks when available;
- independent GPT-5.6 review;
- QA receipt.

Worktree: recommended.

## Medium

Typical: user-visible feature, cross-file change, integration behavior, dependency use, meaningful regression potential.

Required:

- isolated worktree;
- executor receipt;
- required automated tests when available;
- regression check;
- independent GPT-5.6 review;
- QA receipt.

## High

Typical: schema/migration, auth/security, billing, destructive data behavior, deployment topology, breaking API, major dependency/framework change.

Required before/for merge:

- isolated worktree;
- explicit architecture/risk pre-review;
- ADR where architecture-gated;
- executor receipt;
- automated tests and regression evidence when available;
- rollback plan;
- independent GPT-5.6 review;
- cross-family second review **or** documented human waiver;
- explicit human merge approval.

The executor cannot lower risk. A reviewer/planner may raise risk at any time.
