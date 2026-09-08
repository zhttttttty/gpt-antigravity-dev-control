# Recommended: V3.1 local delegation

Start with [Local Delegation](LOCAL_DELEGATION.md). It needs Git, Python, PyYAML
and a working local agy login; no OpenAI reviewer API key. The guide below
documents the retained V2 and optional experimental V3 Lite paths.

# Quick Start

## 1. Choose a mode

Use branch `v2` for manual orchestration. Use `main` for V3 Lite automation.

## 2. Initialize project context

Ask GPT-5.6 Sol to read `AGENTS.md` and initialize `.ai/project/*` plus `.ai/state/PROJECT_STATE.yaml` for your real project.

## 3. Create a task

Copy `.ai/templates/task/` to `.ai/tasks/queue/TASK-001/` and let GPT-5.6 Sol fill the contract.

Validate:

```bash
python .ai/scripts/ai.py validate TASK-001
```

## 4A. V2 manual execution

```bash
python .ai/scripts/ai.py start TASK-001 --worktree
```

Open the task worktree in Antigravity. Tell it to read `AGENTS.md`, `GEMINI.md` and the assigned task. After implementation and tests, it fills `receipt.executor.yaml`.

Move to review and ask GPT-5.6 Sol to independently review the diff and evidence:

```bash
python .ai/scripts/ai.py transition TASK-001 REVIEW
```

After `PASS` / `PASS_WITH_NOTES`:

```bash
python .ai/scripts/ai.py transition TASK-001 DONE
```

## 4B. V3 Lite automated execution

```bash
python -m pip install -r .ai/orchestrator/requirements.txt
python .ai/orchestrator/orchestrator.py init
```

Set required API keys, then:

```bash
python .ai/orchestrator/orchestrator.py loop --until-idle
```

The Orchestrator discovers READY tasks, dispatches Antigravity, gathers evidence and invokes GPT-5.6 review.

## 5. High-risk work

High-risk tasks remain fail-closed. Human approval is required before the final gate can pass.
