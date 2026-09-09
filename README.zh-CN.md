# GPT × Antigravity 本地开发控制平面

[English](README.md)

推荐流程：**Codex 规划与验收 → 本地 agy + 独立 Worktree 实施 → 精简回执 → 人工合并**。
V2 的 Task、Risk Gate、Receipt、状态机和 Worktree 规则继续作为稳定协议。

```powershell
python -m pip install -r .ai/scripts/requirements-local.txt
python .ai/scripts/delegate.py probe --executable "$env:LOCALAPPDATA\agy\bin\agy.exe"
python .ai/scripts/delegate.py --help
```

仓库内已提供 `$antigravity-delegate` 技能，无需 Hermes 或远程 Reviewer API。
小任务直接执行；边界明确的多文件实现与测试交给 Antigravity；高风险任务先审批。
默认不会自动重试、自动合并或后台批量调度。

## 核心流程

```text
需求 → Codex 规划 → task.yaml → 本地 agy / Worktree
     → Compact Receipt + 本地日志 → Codex 独立验收 → 人工合并
```

推荐在真实终端使用 `launch --interactive` 逐项审批。若一次性可信 Worktree
确需免逐项确认，可显式使用：

```powershell
python .ai/scripts/delegate.py launch TASK-001 --approve --interactive --full-access --executable "$env:LOCALAPPDATA\agy\bin\agy.exe"
```

该参数只向 agy 传递 `--dangerously-skip-permissions`，不会授予 Windows 管理员权限；
任务范围、回执、Review 与人工合并门仍然生效。

## 分支定位

| 分支 | 定位 |
|---|---|
| `main` | V3.1 本地委派主线 |
| `v2` | 纯手动协议基线 |
| `archive/v3-lite` | 已归档的远程 API / SQLite Orchestrator，仅供历史追溯 |

V3 Lite 已从 `main` 移除；归档见
[`archive/v3-lite`](https://github.com/zhttttttty/gpt-antigravity-dev-control/tree/archive/v3-lite)。

## 设计原则

1. 仓库与 Git，而不是聊天记录，是长期事实源。
2. Executor 不得自行扩大 scope 或修改架构权限。
3. “实现完成”不等于“验收通过”。
4. 关键结论必须有可检查 Evidence。
5. 高风险变更必须经过独立 Review 和人工审批门。
6. REWORK 不覆盖旧证据；完整日志留在本地，默认只回传摘要。

详细说明：

- [快速开始](docs/QUICK_START.md)
- [V3.1 操作与恢复指南](docs/LOCAL_DELEGATION.md)
- [架构](docs/ARCHITECTURE.md)
- [V2 / V3.1 对比](docs/V2_V3_1_COMPARISON.md)
- [用量测量方法](COST_METRICS.md)
