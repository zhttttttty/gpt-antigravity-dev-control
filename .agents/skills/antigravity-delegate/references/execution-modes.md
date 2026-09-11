# 执行模式与能力映射

`direct`、`delegated` 和 `approval_required` 是契约中的控制器路由，
不是 `agy --mode` 的值。

## 选择后端

| 执行负责人 | 路由 | 派发与证据 |
|---|---|---|
| Root 或人类 | `direct` | 核心生命周期、显式检查与回执 |
| 原生 Codex worker | `direct` | 真实 `spawn_agent`，Root 核验回执与范围 |
| 本地 Antigravity | `delegated` 或 `approval_required` | `control.py` 的 probe/prepare/launch/collect |

原生 explorer、researcher、tester、reviewer 可以辅助两条路径。
不要设置 `execution.mode: native`，也不要虚构 Gemini Codex 角色。
direct 下 agy adapter 不启用。任何后端都须遵守架构与风险门，见[任务协议](task-protocol.md)。

## 本地能力映射

每次 agy 运行前探测 `--version`、`--help`、`agent`、`agents` 和 `agent list`。
帮助输出是参数与模式支持情况的依据。已知模式有 `accept-edits` 和 `plan`，
但 Adapter 不能硬编码假定它们必然可用。

| 意图 | agy 映射 | 约束 |
|---|---|---|
| 访问一次性 Worktree | 省略 `--sandbox` | 不扩大契约和授权范围 |
| 自动批准工具调用 | 帮助确认后添加 `--dangerously-skip-permissions` | 须明确批准且使用隔离 Worktree |
| 只读审查 | `--mode plan` | 提示词禁止创建、修改、删除、提交、合并和推送 |
| 正常实现 | 支持时用 `--mode accept-edits` | 保留范围、回执、测试和审查门 |

未声明支持的参数应拒绝并报告，不能把 direct 转成虚构 agy 模式。
启动参数必须以数组或 `ProcessStartInfo.ArgumentList` 传递，不拼接 Shell 命令。
