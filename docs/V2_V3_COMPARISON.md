# V2 vs V3 Lite

| Dimension | V2 | V3 Lite |
|---|---|---|
| Protocol | Structured `task.yaml` | Same V2 protocol |
| Dispatch | Human-triggered | Automated |
| Review trigger | Human-triggered | Automated |
| Worktree | Supported | Automated/managed |
| Task state | Repository folders | Repository folders + SQLite coordination |
| REWORK history | Preserved | Preserved + auto-loop |
| Multi-task throughput | Manual scheduling | Orchestrator scheduling |
| Failure recovery | Files/Git | Files/Git + runtime state |
| High-risk approval | Human | Human; never bypassed |
| Complexity | Low | Moderate |

## Recommendation

- Use V2 when transparency and minimal moving parts matter more than automation.
- Use V3 Lite when a project has repeated task/review loops or enough tasks that manual dispatch becomes the bottleneck.
- Do not add heavier infrastructure until real usage demonstrates a need.
