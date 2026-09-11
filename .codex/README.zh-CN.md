# Codex 项目级模型路由

`.codex/config.toml` 提供 Plus 项目默认配置：Luna max 负责规划与集成，Luna medium 负责原生执行，Astra low 负责独立审查。较大有界实现可以由 Root 通过现有控制器交给 Antigravity。`.ai/` 仍然是任务状态、范围、风险门和回执的事实源。

五个角色的职责边界位于 `.codex/agents/`：

- `explorer`：只读拓扑和依赖分析
- `worker`：按 Task Contract 实现代码
- `tester`：独立运行验证并记录证据
- `reviewer`：只读检查 diff、范围和安全性
- `researcher`：只读查阅文档与依赖兼容性

按需选择角色，原生线程默认上限两个；Root 协调原生与 agy 活跃任务合计最多两个，尚无跨两者的统一硬锁。完整流程、限制和验证方法见 [混合执行指南](../docs/HYBRID_ORCHESTRATION.md)。模型默认值不会改变任务权限或覆盖用户显式选择。
