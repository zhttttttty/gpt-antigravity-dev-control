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

初始化创建最小 `.ai/` 状态，并可能补充根 `.gitignore`；默认不覆盖已有模板。
先确认真实仓库路径与 Git 根，再初始化；Windows 非 ASCII 路径的验证与恢复见
[故障恢复](references/failure-recovery.md)。初始化后检查 Diff，再提交契约模板与项目说明。

Codex 负责规划、路由、范围、验收和独立核验。此 Skill 提供确定性的本地执行协议，
不是远程调度器，也不能静默替换普通 Codex 子任务。

## 混合执行

选择或混用后端时阅读[编排规则](references/orchestration.md)。
需要可复制的完整流程、分阶段和高风险调用模板时阅读
[调用提示词](references/invocation-prompts.md)。
使用 `.ai/config.yaml` 模型偏好及 `.codex/agents/` 角色定义：
默认 Sol high 作为唯一规划与最终决策主控，Luna high 负责有界只读探索、独立测试与
审查，Antigravity 作为有界任务的默认实现后端。原生 Luna worker 只在 agy 不可用且
Root 明确记录原因并批准切换后端时作为回退。
用户或运行时的明确选择优先，报告实际使用情况。

小型低风险修改可由 Root 直接执行；边界明确、可由命令验收的多文件实现默认使用本地 agy。
高判断力审查、正确性证明、微妙语言语义与安全结论默认交给 Sol/Luna；agy 可做首轮扫描，
但其 PASS 不能成为最终结论。把机械实现、补测试、样板代码和独立重构优先交给 agy，
把契约、反例设计、独立审查和最终裁决留给原生角色。
Luna 的调查与审查输出是证据和建议，不能代替 Sol 的任务契约或最终结论。
原生任务使用真实 `spawn_agent` 和 direct 协议，agy 使用 `control.py`；
不要仅为转发 agy 启动原生代理，也不要对原生任务套用 agy 的 launch/collect。

仅 Root 管理派发，提供契约、文件归属、精确 Worktree/版本、检查项和回执路径。
原生与 agy 合计默认两个执行单元，由协调者管理，没有跨运行时硬锁。
同一 Worktree 只有一个写入者，实现、测试和审查针对同一快照。
返回精简证据和完整日志路径，如实报告不可用工具、失败与替代路径。

## 选择本地执行

Codex 可以自动选择本 Skill；启动 Antigravity 前说明路由决定。

- `direct`：小型修改、简短文档或配置、正确性/安全审查、微妙运行时语义，或需要持续交互推理的工作；原生 worker
  仅作为明确批准的故障回退，不能静默替代 agy。
- `delegated`：有界多文件实现、补充测试、独立重构或可通过确定性命令验收的批量工作。
- `approval_required`：架构、认证、安全、迁移、部署、计费、破坏性或其他高风险工作。
- 探测失败时先停止派发并诊断；若用户指定 Antigravity，不得以成本或超时为由静默
  切换 Codex 编码。小型低风险任务可按已授权范围直接处理。

自动选择 Skill 本身仅授权规划与只读探测。变更、权限绕过或受控执行前，落实任务
要求的审批；已有明确用户授权按当前会话范围适用。

## 本地协议

1. 每次运行前探测实际可执行文件：

       powershell -NoProfile -ExecutionPolicy Bypass -File .agents/skills/antigravity-delegate/scripts/probe_agy.ps1 -Executable agy -OutputDir .ai/runtime/logs/probe

   读取 `capabilities.json`，不要假设参数、模式、登录或代理列表命令可用。
   控制器路由不是 `agy --mode`。全访问映射为省略 `--sandbox`；
   自动批准对应 `--dangerously-skip-permissions`（control.py 使用 `--auto-approve`；
   `--full-access` 仅为兼容别名，不是沙箱开关）；无头任务若需要读文件或运行命令，
   未授权自动批准时可能以 exit 0 返回权限拒绝，必须检查诊断与实际输出。
   只读审查用 `--mode plan`，
   实现使用帮助中确认的编辑模式。权限绕过须绑定具体任务/Worktree 的明确授权；
   Worktree 不是操作系统隔离。帮助、模型列表或短 READY 请求不证明账号身份、余额
   或长任务必然可完成。
2. 单任务生命周期用 `control.py prepare` 创建 Worktree；
   独立审查分片用 `create_review_worktree.ps1`，不要为同次执行创建两套目录。
   使用返回的路径和分支，以及 run.json 的不可变 base_commit；派发时附实际回执模板
   和规范字段，见[回执协议](references/receipt-protocol.md)。脏基线须按任务授权处理。
3. 单任务使用统一 CLI；多个有界分片阅读[协作协议](references/coordination-protocol.md)，
   定义无环 `depends_on` 图并调用 `launch_agents.ps1`。扣除原生任务已占容量；
   三到四个 agy 分片须先显式协调项目预算。启动器从两个开始，成功后才扩容。
   独立写入使用独立 Worktree；先串行 prepare，再按剩余容量并行编码，最后串行 collect。
   不要并行运行持同仓锁的 control.py launch。启动器重试仍须计入已批准任务预算，
   无剩余预算时 max_retries 为 0；首次失败后降为单并发。
4. 固定输出目录保存 `sessions.json`、逐代理报告、stderr、执行日志和能力记录。
   多分片先运行 `collect_reports.ps1`；单任务读 run.json 和原始回执。
   启动器 COMPLETE/exit 0 只证明进程结束，不证明任务验收；空 stdout、权限自动拒绝、
   缺少回执或格式不符均不得计为成功。
5. agy 完全退出后再串行启动 Luna tester/reviewer；独立核验全部 P0/P1 的路径行号、
   测试、验收和覆盖计数及 Worktree 状态，
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
与[Codex 流程](references/codex-workflow.md)。提示词示例见
[调用提示词](references/invocation-prompts.md)。

修改配置默认值后运行 `control.py check-orchestration`，它只检查仓库一致性。
实际模型和角色以运行证据为准，不能由 TOML 推断。保留 Skill 名称，兼容
`$antigravity-delegate` 调用。

成本比较必须包含失败尝试、编排和独立审查；CLI 输出字节不是 Token。Provider 未返回
用量时保持 UNKNOWN，只能把账号额度百分比作为受其他会话干扰的粗粒度观测，不能宣称
精确节省比例。优先以“通过独立审查的任务/返工次数/总耗时”比较后端，而非只看首个 exit 0。

修改 canonical Skill 后，用 `scripts/check_skill_sync.py --other PATH` 对实际安装副本做
换行归一化后的清单/内容核对；任何缺失、额外或内容差异都先同步再宣称新版已生效。
忽略 `__pycache__`、`.pyc` 等运行缓存，不把缓存差异当作协议漂移。

本 Skill 自带控制器和模板；执行时通过 `--repo` 指向目标仓库。目标仓库必须是 Git
仓库。协议或入口缺失时报告前置条件；只有显式调用 `init` 才会生成运行状态。
