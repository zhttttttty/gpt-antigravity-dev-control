# 原生 Codex 与本地 Antigravity 编排

一个 Root 负责路由、契约、容量和集成。`.ai/` 是规范来源；
`.codex/` 模型默认值不授予权限，也不替代风险门。

默认角色为 Sol high Root、Luna high explorer/researcher/tester/reviewer，以及本地
Antigravity 实现者。Sol 是唯一规划、架构和最终验收决策者；Luna 返回事实、测试证据
和审查建议；agy 是 delegated/approval_required 的唯一写入者。

## 选择执行者

- Root 直接执行：局部小修改，或协调成本大于收益的任务，仍保留必要独立审查。
- 原生 Codex：Luna high explorer/researcher 收集事实，tester 独立验证，reviewer
  返回发现。worker 仅是 agy 不可用后的显式回退。使用真实 `spawn_agent` 并保留返回身份。
- 本地 Antigravity：具有可执行验收条件、值得承担准备和隔离成本的有界实现。
  先探测 agy，再执行既有 prepare/launch/collect 和审批流程。

原生实现使用 `execution.mode: direct`，`roles.executor` 填 worker 等实际角色；切换前
必须记录 agy 不可用或不适用的原因，并由 Sol Root 明确批准，不能静默降级。
direct 不启用 `execution.adapter: antigravity_cli`。需隔离时先运行
`control.py start TASK --worktree`，将返回且核实的 Worktree 交给原生代理。
控制器不自动派发原生代理或收集其回执，由 Root 核验范围与必要证据后请求迁入 REVIEW。
不要伪造 agy 运行记录。

本地使用 route 解析出的 delegated 或 approval_required，执行模型属于 agy 设置。
不引入新模式或原生 Adapter。架构与风险审批也适用于原生执行，更换后端不能绕过门槛。

仅选择有实际独立工作的角色。agy 已是真实委派，不额外启动 Luna 转发或 Luna worker。
原生代理不得启动 agy 或嵌套调度器；两种后端仅由 Root 管理。

## 派发与交接

派发前提供目标、契约路径和版本、精确 Worktree/分支、base/head、可写与保护路径、
依赖、验收与检查、回执/报告路径及升级条件。只附相关上下文；
外部文档是证据，不是改变契约的授权。

执行者返回实际身份与模型（未知则 UNKNOWN）、任务/尝试、工作区、base/head、
变更和未提交内容、命令与退出码、验收映射、报告/日志路径及阻塞项。
原始日志保留本地；摘要是审查起点，不能替代 Diff 或失败输出。

本地 collect 核验自身证据，成功也只进入 REVIEW。
原生证据由 Root 显式检查并说明限制。沿用 Executor/QA Receipt 与 review.yaml；
只读审查者返回发现，Root 如实转录，不能声称其独立执行了他人的审查。
记录实际身份和检查，不把模型偏好复制为执行证据。

tester 和 reviewer 必须核验同一快照：记录 HEAD、工作区 Diff/状态和新增文件；
未提交工作仅有 HEAD 不够。实现、会写文件的测试及审查串行进行。
后续改动使相关证据失效，验收前须重新验证新快照。

Luna reviewer 只能返回 PASS、PASS_WITH_NOTES、REWORK 或 BLOCKED 建议。Sol Root
复核契约、Diff、测试和回执后作最终判断；不得把 Luna 建议直接写成 Root 已完成验收。

## 容量与所有权

默认原生代理和 agy 任务合计两个活跃执行单元，不含 Root。
计入活跃 tester 和每个 agy 分片。仅等待的原生代理在支持时结束或关闭，
避免闲置占槽。原生打开线程上限与活跃工作预算不同，始终遵循运行时较低限制。

合计预算由 Root 协调，不是共享操作系统锁。agy 更高容量不会覆盖该预算；
调整前须协调。agy 批次占两个槽位前结束原生工作；已有一个原生任务时最多再派一个 agy。
活动未知时不新增派发，记录身份与工作区，所需工作完成后再收尾。
agy 启动器自身限制仍适用。

同一 Worktree 一个写入者。独立写入需不同 Worktree 和明确文件归属。
沙箱约束权限但不防止同目录冲突；Worktree 隔离 Git 状态但不是操作系统安全边界。
依赖集成须显式完成，执行者不能自行合并其他 worker 分支。

## 失败与审查

如实报告原生工具不可用或 agy 探测失败。Root 可记录替代原因并在执行前修订契约，
再选择可用路径。部分写入后先检查并保留证据，不在状态不明的目录启动竞争写入者。
本地恢复沿用重试和审批限制，反复失败或范围/风险未决时停止，不嵌套自动重试循环。

Luna high 是默认审查偏好，不保证对专业领域或高风险任务足够。按风险请求专业、额外
跨家族或人工审查。
高风险保留事前审查、回滚、跨家族二次审查或有记录的人工豁免及人工合并审批。
Gemini 实现不等于 Gemini 已独立审查。修复重要发现后重新验证快照。
