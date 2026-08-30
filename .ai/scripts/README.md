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

`task.yaml` remains the contract. This helper validates only the stable V2 schema fields used by the template; it is not a general YAML engine or full orchestrator.

For production orchestration, keep the artifact schema but move concurrency, leases, retries and centralized runtime state into a transactional store such as SQLite.
