# 项目说明

## 定位与交付物

本项目让 Codex 通过本地 agy 完成有界修改，默认使用一次 run 委派；需要审批和持久任务时再使用完整控制协议。
主要交付物为 `.agents/skills/antigravity-delegate/`，包含统一 CLI、任务与回执模板、
Antigravity CLI Adapter、PowerShell 多代理审阅脚本和操作说明。
版本以仓库根目录 `VERSION` 为准，当前文件内容为 `3.5.0-local`。

## 要解决的问题

将需求、可写范围、风险、执行、测试与独立验收关联到同一任务和同一代码快照，
避免把执行器退出、模型声明或配置默认值误认为实现成功。

## 使用者与范围

- 维护者或 Codex Root：创建任务、选择路由、检查证据并推进状态。
- 执行者：按契约实现，记录真实命令、变更和验收证据。
- 独立审查者：核验同一快照，返回发现及验收建议。
- 人类：完成适用的事前审批、残余风险接受和最终合并。

日常 run 无需初始化、模型角色或手工回执，在干净 HEAD 的工作树完成实现与检查，结果保存在 Git 公共元数据目录 agy-runs。
高级流程支持 `direct`、`delegated`、`approval_required`，按工作类型、判断强度、上下文连续性与验收确定性选择后端，沿用 schema v2。
整合上游 main `db1426b` 的 verify、分离预算和受控 partial 恢复；日常与高级检查共用进程执行模块。
本地委派使用用户已有的 agy 安装；任务事实保存在 `.ai/tasks/`，运行记录保存在
`.ai/runtime/`。不提供远程调度服务、Provider SDK、自动合并或自动用量采集。

## 约束与验收

Python CLI 依赖 Git 和 PyYAML；完整开发检查使用 Python 3.11+。
PowerShell 调度测试需 Windows PowerShell，真实委派另需可用的 agy 和终端环境。
交付以[需求](REQUIREMENTS.md)和[验收](ACCEPTANCE.md)中的可观察行为为准，
不以固定 Token 节省比例衡量成功。

## 事实来源

- [架构](ARCHITECTURE.md)：组件与状态边界。
- [实现](../../.agents/skills/antigravity-delegate/scripts/)及[测试](../../tests/)：实际行为。
- [任务目录](../tasks/)：持久任务、回执及审查结果。
- [当前状态](../../docs/STATUS.md)：2026-10-28 文件检查快照和验证缺口。
- [变更记录](../../CHANGELOG.md)、[ADR](../../.agents/skills/antigravity-delegate/references/decisions/)：版本与决策历史。

本说明描述当前外层仓库；嵌套的 `gpt-antigravity-dev-control/` 是另一个独立仓库，
未将其较新版本或未提交功能计入本项目能力。
