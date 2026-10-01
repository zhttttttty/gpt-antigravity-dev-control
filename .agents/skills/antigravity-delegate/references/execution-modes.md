# 执行模式与能力映射

`direct`、`delegated` 和 `approval_required` 是契约中的控制器路由，
不是 `agy --mode` 的值。

## 选择后端

| 执行负责人 | 路由 | 派发与证据 |
|---|---|---|
| Root 或人类 | `direct` | 核心生命周期、显式检查与回执 |
| 原生 Codex worker | `direct` | 真实 `spawn_agent`，Root 核验回执与范围 |
| 本地 Antigravity | `delegated` 或 `approval_required` | `control.py` 的 probe/prepare/launch/verify/collect |

原生 explorer、researcher、tester、reviewer 可以辅助两条路径。
不要设置 `execution.mode: native`，也不要虚构 Gemini Codex 角色。
direct 下 agy adapter 不启用。任何后端都须遵守架构与风险门，见[任务协议](task-protocol.md)。

`approval_required` 只表达执行前需要审批。实际后端还受自适应路由控制：高判断或强连续性
任务即使有审批也默认 direct；只有声明 `execution.routing_override` 且 prepare 同时收到
绑定当前契约哈希的独立 approval artifact，才允许 Antigravity 执行这类任务。
旧任务缺少新 planning 字段时沿用显式 mode。

Antigravity 的正常生命周期为 `prepare -> launch -> verify -> collect`。launch 只负责实现；
verify 在同一 Worktree 中运行契约声明的命令，依次处理 `adversarial_probes`、`fast_gate`、
`final_gate`，旧 `checks.required` 作为兼容 final gate。

所有 verify 都须收到 contract-bound `--approval-file`，审批的是当前契约中的确切命令矩阵。
check 默认按 argv、`shell: false` 执行；只有契约显式写 `shell: true` 时才调用 shell。
每条命令有超时，整组有总 deadline；
超时会清理进程树，每条命令后重新核验 branch、HEAD 和干净 Worktree。

## 本地能力映射

每次 agy 运行前探测 `--version`、`--help`、`agent`、`agents` 和 `agent list`。
帮助输出是参数与模式支持情况的依据。已知模式有 `accept-edits` 和 `plan`，
但 Adapter 不能硬编码假定它们必然可用。

| 意图 | agy 映射 | 约束 |
|---|---|---|
| 访问一次性 Worktree | 省略 `--sandbox` | 不扩大契约和授权范围 |
| 自动批准工具调用 | `control.py launch --approve --auto-approve` 映射为 `--dangerously-skip-permissions` | 须明确批准且使用隔离 Worktree；`--full-access` 仅兼容旧调用 |
| 只读审查 | `--mode plan` | 提示词禁止创建、修改、删除、提交、合并和推送 |
| 正常实现 | 支持时用 `--mode accept-edits` | 保留范围、回执、测试和审查门 |

未声明支持的参数应拒绝并报告，不能把 direct 转成虚构 agy 模式。
启动参数必须以数组或 `ProcessStartInfo.ArgumentList` 传递，不拼接 Shell 命令。
