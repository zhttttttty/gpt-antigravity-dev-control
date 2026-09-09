# 统一工作流程

[English](WORKFLOW.md)

## 1. 规划

Codex 读取项目和状态，定义边界明确的任务，设置风险、权限、范围、验收证据和
execution.mode。

    python .ai/scripts/control.py validate TASK-001
    python .ai/scripts/control.py route TASK-001

## 2. 执行

- direct：Codex 或人工直接实现。
- delegated：本地 agy 在任务 Worktree 实现。
- approval_required：先完成契约绑定的审批，再本地委派。

    python .ai/scripts/control.py start TASK-001 --worktree
    python .ai/scripts/control.py prepare TASK-001 --approve
    python .ai/scripts/control.py launch TASK-001 --approve --interactive
    python .ai/scripts/control.py collect TASK-001

Executor 只能修改可写范围，运行检查并写 Receipt，不得自我批准或合并。

## 3. Review 与收尾

Codex 独立检查精确 Diff 和证据，结论为 PASS、PASS_WITH_NOTES、REWORK 或 BLOCKED。
Risk Gate 通过后使用 control.py transition 完成状态迁移，项目同步和 Git 合并保持显式。
