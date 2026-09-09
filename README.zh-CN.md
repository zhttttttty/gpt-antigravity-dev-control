# V3.1：本地优先的 AI 开发分工控制层

推荐流程：**Codex 规划与验收 → 本地 agy + 独立 Worktree 实施 → 精简回执 → 人工合并**。
保留 V2 Task / Risk Gate / Receipt；原 V3 Lite 远程 API 实现保留为实验性可选路径。

```powershell
python -m pip install -r .ai/scripts/requirements-local.txt
python .ai/scripts/delegate.py probe --executable "$env:LOCALAPPDATA\agy\bin\agy.exe"
python .ai/scripts/delegate.py --help
```

仓库内已提供 `$antigravity-delegate` 技能，无需 Hermes 或全局配置改写。
小任务直接执行；大块独立任务委派；高风险先审批。默认不会自动重试或合并。
已检查 agy 1.0.10 帮助中的 `-p`、`--print-timeout`，登录与真实任务能力需实测。

真实交互辅助测试已通过：6 个单元测试及 14 个独立边界检查。
推荐在终端使用 `launch --interactive` 逐项审批。无完成证据的零退出码现在
返回 `NEEDS_ATTENTION`；可用 `diagnose` 排查，并显式执行一次交互 `--recover`。
这不代表无人值守已验证，也不启用全局免确认。

如确需在一次性可信 Worktree 中免逐项确认，可显式使用
`launch --interactive --full-access --approve`。它只传递 agy 的
`--dangerously-skip-permissions`，不授予 Windows 管理员权限；回执、范围和
Review 门仍然有效，且不会成为默认模式。

- [V3.1 操作与恢复指南](docs/LOCAL_DELEGATION.md)
- [用量测量方法](COST_METRICS.md)：不保证固定 Token 节省比例。

以下为保留的 V2 / V3 Lite 背景与远程路径说明。

# GPT-5.6 Sol × Antigravity 开发控制平面

[English](README.md)

这是一个以 Git 仓库为事实源的 AI 软件开发控制框架：

- **GPT-5.6 Sol**：PM / 架构师 / Planner / Reviewer；
- **Antigravity / Gemini**：受约束的 Executor，负责实现、测试和证据回传；
- **Human**：架构、高风险变更和最终合并的最高权限。

## 核心流程

```text
需求
 ↓
GPT-5.6 制定架构与任务
 ↓
task.yaml
 ↓
V3 Lite Orchestrator
 ↓
Antigravity 实现 + 测试
 ↓
Executor Receipt
 ↓
GPT-5.6 独立 Review
 ↓
PASS / REWORK / BLOCKED / 人工风险门
```

## V2 与 V3 Lite

- `v2` 分支：手动工作流。适合小项目和希望完全人工控制派发过程的场景。
- `main` 分支：V3 Lite。在 V2 协议之上增加 SQLite 状态、Lease、自动派发、自动 Review Loop。

V3 不推翻 V2。`task.yaml`、Receipt、Risk Gate、Worktree、ADR 和状态机仍是核心协议。

## 快速开始

```bash
git clone https://github.com/zhttttttty/gpt-antigravity-dev-control.git
cd gpt-antigravity-dev-control
python -m pip install -r .ai/orchestrator/requirements.txt
python .ai/orchestrator/orchestrator.py init
python .ai/orchestrator/orchestrator.py status
```

真实调用 V3 时设置：

```text
OPENAI_API_KEY
GEMINI_API_KEY
ANTIGRAVITY_GITHUB_PAT   # 私有仓库时
```

自动执行 READY 任务：

```bash
python .ai/orchestrator/orchestrator.py loop --until-idle
```

## 设计原则

1. 仓库而不是聊天记录是长期事实源。
2. Executor 不能自行扩大 scope 或修改架构权限。
3. “实现完成”不等于“验收通过”。
4. 所有关键结论必须有可检查 Evidence。
5. 高风险变更必须经过独立 Review 和人工审批门。
6. REWORK 不覆盖旧证据。

详细说明见 [快速开始](docs/QUICK_START.md)、[架构](docs/ARCHITECTURE.md) 和 [V2/V3 对比](docs/V2_V3_COMPARISON.md)。
