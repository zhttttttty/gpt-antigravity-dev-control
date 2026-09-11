# 统一控制流程

## 角色

- Codex Root（默认 Luna max）：需求、架构、任务契约、路由和集成。
- 原生角色（默认 Luna medium）：有界探索、实现、测试和调研。
- 独立 Reviewer（默认 Astra low）：返回发现与验收建议，由 Root 记录治理文件。
- Antigravity / Gemini：在 Worktree 中完成受限实现并生成执行证据。
- Human：高风险审批和最终合并。

## 1. 规划

建立最小可独立验收的任务，定义范围、风险、验收证据、检查命令和 execution.mode。

    python .ai/scripts/control.py create TASK-001 --title "有界修改" --objective "可观察的结果" --risk low --mode direct
    # 补齐范围、验收条件和检查命令后再验证
    python .ai/scripts/control.py validate TASK-001
    python .ai/scripts/control.py route TASK-001

## 2. 执行

使用 `create TASK-001 --title "有界修改" --objective "可观察的结果" --risk low --mode direct`
自动生成七个任务文件及身份，不覆盖已有任务。补齐范围、验收、检查、实际角色和基线；
初始验收列表为空，会被 validate/start 拒绝。YAML 结构化写入可能规范化注释和格式，
重复键会被拒绝。

start --worktree、worktree-create 和 prepare 前提交完整契约及预期修改，保持主控工作区
干净，配置的基线必须等于当前 HEAD。基线不存在、落后或 direct 分支已存在时会报错。

- direct：Root、人工或原生 Codex worker 在契约范围内实现。
- delegated：本地 agy 在准备好的任务 Worktree 中实现。
- approval_required：先将人工审批绑定到契约，再执行本地委派。

    python .ai/scripts/control.py start TASK-001 --worktree
    python .ai/scripts/control.py prepare TASK-001 --approve
    python .ai/scripts/control.py launch TASK-001 --approve --interactive
    python .ai/scripts/control.py collect TASK-001

Executor 只能修改可写范围，运行必要检查并写回执，不得自我批准或合并。

原生代理由 Root 通过真实派发启动，必须指定 Worktree、契约、文件归属和回执路径。
Root 显式检查范围与证据后迁入 REVIEW，不对原生任务运行 agy 的 collect。
合计并发和版本交接见 [混合执行](HYBRID_ORCHESTRATION.md)。

两条路径的活动状态都归主控仓库。生命周期命令在主控运行，也可指定
`control.py --repo <主控路径>`；Worktree 内任务文件只是已提交快照。
direct/native worker 返回证据，由 Root 写到 start 输出的主控回执路径，不修改
Worktree 内的任务状态。Root 核实同一快照的范围、变更和测试后显式执行
`transition TASK-001 REVIEW`。`status TASK-001` 显示主控状态及存在的 agy 运行记录。

direct/manual 的受控任务使用 `start --approval-file PATH` 绑定当前契约审批；start
还检查依赖和隔离要求。agy 写入其 Worktree 的 `.ai/runtime/delegation/receipt.executor.yaml`，
由 collect 验证并收集到主控任务目录。

## 3. 审查

Codex 独立阅读契约、精确 Diff、Executor Receipt、测试证据、架构和 ADR。
允许的结论是 PASS、PASS_WITH_NOTES、REWORK、BLOCKED。

Review 不应悄悄修改实现。REWORK 必须记录具体问题并保留之前的尝试证据。

只读 Reviewer 返回结果，由 Root 写 QA/Review。测试和审查必须针对同一快照，
包括未提交修改与新增文件；修复后必须重新验证受影响的证据。

DONE 校验 COMPLETE 执行回执、REVIEWED QA、独立真实身份、任务/版本/尝试绑定、
全部必要命令和验收证据、QA 风险/范围检查、一致的结论和摘要。架构偏离、未验证事项
阻止完成，中高风险还要求回归 PASS。启用的控制要求跨家族 PASS 或有记录的人工豁免、
有姓名和时间的合并审批、非空回滚计划。Root 仍需核实真实证据、豁免权限、回滚内容和
实现快照，结构化回执校验不能替代这些判断。

## 4. 收尾

QA、Review 和 Risk Gate 全部通过后：

    python .ai/scripts/control.py transition TASK-001 DONE

同步项目状态，保留证据，并明确合并已 Review 的提交。
REWORK 只执行一次 REVIEW 到 READY，控制器自动归档并增加 attempt。
再次使用 direct Worktree 时选择新契约分支，检查后保留或显式清理原干净工作区。

## 恢复

新会话依次读取项目状态、任务目录、回执、Review、Git Worktree、ADR 和本地运行记录。
安全恢复不依赖原始聊天记录。

旧版 direct 可能只在任务分支保存 active 状态。比较版本、attempt 和 Git Diff，保留
回执，再协调为主控内唯一任务目录。不要合并出重复目录或在活动未知时重派执行器。
runtime 日志属于恢复证据，清理前核实所属运行及 Worktree。

## 旧模板迁移

V1 布局的项目规格从 `.ai/*.md` 移到 `.ai/project/`；未完成的
`.ai/tasks/TASK-ID.md` 改为从 `.ai/templates/task/` 创建的任务文件夹，包含
task.yaml、brief、context、回执、review 和 rollback。放入对应状态目录并同步
PROJECT_STATE.yaml。保留已接受 ADR 和已归档报告，不重写历史证据。

派发前执行 `python .ai/scripts/control.py validate TASK-ID`；中高风险使用
Worktree。根 `.gitignore` 已排除 `.worktrees/` 和 `.ai/runtime/`，无需额外片段。
当前 schema v2 任务无需为混合路由做结构迁移；新模板使用 Plus 偏好，历史身份仍有效。
