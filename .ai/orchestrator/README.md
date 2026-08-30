# V3 Lite Orchestrator

V3 Lite automates the V2 protocol; `.ai/` remains canonical.

## Setup

```bash
python -m pip install -r .ai/orchestrator/requirements.txt
python .ai/orchestrator/orchestrator.py init
python .ai/orchestrator/orchestrator.py doctor
```

Set `OPENAI_API_KEY` and `GEMINI_API_KEY`. For private repositories also set `ANTIGRAVITY_GITHUB_PAT`.

Run one task:

```bash
python .ai/orchestrator/orchestrator.py once TASK-001
```

Run queued tasks until idle:

```bash
python .ai/orchestrator/orchestrator.py loop --until-idle
```

High-risk approval remains human-controlled:

```bash
python .ai/orchestrator/orchestrator.py approve TASK-017 --by "<name>"
```

The SQLite database is coordination state only; task contracts, receipts and Git history remain durable project truth.
