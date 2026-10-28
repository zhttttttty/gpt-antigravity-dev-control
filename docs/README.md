# 文档与目录导航

## 当前文档

| 要做的事 | 阅读位置 |
|---|---|
| 安装、快速开始 | [中文 README](../README.zh-CN.md) / [English README](../README.md) |
| 日常一次委派，无需任务契约 | [run 使用指南](../.agents/skills/antigravity-delegate/references/quick-start.md) |
| 核对当前能力、配置缺口与未完成任务 | [当前状态](STATUS.md) |
| 查询命令参数、输出与副作用 | [命令参考](../.agents/skills/antigravity-delegate/references/cli.md) |
| 了解项目定位与组件 | [项目说明](../.ai/project/PROJECT.md)、[架构](../.ai/project/ARCHITECTURE.md) |
| 核对需求、交付标准与后续工作 | [需求](../.ai/project/REQUIREMENTS.md)、[验收](../.ai/project/ACCEPTANCE.md)、[工作索引](../.ai/project/ROADMAP.md) |
| 在对话中调用 | [调用提示词](../.agents/skills/antigravity-delegate/references/invocation-prompts.md) |
| 创建、执行、审查和恢复任务 | [统一控制流程](../.agents/skills/antigravity-delegate/references/workflow.md) |
| 使用本地 Antigravity | [委派操作](../.agents/skills/antigravity-delegate/references/delegation.md) |
| 选择执行模式 | [执行模式与能力映射](../.agents/skills/antigravity-delegate/references/execution-modes.md) |
| 角色、并发与文件所有权 | [编排规则](../.agents/skills/antigravity-delegate/references/orchestration.md) |
| 任务、回执与审查规则 | [任务协议](../.agents/skills/antigravity-delegate/references/task-protocol.md)、[回执协议](../.agents/skills/antigravity-delegate/references/receipt-protocol.md)、[审查契约](../.agents/skills/antigravity-delegate/references/review-contract.md) |
| 排查失败 | [故障恢复](../.agents/skills/antigravity-delegate/references/failure-recovery.md) |
| 测量成本、参与开发 | [用量测量](../COST_METRICS.md)、[贡献指南](../CONTRIBUTING.md) |
| 查看文件和文档整理结果 | [文件整理记录](maintenance/cleanup-2026-10-28.md)、[文档维护记录](maintenance/documentation-2026-10-28.md) |
| 查看工具修复与清理 | [基础优化](maintenance/optimization-2026-10-28.md)、[轻量化记录](maintenance/lightweight-plan-2026-10-28.md)、[当前整合记录](maintenance/upstream-integration-2026-10-28.md) |

生命周期只在 `workflow.md` 维护，原 `codex-workflow.md` 的恢复提醒已并入该文档。
Skill 的运行文档随 `.agents/skills/antigravity-delegate/` 一起分发，保持其内部相对路径。

## 目录用途

| 目录 | 内容与维护方式 |
|---|---|
| `.agents/skills/antigravity-delegate/` | 当前外层仓库的 Skill、实现、参考文档与分发模板 |
| `.ai/project/` | 根据外层实现补齐的项目说明、架构、需求、验收与后续工作 |
| `.codex/`、`.ai/config.yaml` | 本轮显式安装的默认模型配置，离线检查通过；实际模型可用性需另行确认 |
| `.ai/templates/` | 任务运行所需的项目模板；即使与 Skill 模板相同也保留 |
| `.ai/tasks/` | 高级流程的任务契约、回执和历史证据，按状态保存 |
| Git 公共元数据目录的 `agy-runs/` | 日常 run 的工作树、报告和检查结果，不进入持久任务队列 |
| `.ai/runtime/` | 本地运行及恢复记录，不纳入 Git；不能当作普通缓存删除 |
| `tests/` | 回归测试与独立测试夹具；相同模板用于验证，不作冗余删除 |
| `.worktrees/` | 外层仓库注册的 7 个工作树；其中 2 个含未提交修改，保留原路径 |
| `gpt-antigravity-dev-control/` | 独立 Git 仓库，HEAD 为 `db1426b`，含未提交修改和自己的 `.ai/`；不是可直接删除的副本 |
| `docs/archive/research/` | 原 `gpt-gemini/` 的历史方案、网页原件、上游参考快照 |

以上仓库和工作树状态为 **2026-10-28 整理时快照**。外层仓库 HEAD 为
`2e8706e`，与嵌套仓库版本不同；本次只整理外层文档和资料，没有合并这两个版本。

## 历史资料

[历史资料索引](archive/research/README.md)提供方案、原始网页和上游快照的入口。
历史资料记录当时的观点及配置，不作为当前模型能力、价格或配置兼容性的依据。

## 文档维护约定

- README 只承担定位、快速开始与导航；命令参数维护在 `references/cli.md`。
- 执行顺序维护在 `references/workflow.md`，字段与状态机维护在 `task-protocol.md`，证据门维护在 `receipt-protocol.md`。
- 本项目实际规格在 `.ai/project/`；Skill 的 `templates/project/` 保持可复制的通用模板。
- 状态页是有日期的快照。任务状态变更先写真实任务文件，再同步摘要；历史审查与 ADR 不重写。
- 自动化读取任务时使用 `control.py status --json`；人工摘要的空 active_tasks 不代表没有待审查或阻塞任务。
- 示例参数应对照解析器核验；配置偏好、离线测试、历史运行和当前实测分别标注。
