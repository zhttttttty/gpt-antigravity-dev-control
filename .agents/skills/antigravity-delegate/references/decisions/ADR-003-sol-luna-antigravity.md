# ADR-003：Sol 主控、Luna high 核验与 Antigravity 实现

状态：已由 [ADR-004](ADR-004-adaptive-delegation.md) 部分取代，2026-10-01。

## 背景

原配置使用 Luna max 主控、Luna medium 原生执行和 Astra low 审查，适合优先节省
Codex 用量的混合执行。新的目标是让较强模型集中处理高价值判断，同时保持本地执行、
独立证据和人工合并边界。

## 决策

- GPT-5.6 Sol high 是唯一规划、架构、路由和最终验收决策者。
- GPT-5.6 Luna high 承担有界只读探索、调研、独立测试和审查，输出事实或建议，
  不代替 Root 批准计划或验收结果。
- 本地 Antigravity/agy 是 `delegated` 和 `approval_required` 任务的默认且唯一实现者。
- Luna worker 仅在 agy 不可用或不适用、Root 记录原因并明确批准切换为 `direct` 后使用；
  不允许静默降级，也不为 agy 增加转发代理。
- agy 完全退出后才串行运行 tester/reviewer；同一 Worktree 同时只有一个写入者。
- Sol 默认使用 high；特别困难或高风险的决策可由用户或运行时显式提高推理等级。

## 取舍

该配置把 Sol 用量集中在任务契约和最终判断，同时用 Luna high 承担大量读取与核验。
与固定由 Sol 处理全部步骤相比，它减少主控上下文和机械工作；与原配置相比，它增加
默认推理成本，但提升角色分离和复杂任务判断质量。

Antigravity 故障时不会自动回退，因此可用性换取了更可预测的执行身份。保留显式 native
worker 回退以便人工选择，不把偏好模型或 TOML 配置当作实际运行证据。

## 验证与回滚

`control.py check-orchestration` 必须验证项目配置、角色文件和任务模板一致。仓库测试只证明
离线协议一致性，不能证明账户模型可用、agy 登录、真实沙箱或 Provider 额度。

回滚时共同恢复 `.ai/config.yaml`、`.codex/`、任务模板、文档和版本；已有任务继续记录
实际身份，不重写历史回执。
