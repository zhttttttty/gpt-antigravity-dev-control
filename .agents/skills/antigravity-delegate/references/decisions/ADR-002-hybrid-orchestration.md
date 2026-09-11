# ADR-002：Plus 配置与两种执行后端

状态：按用户要求接受项目集成，2026-09-11。

## 背景

项目原生 Codex 配置与本地 agy Adapter 已共存，但默认值与原 Sol 角色规范不一致。
上游 [donvito/codex-astra-luna-orchestrator](https://github.com/donvito/codex-astra-luna-orchestrator/tree/014b1d7c48c39087beec8aa4f1ca022053ac17b3)
提供 Plus/Pro 配置、有界角色契约、摘要优先交接和用量测量方法。
本项目吸收这些思路，没有导入其安装器或源码。

## 决策

在 `.ai/config.yaml` 和 `.codex/` 使用 Plus 默认值：
Luna max 主控、Luna medium 执行、Astra low 审查。
模型名表示偏好，角色决定权限，实际执行身份写入回执。

保留一个可发现的委派 Skill。原生实现使用既有 direct 生命周期，
本地 agy 使用 delegated/approval_required。保留 schema v2、
回执格式、Adapter 与审查/合并门。

默认由 Root 协调两个活跃执行单元，原生打开线程也上限两个。
agy 调度器不共享此计数，不能宣称存在全局硬锁。
两条后端均要求同一 Worktree 一个写入者、验收同一精确快照。

## 取舍与验证

不导入每次委派强制 spawn_agent 的条件，agy 已是真实执行。
不跳过低风险独立审查，不因 Gemini 实现而豁免跨家族二次审查，也不限定只审查一次。
已有 Sol 任务记录继续有效，仅新任务模板调整默认值。
离线检查检测配置偏移，不能证明运行时工具可用或账户限制。
没有修改全局配置或安装快速服务档位。

成本、延迟和原生路由须在受信任项目实测，包含两侧用量来源、失败与审查成本。
回滚时共同恢复 `.ai/config.yaml`、`.codex/` 与新任务模板默认值；
已有任务与 agy 运行证据无需迁移。

## 历史验证记录

实现前已制定计划，随后完成配置一致化、路由/交接说明、离线检查及 CI 覆盖，
当时还交付了中英操作文档。已完成的一次性计划并入此 ADR，持续流程维护在规则与指南中。

初次实现验证通过 44 项 Python 测试；CLI 帮助完成后，七项配置与五项控制测试通过，
独立测试总数为原有 38 项加新增七项。fake-agy PowerShell 调度测试通过，
使用临时 LOCALAPPDATA 隔离测试锁。首次尝试无法访问真实用户锁路径，
不表示已证明另一个控制器正在运行。

Skill 元数据、链接、Python 编译、20 个 YAML/TOML 文件及空白检查通过。
当时未验证运行时模型路由、真实 agy 执行、全局覆盖或实际节省，也未实现合计进程锁。
这些是历史结果，不代表后续版本自动通过。
