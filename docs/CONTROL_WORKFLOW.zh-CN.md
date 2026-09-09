# 统一控制流程

[English](CONTROL_WORKFLOW.md)

## 角色

- Codex：需求、架构、任务契约、路由和独立 Review。
- Antigravity / Gemini：在 Worktree 中完成受限实现并生成执行证据。
- Human：高风险审批和最终合并。

## 1. 规划

建立最小可独立验收的任务，定义范围、风险、验收证据、检查命令和 execution.mode。

    python .ai/scripts/control.py validate TASK-001
    python .ai/scripts/control.py route TASK-001

## 2. 执行

- direct：Codex 或人工在契约范围内直接实现。
- delegated：本地 agy 在准备好的任务 Worktree 中实现。
- approval_required：先将人工审批绑定到契约，再执行本地委派。

    python .ai/scripts/control.py start TASK-001 --worktree
    python .ai/scripts/control.py prepare TASK-001 --approve
    python .ai/scripts/control.py launch TASK-001 --approve --interactive
    python .ai/scripts/control.py collect TASK-001

Executor 只能修改可写范围，运行必要检查并写回执，不得自我批准或合并。

## 3. Review

Codex 独立阅读契约、精确 Diff、Executor Receipt、测试证据、架构和 ADR。
允许的结论是 PASS、PASS_WITH_NOTES、REWORK、BLOCKED。

Review 不应悄悄修改实现。REWORK 必须记录具体问题并保留之前的尝试证据。

## 4. 收尾

QA、Review 和 Risk Gate 全部通过后：

    python .ai/scripts/control.py transition TASK-001 DONE

同步项目状态，保留证据，并明确合并已 Review 的提交。

## 恢复

新会话依次读取项目状态、任务目录、回执、Review、Git Worktree、ADR 和本地运行记录。
安全恢复不依赖原始聊天记录。
