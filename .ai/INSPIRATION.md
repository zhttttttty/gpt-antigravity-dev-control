# 设计参考

这是原创项目模板，不依赖或复制以下项目的源码。下列公开项目提供了流程思路：

- `QiQi14/multi-agents-control-plane`：仓库内 .ai/ 控制平面、契约、回执、风险门、代理适配入口和证据优先审查。
- `navels/neal`：规划、编码、审查角色分离，按范围创建新上下文，以文件恢复运行。
- `microsoft/ArgusAgent`：持久状态、检查点与证据，分离执行和验证。
- `ferrus-dev/ferrus`：可恢复状态机编排和有界执行产物。
- `Runfusion/Fusion`：规划、审查、执行、再审查与 Git Worktree 隔离。
- `KjellKod/quest`：文件驱动的跨模型审查和人工批准。
- `donvito/codex-astra-luna-orchestrator`，提交 `014b1d7c48c39087beec8aa4f1ca022053ac17b3`：
  Plus 模型配置、有界原生角色、精简证据和可重复用量比较。适配见 ADR-002，
  未复制上游安装器、Skill 文本或测量脚本。

目标是组合兼容的流程，形成轻量 Codex 与 Antigravity 工作方式。
