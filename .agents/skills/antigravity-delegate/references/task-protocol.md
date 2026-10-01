# 任务路由

保留 `schema_version: 2` 与核心字段，确保文件兼容。路由示例：

```yaml
execution:
  mode: delegated
  adapter: antigravity_cli
  model: configured_default
  context_budget: incremental
  report_level: summary
  max_implementation_reworks: 1
  max_infra_retries: 1
  routing_override:
    result: NOT_REQUESTED
    approved_by: null
    evidence: null
  escalation: codex_review
planning:
  work_type: mechanical
  judgment: low
  context_continuity: low
  acceptance_determinism: high
checks:
  adversarial_probes: []
  fast_gate: []
  final_gate: []
  required: []  # 旧任务兼容入口
```

缺少 execution 时按旧版 direct 处理。支持 direct、delegated、approval_required。
高风险或任一 authority 标志启用时必须事前审查。agy 要求 worktree: true；
上下文上限 32KB，超限时拆分或压缩，不能删除验收或风险约束。
`incremental` 在返工时优先发送当前 task、brief、rollback 与前次结构化 review；缺少 review
时自动回退完整 context。新 gate 按 adversarial、fast、final 顺序执行，旧 required 追加为
兼容 final gate。
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
`routing_override` 只是契约中的路由声明，高判断任务覆盖到 Antigravity 时仍强制读取该
独立审批文件，不能把 task.yaml 自身当成审批证据。

所有 verify 都必须提供绑定当前契约哈希的独立 approval file，从而批准其中的确切命令矩阵。
检查命令默认按 argv（`shell: false`）执行。确需管道、重定向等 shell 语法时必须显式写
`shell: true`；控制器仍执行单命令
超时、总 deadline、进程树清理和每条命令后的 Worktree 身份/干净度复核。
