# Migration from V1 to V2

## Structural Changes

| V1 | V2 |
|---|---|
| `.ai/PROJECT.md` | `.ai/project/PROJECT.md` |
| `.ai/REQUIREMENTS.md` | `.ai/project/REQUIREMENTS.md` |
| `.ai/ARCHITECTURE.md` | `.ai/project/ARCHITECTURE.md` |
| `.ai/ROADMAP.md` | `.ai/project/ROADMAP.md` |
| `.ai/ACCEPTANCE.md` | `.ai/project/ACCEPTANCE.md` |
| `.ai/tasks/TASK-001.md` | `.ai/tasks/queue/TASK-001/task.yaml + brief/context/receipts` |
| `.ai/reports/*` | receipts live with each task |
| free-form task status | folder-backed state machine |
| optional architecture gate prose | structured authority + risk gate |
| shared working tree | task-specific Git worktree |
| executor report Markdown | structured `receipt.executor.yaml` |
| review Markdown | structured QA receipt + `review.yaml` |

## Migration Steps

1. Move project documents into `.ai/project/`.
2. Keep old accepted ADRs under `.ai/decisions/`.
3. Convert unfinished V1 tasks into V2 task folders.
4. Put each unfinished task into the correct state folder.
5. Initialize `.ai/state/PROJECT_STATE.yaml`.
6. Adopt `GEMINI.md` for Antigravity execution.
7. Use `.ai/scripts/ai.py validate` before dispatch.
8. Prefer worktrees for all medium/high risk coding tasks.

Old completed task reports may remain archived; there is no need to rewrite historical evidence.
