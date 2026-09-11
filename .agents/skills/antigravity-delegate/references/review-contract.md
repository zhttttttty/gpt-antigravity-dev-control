# 审查契约

原生 Codex 与 Antigravity 的输出是证据，不是验收决定。
返回精简报告并引用完整证据；agy 的 stdout、stderr 和 CLI 日志保存在调用者选择的目录。
原生代理保留身份和命令/测试证据，不虚构 agy 日志。

报告包含：

- 任务名、Worktree、基础提交、头部提交和最终状态。
- 变更文件与测试计数：`passed`、`failed`、`not_run`。
- 验收检查的 `passed` 与 `total`。
- 覆盖计数：语义阅读的文本文件，以及检查过类型、大小、哈希和用途的非文本文件。
- 已知问题与完整日志路径。

只有任务要求全仓库审计时才报告全仓覆盖；小任务或文件枚举不能证明全仓阅读。
记录未提交和新增文件，仅 HEAD 一致不够。使用真实审查者身份；
Astra low 偏好不豁免独立审查、事前审查、跨家族或人工风险门。

Codex 用 `rg -n -C` 或源码阅读独立核实所有 P0/P1 的路径和行号，
运行仓库测试并检查 Worktree。将证据标记为 `CONFIRMED`、`CONDITIONAL` 或
`HYPOTHESIS`，合并重复发现，按部署或数据前提调整严重程度。
收集只能进入 REVIEW，不直接进入 DONE 或合并。

## 本地启动器契约

`launch_agents.ps1` 接收含 `tasks` 数组的 JSON。每项包含稳定的 `name`、
绝对 `worktree`、有界 `prompt`；可选 `mode`（plan/accept-edits）、
`depends_on`、`max_retries`、`timeout_seconds`、`auto_approve`、
`effort`、`model`、`attempt`。可按需采用 full、backend、frontend、opsdocs 分片。
依赖图、并发和写入锁见[协作协议](coordination-protocol.md)。
