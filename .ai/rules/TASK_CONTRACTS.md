# 任务契约规则

任务目录是工作和证据的基本单位，必须包含：

```text
<TASK-ID>/
  task.yaml
  brief.md
  context.md
  receipt.executor.yaml
  receipt.qa.yaml
  review.yaml
  rollback.md
```

## 契约不可擅改

执行开始后，执行者不得扩大范围、降低风险、更改权限或削弱验收。
确需修改时，由规划者、审查者或人类明确修订并增加 contract_revision。

## 任务粒度

一个任务只有一个主要结果，可独立验收。
不相关模块、架构迁移与功能实现、多条独立验收路径应拆分处理。
