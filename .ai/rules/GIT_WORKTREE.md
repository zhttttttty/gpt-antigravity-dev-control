# Git Worktree Isolation

Each medium/high-risk implementation task should use its own worktree.

Default layout:

```text
repo/
├─ .git/
├─ .worktrees/
│  └─ TASK-001/
└─ ...
```

Default branch:

```text
ai/TASK-001
```

Rules:

1. Create from the intended base commit/branch.
2. Do not rely on uncommitted changes in the base workspace.
3. Record base commit and branch in the executor receipt.
4. Run tests in the same worktree whose diff is reviewed.
5. Review/merge the exact commit range produced by the task.
6. Remove worktree only after evidence is preserved and the task is safely integrated or abandoned.

## Branch-Local State Note

With the lightweight helper, an active task's folder/status transition occurs inside the task worktree/branch. The base branch therefore retains the last integrated task state until that task branch is accepted and integrated. This is intentional for the lightweight V2 template.

V3.1 keeps scheduling explicit and local. Do not run two controllers against the
same task/worktree; inspect and resolve any stale local run record before retrying.
