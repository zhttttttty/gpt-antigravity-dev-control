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
