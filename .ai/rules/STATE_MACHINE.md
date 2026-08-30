# Task State Machine

Canonical state is represented by **both** the task folder location and `task.yaml.status`. They must agree.

```text
READY      -> IN_PROGRESS | BLOCKED
IN_PROGRESS-> REVIEW      | BLOCKED
REVIEW     -> DONE        | READY | BLOCKED
BLOCKED    -> READY
DONE       -> ARCHIVED
```

Folder mapping:

- READY → `.ai/tasks/queue/`
- IN_PROGRESS → `.ai/tasks/active/`
- REVIEW → `.ai/tasks/review/`
- BLOCKED → `.ai/tasks/blocked/`
- DONE → `.ai/tasks/done/`
- ARCHIVED → `.ai/tasks/archive/`

A REWORK verdict transitions the same task from REVIEW back to READY and increments `attempt`. For large or logically distinct remediation, create a new fix task instead.
