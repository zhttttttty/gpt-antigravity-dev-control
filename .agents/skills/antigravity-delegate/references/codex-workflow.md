# Codex 工作流程

正式生命周期维护在[统一控制流程](../../../../docs/CONTROL_WORKFLOW.md)。
按当前阶段阅读，混合执行、精确快照和合计容量见
[编排规则](../../../../.ai/rules/ORCHESTRATION.md)。

生命周期命令均针对主控仓库。原生/direct 使用 `start`，
本地 agy 使用 `prepare/launch/collect`。仅 Root 推进状态；
Worktree 的任务目录是契约快照，不是活动状态。

新任务使用 `control.py create`，补齐范围、验收和检查后验证。
创建 Worktree 前提交契约，配置基线必须等于 HEAD，并使用控制器返回的回执路径。

收到“继续”时，先检查任务状态、回执、Git 和真实执行器状态，从未完成阶段恢复，
不重复成功启动。缺失证据保持 UNKNOWN；agy 失败参见[故障恢复](failure-recovery.md)。
