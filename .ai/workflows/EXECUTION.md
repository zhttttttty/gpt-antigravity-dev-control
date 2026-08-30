# Execution Workflow

1. Validate task contract.
2. Create/enter task worktree when required.
3. Record base commit/workspace.
4. Start fresh executor context.
5. Read only relevant context.
6. Implement the smallest compliant change.
7. Run required checks.
8. Fill executor receipt.
9. Transition to REVIEW.
10. Stop; do not self-approve or merge protected branch.
