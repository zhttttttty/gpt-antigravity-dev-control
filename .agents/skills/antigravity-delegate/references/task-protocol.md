# 任务路由

保留 `schema_version: 2` 与核心字段，确保文件兼容。路由示例：

```yaml
execution:
  mode: delegated
  adapter: antigravity_cli
  model: configured_default
  context_budget: compact
  report_level: summary
  max_execution_attempts: 2
  escalation: codex_review
```

缺少 execution 时按旧版 direct 处理。支持 direct、delegated、approval_required。
高风险或任一 authority 标志启用时必须事前审查。agy 要求 worktree: true；
上下文上限 32KB，超限时拆分或压缩，不能删除验收或风险约束。
代码在 Worktree 按需读取，不复制到提示词。单任务生命周期没有自动重试或依赖调度，
可选多代理启动器的运行内 DAG 和一次重试不改变持久状态或合并权限。

原生实现用 `mode: direct`，`roles.executor` 填实际角色（例如 worker），
不调用 agy Adapter。中高风险必须隔离，低风险也须服从契约的隔离要求。
Root 派发后核验范围和回执，再执行核心迁移；原生任务不产生 agy 记录，也不交给 collect。
更换后端不能绕过风险门，见[编排规则](orchestration.md)。

受控任务由 route 输出契约哈希，人类在版本化任务文件外创建审批 YAML，包含
task_id、contract_sha256、result: APPROVED、approved_by 和 evidence（ADR/审查引用）。
通过 prepare 的 `--approval-file` 传入；direct/manual 使用 start 的同名参数。
这是事前审查记录，不是身份的密码学证明，也不是合并批准；核心合并门仍适用。
