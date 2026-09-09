# 最小任务示例

[English](README.md)

该目录展示最小完整任务包，位于 .ai/tasks/ 之外，因此不会自动成为活动任务。

本地验证：

    Copy-Item -Recurse examples/minimal-task .ai/tasks/queue/TASK-EXAMPLE
    python .ai/scripts/control.py validate TASK-EXAMPLE
    Remove-Item -Recurse .ai/tasks/queue/TASK-EXAMPLE
