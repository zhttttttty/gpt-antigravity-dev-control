---
name: antigravity-delegate
description: "在原生 Codex 角色与本地 Antigravity CLI 之间分配有界开发任务并核验契约证据。适用于独立执行或原生/本地混合协作；简单修改直接处理。"
---

# 原生与 Antigravity 委派控制

本目录就是可复制的 Skill 包。控制器、任务模板、项目模板和参考协议都随 Skill
分发；目标业务仓库只保存由 `init` 生成的最小 `.ai/` 运行状态。旧项目中已有的
`.ai/scripts` 仍可兼容运行，但新项目不要复制整套控制平面。

## 首次接入

从 Skill 包运行：

    python .agents/skills/antigravity-delegate/scripts/control.py init --repo PATH

可选安装推荐的 Codex 角色配置：

    python .agents/skills/antigravity-delegate/scripts/control.py init --repo PATH --install-codex-profile

初始化只创建 `.ai/tasks`、`.ai/project`、`.ai/templates/task`、`.ai/state` 和被 Git
忽略的 `.ai/runtime`，不会覆盖已有文件。初始化后提交 `.ai` 中的契约模板与项目说明。

Codex 负责规划、路由、范围、验收和独立核验。此 Skill 提供确定性的本地执行协议，
不是远程调度器，也不能静默替换普通 Codex 子任务。

## 混合执行

选择或混用后端时阅读[编排规则](references/orchestration.md)。
使用 `.ai/config.yaml` 模型偏好及 `.codex/agents/` 角色定义：
默认 Luna max 主控、Luna medium 原生执行、Astra low 独立审查。
用户或运行时的明确选择优先，报告实际使用情况。

按范围和协调成本选择 Root 直接执行、原生 Codex 或本地 agy。
原生任务使用真实 `spawn_agent` 和 direct 协议，agy 使用 `control.py`；
不要仅为转发 agy 启动原生代理，也不要对原生任务套用 agy 的 launch/collect。

仅 Root 管理派发，提供契约、文件归属、精确 Worktree/版本、检查项和回执路径。
原生与 agy 合计默认两个执行单元，由协调者管理，没有跨运行时硬锁。
同一 Worktree 只有一个写入者，实现、测试和审查针对同一快照。
返回精简证据和完整日志路径，如实报告不可用工具、失败与替代路径。

## 选择本地执行

Codex 可以自动选择本 Skill；启动 Antigravity 前说明路由决定。

- `direct`：小型修改、简短文档或配置、边界未明确的探索，或需要持续交互推理的工作。
- `delegated`：有界多文件实现、补充测试、独立重构或可通过命令核验的仓库审查。
- `approval_required`：架构、认证、安全、迁移、部署、计费、破坏性或其他高风险工作。
- 探测失败或准备与审查成本可能超过实现成本时，保持直接执行。

自动选择 Skill 本身仅授权规划与只读探测。变更、权限绕过或受控执行前，落实任务
要求的审批；已有明确用户授权按当前会话范围适用。

## 本地协议

1. 每次运行前探测实际可执行文件：

       powershell -NoProfile -ExecutionPolicy Bypass -File .agents/skills/antigravity-delegate/scripts/probe_agy.ps1 -Executable agy -OutputDir .ai/runtime/logs/probe

   读取 `capabilities.json`，不要假设参数、模式、登录或代理列表命令可用。
   控制器路由不是 `agy --mode`。全访问映射为省略 `--sandbox`；
   自动批准对应 `--dangerously-skip-permissions`；只读审查用 `--mode plan`，
   实现使用帮助中确认的编辑模式。全访问不会扩大契约。
2. 单任务生命周期用 `control.py prepare` 创建 Worktree；
   独立审查分片用 `create_review_worktree.ps1`，不要为同次执行创建两套目录。
   使用返回的路径和分支。脏基线须按任务授权处理，不能自行假定允许。
3. 单任务使用统一 CLI；多个有界分片阅读[协作协议](references/coordination-protocol.md)，
   定义无环 `depends_on` 图并调用 `launch_agents.ps1`。扣除原生任务已占容量；
   三到四个 agy 分片须先显式协调项目预算。启动器从两个开始，成功后才扩容。
   独立写入使用独立 Worktree；本地启动器只约束自身任务，最多重试一次，首次失败后降为单并发。
4. 固定输出目录保存 `sessions.json`、逐代理报告、stderr、执行日志和能力记录。
   先运行 `collect_reports.ps1` 阅读摘要，再按需打开完整证据。
5. 独立核验全部 P0/P1 的路径行号、测试、验收和覆盖计数及 Worktree 状态，
   将发现标记为确认、条件成立或假设。收集不会自动合并或迁入 DONE。
6. 使用 `cleanup_worktree.ps1` 清理；只有干净 Worktree 可移除，强制清理需明确批准。

## 仓库入口

    python .agents/skills/antigravity-delegate/scripts/control.py <command>

用 `create TASK-ID --title ... --objective ...` 生成任务，补齐并验证契约。
创建 Worktree 前提交契约，基线必须等于 HEAD。状态命令在主控仓库执行，
Worktree 内任务文件为快照。原生/direct 证据经 Root 写入输出的主控回执路径。
DONE 要求当前 COMPLETE/REVIEWED 回执和已核验的证据。

按当前阶段阅读[统一控制流程](references/workflow.md)、
[执行模式](references/execution-modes.md)、[审查契约](references/review-contract.md)
或[故障恢复](references/failure-recovery.md)；状态和回执说明见
[任务协议](references/task-protocol.md)、[回执协议](references/receipt-protocol.md)
与[Codex 流程](references/codex-workflow.md)。

修改配置默认值后运行 `control.py check-orchestration`，它只检查仓库一致性。
实际模型和角色以运行证据为准，不能由 TOML 推断。保留 Skill 名称，兼容
`$antigravity-delegate` 调用。

本 Skill 自带控制器和模板；执行时通过 `--repo` 指向目标仓库。目标仓库必须是 Git
仓库。协议或入口缺失时报告前置条件；只有显式调用 `init` 才会生成运行状态。
