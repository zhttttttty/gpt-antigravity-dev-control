# V2 vs V3.1 Local Delegation

| Dimension | V2 Manual | V3.1 Local |
|---|---|---|
| Protocol | Structured `task.yaml` | Same V2 protocol plus execution routing |
| Dispatch | Human opens executor manually | Confirmed local `agy` launch |
| Worktree | Supported | Required and controller-managed for delegation |
| Result transfer | Receipts written manually | Compact receipt plus retained local logs |
| Review | Human-triggered | Codex-triggered after collection; still independent |
| Recovery | Files and Git | Files/Git plus bounded local run records |
| High-risk approval | Human | Human; never bypassed |
| Merge | Human | Human |
| Remote API keys | None required | None required by the controller |
| Background/parallel scheduler | No | No |
| Complexity | Lowest | Low to moderate |

## Recommendation

- Use V2-style direct/manual execution for small edits and tasks where delegation
  overhead exceeds implementation effort.
- Use V3.1 for bounded multi-file changes, test work, and refactors that benefit
  from separating Codex planning/review from Antigravity implementation.
- Use `approval_required` routing and existing Risk Gates for architecture,
  security, migration, deployment, or destructive changes.

The former V3 Lite remote concurrency experiment is archived on
[`archive/v3-lite`](https://github.com/zhttttttty/gpt-antigravity-dev-control/tree/archive/v3-lite)
and is not part of `main`.
