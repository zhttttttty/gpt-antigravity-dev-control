# 快速开始

[English](QUICK_START.md)

## 1. 安装与检查

    python -m pip install -r .ai/scripts/requirements-local.txt
    python .ai/scripts/control.py status
    python .ai/scripts/control.py probe

probe 只检查 agy 是否能被发现以及帮助信息，不代表已经登录或模型调用成功。

## 2. 创建任务

将 .ai/templates/task/ 复制到 .ai/tasks/queue/TASK-001/，填写目标、可写范围、
保护范围、风险、验收证据、检查命令和 execution.mode。

    python .ai/scripts/control.py validate TASK-001
    python .ai/scripts/control.py route TASK-001

## 3. 直接执行

小型修改或委派成本高于实现成本时使用 direct：

    python .ai/scripts/control.py start TASK-001 --worktree

严格在任务范围内修改，填写 Executor Receipt，然后独立检查 Diff 和证据。

## 4. 本地委派

边界明确的多文件实现、测试和重构可以使用 delegated：

    python .ai/scripts/control.py prepare TASK-001 --approve
    python .ai/scripts/control.py launch TASK-001 --approve --interactive --executable /absolute/path/to/agy
    python .ai/scripts/control.py status TASK-001
    python .ai/scripts/control.py collect TASK-001

collect 只会把完整证据移到 REVIEW，不会直接变成 DONE。Codex 独立检查 Diff
和测试，人类明确执行合并。

## 5. 审批后执行

高风险或架构权限任务会路由到 approval_required。按照
[本地委派操作](LOCAL_DELEGATION.zh-CN.md) 创建绑定当前契约摘要的审批文件，
再传给 prepare。

## 6. Review 与收尾

写入 receipt.qa.yaml 和 review.yaml 后：

    python .ai/scripts/control.py transition TASK-001 DONE

只有所有 Risk Gate 通过后才能执行。项目状态同步和 Git 合并必须显式完成。
