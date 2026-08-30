# Closeout Workflow

For PASS / PASS_WITH_NOTES:

1. confirm required human approval for high-risk tasks;
2. transition task to DONE;
3. update `PROJECT_STATE.yaml`;
4. update ROADMAP status;
5. update durable memory/ADR/API surface when relevant;
6. merge/integrate according to repository policy;
7. archive later when no longer needed in active history.

For REWORK:

- increment attempt;
- preserve prior receipts/findings;
- transition back to READY, or create a separate fix task if remediation is independently reviewable.
