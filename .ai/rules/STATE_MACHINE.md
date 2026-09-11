# 任务状态机

规范状态由主控任务目录位置和 `task.yaml.status` 共同表示，两者必须一致。

```text
READY       -> IN_PROGRESS | BLOCKED
IN_PROGRESS -> REVIEW      | BLOCKED
REVIEW      -> DONE        | READY | BLOCKED
BLOCKED     -> READY
DONE        -> ARCHIVED
```

| 状态 | 目录 |
|---|---|
| READY | `.ai/tasks/queue/` |
| IN_PROGRESS | `.ai/tasks/active/` |
| REVIEW | `.ai/tasks/review/` |
| BLOCKED | `.ai/tasks/blocked/` |
| DONE | `.ai/tasks/done/` |
| ARCHIVED | `.ai/tasks/archive/` |

REWORK 将同一任务从 REVIEW 迁回 READY，归档旧回执并增加 attempt。
较大或逻辑独立的修复应另建任务。
