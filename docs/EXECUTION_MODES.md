# 执行模式

执行路由属于任务契约，用于在不改变证据和 Review 规则的前提下选择合适的成本路径。

    execution:
      mode: direct
      adapter: antigravity_cli
      model: configured_default
      context_budget: compact
      report_level: summary
      max_execution_attempts: 2
      escalation: codex_review

## direct

适合小型代码、配置、文档修改，或协调成本高于实现成本的任务。仍然使用同一套
状态机、回执、证据和 Review 规则。

原生 Codex 实现也使用 direct：`roles.executor` 填实际角色，按风险与契约提供
Worktree，由 Root 派发、检查范围和核对回执，agy adapter 不参与。direct 是协议
路由，不代表只有 Root 工作。见 [混合执行](HYBRID_ORCHESTRATION.md)。

## delegated

适合边界明确、可独立验收的多文件实现、测试和重构。控制器创建隔离 Worktree，
启动本地 agy，保留完整日志，并收集精简回执。

## approval_required

适合高风险或涉及架构权限的任务。风险或 authority 字段触发时会自动升级。准备任务
前需要绑定当前契约的审批文件，Review 和最终合并仍然是独立步骤。

## 共享保证

| 事项 | 统一行为 |
|---|---|
| 契约 | 结构化 task.yaml |
| 状态 | 仓库目录驱动 |
| 风险 | Risk Gate |
| 证据 | Executor/QA Receipt 与 Review |
| REWORK | 保留之前尝试的证据 |
| 验收 | 独立 Review |
| 合并 | 人工控制 |
