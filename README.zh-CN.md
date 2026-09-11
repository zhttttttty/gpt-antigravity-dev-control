# GPT × Antigravity 本地开发控制平面

[English](README.md)

统一流程：**Codex 规划与验收 → 按任务路由直接实施或交给本地 Antigravity →
精简回执 → 人工合并**。

项目只有一套任务协议和一个主要命令入口，通过 `execution.mode` 选择直接执行、本地委派或审批后委派。

本仓库的主要交付物是 `.agents/skills/antigravity-delegate`。将该目录作为 Skill
复制到其他 Git 项目后，只需生成最小 `.ai/` 运行状态：

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py init --repo D:\Projects\my-app
python .agents/skills/antigravity-delegate/scripts/control.py --repo D:\Projects\my-app create TASK-001 --title "有界修改" --objective "可观察的结果"
```

## 快速开始

```powershell
python -m pip install -r .agents/skills/antigravity-delegate/scripts/requirements-local.txt
python .agents/skills/antigravity-delegate/scripts/control.py status
python .agents/skills/antigravity-delegate/scripts/control.py probe --executable "$env:LOCALAPPDATA\agy\bin\agy.exe"
python .agents/skills/antigravity-delegate/scripts/control.py --help
```

每个任务通过 `execution.mode` 选择执行方式：

```yaml
execution:
  mode: delegated  # direct | delegated | approval_required
  adapter: antigravity_cli
  context_budget: compact
  report_level: summary
  max_execution_attempts: 2
  escalation: codex_review
```

| 模式 | 用途 |
|---|---|
| `direct` | Root、人工或原生 Codex worker 按契约实现，由 Root 检查证据 |
| `delegated` | 本地 agy 在独立 Worktree 完成边界明确的实现与测试 |
| `approval_required` | 架构、安全、迁移、部署或其他高风险任务先审批再委派 |

三种模式共用同一套 Task Contract、状态机、Risk Gate、Receipt、Review 和人工合并门。

## 统一命令入口

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py validate TASK-001
python .agents/skills/antigravity-delegate/scripts/control.py route TASK-001
python .agents/skills/antigravity-delegate/scripts/control.py prepare TASK-001 --approve
python .agents/skills/antigravity-delegate/scripts/control.py launch TASK-001 --approve --interactive --executable "$env:LOCALAPPDATA\agy\bin\agy.exe"
python .agents/skills/antigravity-delegate/scripts/control.py collect TASK-001
```

原 ai.py 和 delegate.py 暂时保留为兼容入口，新使用方式统一采用 control.py。

## 在 Codex 中使用

仓库提供 Plus 项目级配置：Luna max 主控、Luna medium 原生执行、Astra low
独立审查。Root 可以在原生 worker 与 Antigravity 两种实现路径间选择，仍使用同一套
`.ai/` 契约与风险门。原生线程上限为两个，跨原生/agy 的合计预算由 Root 协调。
详见 [混合执行指南](.agents/skills/antigravity-delegate/references/orchestration.md)。

使用 Python 3.11+ 执行 `python .agents/skills/antigravity-delegate/scripts/control.py check-orchestration` 可检查
项目配置一致性；这不代表已验证实际模型路由、额度或沙箱执行。

仓库内置可发现技能：.agents/skills/antigravity-delegate。在当前仓库的
Codex 任务中调用 $antigravity-delegate，Codex 会负责规划、命令执行、回执收集、
验收和恢复；agy 只作为 Codex 启动的本地实现子进程。

对于边界明确的多文件任务，Codex 可以自动选择该 Skill。多代理运行支持依赖 DAG、
默认两个并发、大型只读任务健康探测后最多四个并发、独立写入 Worktree、失败一次后降为单并发重试，以及
`summary.json`/`handoff.md` 精简验收交接。

一次性可信 Worktree 如需免逐项确认，可显式增加 `--full-access`。它只向 agy
传递 `--dangerously-skip-permissions`，不授予 Windows 管理员权限，也不会绕过
任务范围、回执、验收和人工合并门。

## 核心原则

1. `.ai/` 与 Git 是长期事实源。
2. `task.yaml` 同时定义范围、权限、风险、路由和验收条件。
3. Executor 完成不等于 Reviewer 验收通过。
4. 缺失证据按失败关闭处理；REWORK 保留旧证据。
5. 完整日志留在本地，默认先读取精简回执。
6. 控制器不会自动合并，也不会自行宣布任务 DONE。

## 文档

### 使用指南

- [快速开始](.agents/skills/antigravity-delegate/references/workflow.md)
- [统一控制流程](.agents/skills/antigravity-delegate/references/workflow.md)
- [本地委派与恢复](.agents/skills/antigravity-delegate/references/delegation.md)

### 技术说明

- [文档索引](.agents/skills/antigravity-delegate/SKILL.md)
- [执行模式](.agents/skills/antigravity-delegate/references/orchestration.md)
- [架构](.agents/skills/antigravity-delegate/references/workflow.md)
- [当前限制](.agents/skills/antigravity-delegate/references/delegation.md)
- [用量测量](COST_METRICS.md)

当前版本：**3.2.0-local**。
