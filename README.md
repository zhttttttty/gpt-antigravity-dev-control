# gpt-antigravity-dev-control

A repository-native development control plane for using **GPT-5.6 Sol** as PM / Architect / Planner / Reviewer and **Antigravity / Gemini** as bounded Executor.

## Versions

- **`v2` branch** — protocol/manual workflow: task state machine, structured `task.yaml`, Risk Gates, Receipts, `GEMINI.md`, Git Worktree isolation and review gates.
- **`main` branch** — **V3 Lite**: V2 protocol plus SQLite coordination, leases, automated Antigravity dispatch and GPT-5.6 review orchestration.

## Core model

```text
Human intent
   ↓
GPT-5.6 Sol — plan / architecture
   ↓
V2 task.yaml contract
   ↓
V3 Lite Orchestrator
   ↓
Antigravity — implement / test / receipt
   ↓
GPT-5.6 Sol — independent review
   ↓
PASS / REWORK / BLOCKED / human risk gate
```

Start with [`README_AI_WORKFLOW.md`](README_AI_WORKFLOW.md) and [`.ai/orchestrator/README.md`](.ai/orchestrator/README.md).

The repository, not chat history, is the durable source of truth.
