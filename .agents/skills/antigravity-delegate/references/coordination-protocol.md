# 多代理协作协议

Codex 是协调者。Antigravity Agent 不直接互相对话，而是通过显式依赖、需要串行时
共享的 Git 状态，以及 `sessions.json` 中登记的报告路径协作。

## 配置

`launch_agents.ps1` 接收包含 `tasks` 数组的 JSON：

    {
      "tasks": [
        {
          "name": "full",
          "worktree": "C:/repo-review",
          "mode": "plan",
          "prompt": "审阅整个仓库",
          "max_retries": 0
        },
        {
          "name": "backend",
          "worktree": "C:/repo-backend",
          "mode": "accept-edits",
          "prompt": "实现后端任务契约",
          "depends_on": ["full"],
          "timeout_seconds": 1260
        }
      ]
    }

可选字段包括 `depends_on`、`max_retries`（零或一）、`timeout_seconds`、
`auto_approve`、`effort`、`model` 和初始 `attempt`。

## 调度约束

以下是本地 agy 启动器的保证，不是覆盖 Codex 原生代理的全局锁。Root 还需遵守
项目合计预算（默认两个活跃执行单元），同时计算原生任务和每个 agy 分片。只给
启动器分配剩余容量；分配两个槽位前先结束原生工作。使用下述更高启动器上限前，
必须先协调调整项目合计预算。见 [统一编排规则](orchestration.md)。

- 默认并发数为两个，硬性最大值为四个。
- 请求三个或四个并发时，启动器先运行两个 Agent，首个任务成功后才提升到目标值。
  大型只读或多文档任务可以使用三到四个；包含写入任务时默认仍限制为两个，只有显式
  使用 `-AllowHighWriteConcurrency` 才会放宽，并且各写入 Agent 仍应使用独立 Worktree。
- 用户级排他锁阻止两个启动器同时占用本机 agy 容量。
- 依赖关系必须形成有效 DAG，并据此计算 `planned_wave`。
- 只读 `plan` Agent 可以共享 Worktree；只要任一 Agent 可写，该 Worktree 就必须独占。
- 失败或超时最多重试一次；首次失败会终止扩容，并将本次运行剩余阶段立即降为单并发。
- stdout 和 stderr 会被异步读取，避免管道缓冲区阻塞。
- 依赖任务会收到已完成上游报告的稳定路径。

相互独立的实现分片应使用不同 Worktree。只有后续任务必须读取前序变更并且明确要求
串行时，才使用同一 Worktree 加 `depends_on`。调度器不会自动合并分支。

## 输出

每次尝试都有独立报告、执行日志和 stderr；最新结果同时写入 `<name>.md`。
`sessions.json` 记录依赖图、尝试历史、状态、超时、提示词哈希和实际并发数。
`collect_reports.ps1` 生成 `summary.json` 与 `handoff.md`，之后由 Codex 独立验证并合并
重复发现。
