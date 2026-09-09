# GPT × Antigravity 本地开发控制平面

[English](README.md)

统一流程：**Codex 规划与验收 → 按任务路由直接实施或交给本地 Antigravity →
精简回执 → 人工合并**。

项目只有一套任务协议和一个主要命令入口，通过 `execution.mode` 选择直接执行、本地委派或审批后委派。

## 快速开始

```powershell
python -m pip install -r .ai/scripts/requirements-local.txt
python .ai/scripts/control.py status
python .ai/scripts/control.py probe --executable "$env:LOCALAPPDATA\agy\bin\agy.exe"
python .ai/scripts/control.py --help
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
| `direct` | Codex 或人工直接完成小型修改 |
| `delegated` | 本地 agy 在独立 Worktree 完成边界明确的实现与测试 |
| `approval_required` | 架构、安全、迁移、部署或其他高风险任务先审批再委派 |

三种模式共用同一套 Task Contract、状态机、Risk Gate、Receipt、Review 和人工合并门。

## 统一命令入口

```powershell
python .ai/scripts/control.py validate TASK-001
python .ai/scripts/control.py route TASK-001
python .ai/scripts/control.py prepare TASK-001 --approve
python .ai/scripts/control.py launch TASK-001 --approve --interactive --executable "$env:LOCALAPPDATA\agy\bin\agy.exe"
python .ai/scripts/control.py collect TASK-001
```

原 `ai.py` 和 `delegate.py` 暂时保留为兼容入口，新使用方式统一采用 `control.py`。

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

- [快速开始](docs/QUICK_START.md)
- [统一控制流程](docs/CONTROL_WORKFLOW.md)
- [本地委派与恢复](docs/LOCAL_DELEGATION.md)

### 技术说明

- [文档索引](docs/README.md)
- [执行模式](docs/EXECUTION_MODES.md)
- [架构](docs/ARCHITECTURE.md)
- [当前限制](docs/LIMITATIONS.md)
- [用量测量](COST_METRICS.md)

当前版本：**3.1.2-local**。
