# 高级任务协议与自适应路由

本页维护持久 schema v2 契约。普通一次委派见[日常指南](quick-start.md)，完整步骤见[控制流程](workflow.md)。

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
上下文上限 32,000 UTF-8 字节，超限时拆分或压缩，不能删除验收或风险约束。
`incremental` 在返工时优先发送当前 task、brief、rollback 与前次结构化 review；缺少 review
时自动回退完整 context。新 gate 按 adversarial、fast、final 顺序执行，旧 required 追加为
兼容 final gate。
代码在 Worktree 按需读取，不复制到提示词。单任务生命周期没有自动重试或依赖调度，
可选多代理启动器的运行内 DAG 和一次重试不改变持久状态或合并权限。

原生实现通常声明 `mode: direct`；自适应路由把原 delegated 选择转为 direct 时，以 backend 为准，
先核对实际角色与契约，再执行 start。`roles.executor` 填实际角色（例如 worker），
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

## 字段与预算

七文件任务包含 task.yaml、brief、context、执行回执、QA、review 和 rollback。
ID 为 TASK- 后接 1–80 个字母、数字、下划线或连字符，首位为字母/数字；revision 和 attempt 为正整数。
验收必须有唯一 AC-* 编号、可观察 criterion 和 evidence，且至少有一个 staged 或旧 required 检查。
可写与保护路径、真实角色、依赖、隔离基线、风险开关及 metadata 需保持完整。
YAML 拒绝重复键，输入限制为 128,000 UTF-8 字节；模板以包内 templates/task/task.yaml 为准。

max_implementation_reworks 默认 1，允许 0–9 次实现返工；max_infra_retries 默认 1，允许 0–3 次基础设施重试。
存在新返工字段时优先使用，旧 max_execution_attempts（1–10 次）继续兼容。
显式 approval_required 不会因选择 direct 而降低；routing_override 的批准也不能替代独立审批文件。

## 状态与目录

| 状态 | 目录 | 允许的下一状态 |
|---|---|---|
| READY | `.ai/tasks/queue/` | IN_PROGRESS、BLOCKED |
| IN_PROGRESS | `.ai/tasks/active/` | REVIEW、BLOCKED |
| REVIEW | `.ai/tasks/review/` | DONE、READY、BLOCKED |
| BLOCKED | `.ai/tasks/blocked/` | READY |
| DONE | `.ai/tasks/done/` | ARCHIVED |
| ARCHIVED | `.ai/tasks/archive/` | 无 |

主控目录拥有唯一活动状态；工作树任务副本只是契约快照。REVIEW → READY 会归档并增加 task attempt，
BLOCKED → READY 不执行相同的自动重置。PROJECT_STATE 是人工摘要，实时读取使用 status --json。
日常 run 不进入这套状态机。

## 审批结构

以下值须替换为真实 task、route 哈希、审批人及证据，保存在版本化任务文件之外：

```yaml
task_id: TASK-001
contract_sha256: <route 返回的哈希>
result: APPROVED
approved_by: <实际审批人>
evidence: <事前审查记录>
```

哈希忽略 status 和 metadata，其余契约变化须重新核对。审批记录不是身份的密码学证明，也不是最终合并批准。
