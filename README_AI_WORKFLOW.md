# GPT-5.6 Sol × Antigravity AI Development Control Plane — V2

This template is a repository-native control plane for a two-model software-development workflow:

- **GPT-5.6 Sol** — Product PM, Architect, Planner, Reviewer, acceptance owner.
- **Antigravity / Gemini** — Executor, Developer, Test Agent, evidence producer.
- **Human** — final authority for scope, architecture and high-risk approval.

The repository — not chat history — is the durable source of truth.

## What V2 Adds

Compared with V1, V2 adds:

1. A folder-backed **task state machine**.
2. Structured **`task.yaml` contracts**.
3. **Risk Gates** (`low`, `medium`, `high`).
4. Structured **Executor and QA Receipts**.
5. A dedicated **`GEMINI.md`** adapter for Antigravity.
6. **Git Worktree isolation** for implementation tasks.
7. Explicit **role authority** and architecture escalation.
8. **Fresh-context-per-task** execution guidance.
9. Durable **project state, memory, ADRs and evidence**.
10. A small pure-Python helper: `.ai/scripts/ai.py`.

## Core Workflow

```text
Human intent
   ↓
GPT-5.6 Sol — plan / architecture
   ↓
READY task contract
   ↓
Risk Gate + Worktree
   ↓
Antigravity — implement / test
   ↓
Executor Receipt
   ↓
GPT-5.6 Sol — independent review
   ↓
QA Receipt + verdict
   ├─ PASS → DONE
   ├─ PASS_WITH_NOTES → DONE
   ├─ REWORK → READY
   └─ BLOCKED → BLOCKED
```

## Quick Start

1. Copy this template into the repository root.
2. Ask GPT-5.6 Sol to initialize `.ai/project/*` and `.ai/state/PROJECT_STATE.yaml`.
3. GPT-5.6 Sol creates a task folder in `.ai/tasks/queue/` using `.ai/templates/task/`.
4. Validate it:

```bash
python .ai/scripts/ai.py validate TASK-001
```

5. Start it and create an isolated worktree:

```bash
python .ai/scripts/ai.py start TASK-001 --worktree
```

6. Open the task worktree in Antigravity and tell it to read `GEMINI.md` and the assigned task.
7. Antigravity implements, tests and fills `receipt.executor.yaml`.
8. Move the task to review:

```bash
python .ai/scripts/ai.py transition TASK-001 REVIEW
```

9. GPT-5.6 Sol reviews the exact diff/evidence and fills `receipt.qa.yaml` / `review.yaml`.
10. Close the task:

```bash
python .ai/scripts/ai.py transition TASK-001 DONE
```

## Canonical Source

`.ai/` is canonical. Top-level `AGENTS.md` and `GEMINI.md` are adapters for tools and humans.

Priority when files conflict:

```text
Human instruction
> accepted ADR
> .ai/project/ARCHITECTURE.md
> task.yaml contract
> project requirements
> roadmap / convenience docs
> chat history
```

## Directory Layout

```text
project/
├─ AGENTS.md
├─ GEMINI.md
├─ README_AI_WORKFLOW.md
└─ .ai/
   ├─ config.yaml
   ├─ WORKFLOW.md
   ├─ MIGRATION_V1_TO_V2.md
   ├─ INSPIRATION.md
   ├─ project/
   ├─ agents/
   ├─ rules/
   ├─ workflows/
   ├─ tasks/
   │  ├─ queue/
   │  ├─ active/
   │  ├─ review/
   │  ├─ blocked/
   │  ├─ done/
   │  └─ archive/
   ├─ templates/task/
   ├─ examples/
   ├─ decisions/
   ├─ memory/
   ├─ state/
   └─ scripts/
```

## Recommended Operating Rule

**One task = one bounded change set = one isolated worktree = one executor receipt = one independent review.**

Do not let the executor redefine its own contract or architecture.
