# 快速开始

## 1. 安装与检查

离线配置检查需要 Python 3.11+。Codex 项目级配置需受信任的项目，实际角色和模型
仍需要运行记录核验。

    python -m pip install -r .ai/scripts/requirements-local.txt
    python .ai/scripts/control.py status
    python .ai/scripts/control.py check-orchestration

使用本地 Antigravity 时再运行 `python .ai/scripts/control.py probe`；它只检查
agy 是否能被发现以及帮助信息，不代表已经登录或模型调用成功。

## 2. 创建任务

先创建文件，再填写范围、验收、检查、实际角色和基线。空验收列表会阻止启动。

    python .ai/scripts/control.py create TASK-001 --title "有界修改" --objective "可观察的结果" --risk low --mode direct

    python .ai/scripts/control.py validate TASK-001
    python .ai/scripts/control.py route TASK-001

## 3. 直接执行

两条路径创建 Worktree 前都要提交完整契约，主控工作区保持干净，配置基线等于当前
HEAD。生命周期命令始终在主控仓库运行，Worktree 内任务目录仅为契约快照。

小型修改或委派成本高于实现成本时使用 direct：

    python .ai/scripts/control.py start TASK-001 --worktree

严格在任务范围内修改，填写 Executor Receipt，然后独立检查 Diff 和证据。

原生 worker 也沿用 direct 生命周期，派发时指定核实后的工作区、契约和回执路径。
Root 检查证据后显式迁入 REVIEW，不运行 agy collect。详见
[混合执行](HYBRID_ORCHESTRATION.md)。

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
[本地委派操作](LOCAL_DELEGATION.md) 创建绑定当前契约摘要的审批文件，
再传给 prepare。
direct/manual 的受控任务将审批文件传给 `start --approval-file PATH`。

## 6. 审查与收尾

写入 receipt.qa.yaml 和 review.yaml 后：

    python .ai/scripts/control.py transition TASK-001 DONE

只有所有 Risk Gate 通过后才能执行。项目状态同步和 Git 合并必须显式完成。
DONE 要求 COMPLETE 执行回执、REVIEWED QA、当前身份和完整证据。
回执路径与恢复见 [统一控制流程](CONTROL_WORKFLOW.md)。
