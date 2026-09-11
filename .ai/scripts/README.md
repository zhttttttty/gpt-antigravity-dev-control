# Unified Control CLI

[中文](README.zh-CN.md)

Use one primary entry point:

`python .ai/scripts/control.py check-orchestration` checks project model/role
agreement offline (Python 3.11+). It does not validate runtime model access. See
[Hybrid Orchestration](../../docs/HYBRID_ORCHESTRATION.md).

```sh
python .ai/scripts/control.py status
python .ai/scripts/control.py create TASK-001 --title "Bounded change" --objective "Observable result"
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
`task_data.py` shares structured YAML, approval and evidence validation. Fill and
validate the scaffold, then commit before worktree creation; see
[Control Workflow](../../docs/CONTROL_WORKFLOW.md).

`task.yaml` is the common contract. Its `execution.mode` selects `direct`,
`delegated`, or `approval_required`. Scheduling is explicit and local—there is
no background concurrency service, reviewer API, or auto-merge. Single-task
recovery is explicit; the optional agy multi-agent launcher supports a dependency
DAG and at most one retry, without changing durable task state automatically.
