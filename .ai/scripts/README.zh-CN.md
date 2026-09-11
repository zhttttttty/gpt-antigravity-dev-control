# 统一控制 CLI

[English](README.md)

主要入口是：

`python .ai/scripts/control.py check-orchestration` 使用 Python 3.11+ 离线检查
项目模型与角色配置一致性，不验证实际模型调用。见 [混合执行](../../docs/HYBRID_ORCHESTRATION.md)。

    python .ai/scripts/control.py status
    python .ai/scripts/control.py create TASK-001 --title "有界修改" --objective "可观察的结果"
    python .ai/scripts/control.py validate TASK-001
    python .ai/scripts/control.py route TASK-001
    python .ai/scripts/control.py prepare TASK-001 --approve
    python .ai/scripts/control.py launch TASK-001 --approve --interactive
    python .ai/scripts/control.py collect TASK-001
    python .ai/scripts/control.py transition TASK-001 DONE

control.py 将任务协议操作路由到 ai.py，将本地委派操作路由到 delegate.py。两个旧文件
保留为内部兼容入口，使用者不再需要在两个命令之间选择。
task_data.py 统一 YAML、审批和证据校验。补齐并验证创建的契约，提交后再创建 Worktree；
详见 [统一控制流程](../../docs/CONTROL_WORKFLOW.md)。

task.yaml 是公共契约，execution.mode 支持 direct、delegated 和 approval_required。
调度保持显式和本地化，不提供后台并发服务、Reviewer API 或自动合并。单任务恢复
是显式操作；可选 agy 多代理启动器支持依赖 DAG 和最多一次重试，不自动改变持久任务状态。
