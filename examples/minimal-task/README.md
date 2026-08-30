# Minimal Task Example

This folder demonstrates the smallest complete V2 task bundle. It is intentionally outside `.ai/tasks/` so it does not become active work.

To test it locally:

```bash
cp -R examples/minimal-task .ai/tasks/queue/TASK-EXAMPLE
python .ai/scripts/ai.py validate TASK-EXAMPLE
rm -rf .ai/tasks/queue/TASK-EXAMPLE
```

On Windows PowerShell, use `Copy-Item -Recurse` / `Remove-Item -Recurse` instead.
