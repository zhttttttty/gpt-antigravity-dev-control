# Helper CLI

Pure-Python helper; no third-party package is required.

```bash
python .ai/scripts/ai.py status
python .ai/scripts/ai.py validate TASK-001
python .ai/scripts/ai.py start TASK-001 --worktree
python .ai/scripts/ai.py transition TASK-001 REVIEW
python .ai/scripts/ai.py transition TASK-001 DONE
python .ai/scripts/ai.py worktree-remove TASK-001
```

`task.yaml` remains the contract. This helper validates only the stable V2 schema fields used by the template; it is not a general YAML engine or scheduler.

V3.1 local delegation is provided by `delegate.py`. It intentionally keeps
execution explicit and local, with no background concurrency service.
