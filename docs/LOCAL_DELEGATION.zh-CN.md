# 本地委派操作

[English](LOCAL_DELEGATION.md)

Codex 负责规划和 Review，Antigravity 负责实现，人类负责合并。整个控制流程由
Codex 在仓库内执行，不需要 Hermes、远程 Reviewer API 或后台调度器。

## 安装与探测

    python -m pip install -r .ai/scripts/requirements-local.txt
    python .ai/scripts/control.py --help
    python .ai/scripts/control.py probe

Windows 上 agy 不在 PATH 时：

    python .ai/scripts/control.py probe --executable C:\path\to\agy.exe

探测只检查版本和帮助信息。真实登录、条款、隐私选项和文件夹信任需要在交互终端
中完成。

## 交互执行

    python .ai/scripts/control.py launch TASK-001 --approve --interactive --executable /path/to/agy

必须在真实终端中运行，不要重定向 stdin/stdout。启动后让 Executor 完成契约、测试
和 receipt，然后退出 agy，回到 Codex 执行 collect。

## 全权限模式

可信的一次性 Worktree 可以显式使用：

    python .ai/scripts/control.py launch TASK-001 --approve --interactive --full-access

该选项只向 agy 传递 permission-bypass 参数，不授予管理员权限，也不会移除 Scope、
Receipt、Review 或人工合并门。永远不要静默启用。

## 单任务流程

    python .ai/scripts/control.py validate TASK-001
    python .ai/scripts/control.py route TASK-001
    python .ai/scripts/control.py prepare TASK-001 --approve
    python .ai/scripts/control.py launch TASK-001 --approve --interactive
    python .ai/scripts/control.py status TASK-001
    python .ai/scripts/control.py collect TASK-001

prepare 会创建隔离 Worktree、记录基础提交和契约摘要，并写入上下文包。collect 会
检查 Git 祖先关系、分支状态、变更范围、回执身份、检查命令和验收证据。

## 证据和 Review

完整日志保存在 .ai/runtime/logs/TASK-ID/，默认先读取 compact JSON。缺失证据会阻塞；
collect 成功只会进入 REVIEW，不会独立生成 PASS，也不会自动合并。

Codex 应检查精确 Diff、Receipt、测试日志和验收条件，再写 receipt.qa.yaml 与
review.yaml。高风险任务还必须满足额外 Risk Gate 和人工审批。

## 故障恢复

无回执、权限阻塞或非零退出时：

    python .ai/scripts/control.py diagnose TASK-001

先检查运行记录、Worktree 和日志，再显式确认一次交互 recovery。禁止盲目重试或把
退出码 0 当作成功。REWORK 会保留之前尝试的证据。
