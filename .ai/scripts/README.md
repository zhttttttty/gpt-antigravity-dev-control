# Unified Control CLI

[中文](README.zh-CN.md)

Use one primary entry point:

```sh
python .ai/scripts/control.py status
python .ai/scripts/control.py validate TASK-001
python .ai/scripts/control.py route TASK-001
python .ai/scripts/control.py prepare TASK-001 --approve
python .ai/scripts/control.py launch TASK-001 --approve --interactive
python .ai/scripts/control.py collect TASK-001
python .ai/scripts/control.py transition TASK-001 DONE
```

`control.py` routes Core Protocol operations to `ai.py` and local delegation
operations to `delegate.py`. Those two files remain stable compatibility entry
points and internal modules; callers no longer need to choose between them.

`task.yaml` is the common contract. Its `execution.mode` selects `direct`,
`delegated`, or `approval_required`. Scheduling is explicit and local—there is
no background concurrency service, reviewer API, automatic retry, or auto-merge.
