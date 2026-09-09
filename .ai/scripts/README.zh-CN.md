# 统一控制 CLI

[English](README.md)

主要入口是：

    python .ai/scripts/control.py status
    python .ai/scripts/control.py validate TASK-001
    python .ai/scripts/control.py route TASK-001
    python .ai/scripts/control.py prepare TASK-001 --approve
    python .ai/scripts/control.py launch TASK-001 --approve --interactive
    python .ai/scripts/control.py collect TASK-001
    python .ai/scripts/control.py transition TASK-001 DONE

control.py 将任务协议操作路由到 ai.py，将本地委派操作路由到 delegate.py。两个旧文件
保留为内部兼容入口，使用者不再需要在两个命令之间选择。

task.yaml 是公共契约，execution.mode 支持 direct、delegated 和 approval_required。
调度保持显式和本地化，不提供后台并发、Reviewer API、自动重试或自动合并。
