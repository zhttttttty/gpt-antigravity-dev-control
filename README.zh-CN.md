# GPT × Antigravity 本地开发控制平面

[English](README.md)

统一流程：**Sol high 决策与计划 → Luna high 探索/核验 → 本地 Antigravity 实现 →
Sol 最终验收 → 人工合并**。

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

仓库提供 Plus 项目级配置：Sol high 是唯一规划、架构和最终验收主控，Luna high
负责有界只读探索、独立测试与审查，本地 Antigravity 是 delegated/approval_required
的默认实现者。原生 Luna worker 仅在 agy 不可用或不适用、Root 记录原因并明确批准
切换为 direct 后作为回退。原生线程上限为两个，跨原生/agy 的合计预算由 Root 协调。
详见 [混合执行指南](.agents/skills/antigravity-delegate/references/orchestration.md)。

使用 Python 3.11+ 执行 `python .agents/skills/antigravity-delegate/scripts/control.py check-orchestration` 可检查
项目配置一致性；这不代表已验证实际模型路由、额度或沙箱执行。

仓库内置可发现技能：.agents/skills/antigravity-delegate。在当前仓库的
Codex 任务中调用 $antigravity-delegate，Codex 会负责规划、命令执行、回执收集、
验收和恢复；agy 只作为 Codex 启动的本地实现子进程。

### 调用方式

在 Codex 对话中直接说明：

```text
使用 $antigravity-delegate 完成这个功能：
为用户登录模块增加邮箱验证码校验，并补充测试。
```

如果希望明确交给本地 Antigravity，可补充：

```text
使用 $antigravity-delegate，将任务交给 Antigravity 子代理，
在隔离 Worktree 中完成，并返回测试结果和回执路径。
```

默认角色分工是：Luna explorer 先提供代码路径与风险证据，Sol 据此创建任务契约；
agy 作为唯一写入者实现并退出后，Luna tester/reviewer 串行核验同一快照，最后由 Sol
复核 Diff、测试和回执并决定 PASS、REWORK 或 BLOCKED。任何代理都不会自动合并。

在目标 Git 项目中，也可以直接运行控制器。首次接入只需初始化最小运行状态：

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py init --repo D:\Projects\my-app
Set-Location D:\Projects\my-app
python .agents/skills/antigravity-delegate/scripts/control.py probe
```

创建并执行一个有界任务：

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py create TASK-001 `
  --title "增加邮箱验证码登录" `
  --objective "增加验证码校验并补充测试" `
  --risk medium `
  --mode delegated

python .agents/skills/antigravity-delegate/scripts/control.py validate TASK-001
python .agents/skills/antigravity-delegate/scripts/control.py route TASK-001
python .agents/skills/antigravity-delegate/scripts/control.py prepare TASK-001 --approve
python .agents/skills/antigravity-delegate/scripts/control.py launch TASK-001 --approve --interactive
python .agents/skills/antigravity-delegate/scripts/control.py collect TASK-001
python .agents/skills/antigravity-delegate/scripts/control.py status TASK-001
```

`route` 返回 `direct`、`delegated` 或 `approval_required`。高风险任务必须先完成审批；
`collect` 成功只表示进入待审查状态，不会自动合并或宣布任务完成。执行前可用
`control.py probe --executable <agy路径>` 检查本机 `agy` 是否可用。

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

- [调用提示词：Sol + Luna + Antigravity](.agents/skills/antigravity-delegate/references/invocation-prompts.md)
- [快速开始](.agents/skills/antigravity-delegate/references/workflow.md)
- [统一控制流程](.agents/skills/antigravity-delegate/references/workflow.md)
- [本地委派与恢复](.agents/skills/antigravity-delegate/references/delegation.md)

### 技术说明

- [文档索引](.agents/skills/antigravity-delegate/SKILL.md)
- [执行模式](.agents/skills/antigravity-delegate/references/orchestration.md)
- [架构](.agents/skills/antigravity-delegate/references/workflow.md)
- [当前限制](.agents/skills/antigravity-delegate/references/delegation.md)
- [用量测量](COST_METRICS.md)

当前版本：**3.3.0-local**。
