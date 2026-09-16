# 任务上下文

Read route-evidence.md in this task folder for verified diagnostic facts. This is a NEW
bounded route repair, not another old controller attempt. Prior dirty run2 remains untouched.
Real CLI wrapper run_command returns TaskId; poll manage_task status on that exact handle.
Native CommandId requires command_status. No schedule/timers/passive waiting in print.
Use relative searches in command cwd to avoid Windows drive-colon grep parse bug.
Implement only task.yaml exact files and write canonical runtime executor receipt; commit
implementation only after new tests run, no old test reuse, no self-approval or merge.

只包含当前任务所需的上下文。

## 相关架构
- `<组件、不变量或 ADR>`

## 相关文件
- `<路径>`

## 现有行为
`<当前行为>`

## 约束与注意事项
- `<约束>`

## 参考
- `<需求、ADR、Issue 或文档>`
