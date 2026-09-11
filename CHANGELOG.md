# 变更记录

## 3.2.0-local - 2026-09-11

- 文档语言统一：所有 README 保留中英双版本，其余维护文档使用中文内容和固定 `.md` 路径；
  删除重复的非 README `.zh-CN.md` 文件并修复引用。
- DONE 对所有风险等级校验当前执行/QA 证据，保留高风险控制。
- 原生/direct 状态统一归主控，严格检查基线，新增任务创建和共享 YAML/审批/证据校验。
- 重复流程缩为兼容索引，上下文改为按相关性读取。

- 同步架构、生命周期和快速开始文档，明确两条执行路径、重试、版本和状态所有权。
- 旧模板迁移并入统一控制流程，已完成计划的证据并入 ADR-002；删除被替代的迁移指南、忽略片段和一次性计划，保留有效兼容模块。

- 统一 Plus 项目配置：Luna max 主控、Luna medium 执行、Astra low 审查。
- 扩展现有 Skill 的原生/本地路由、版本交接和主控合计并发规则，保留任务协议、agy Adapter、回执与风险门。
- 新增 `control.py check-orchestration` 离线一致性检查、回归测试和 CI 检查。
- 记录上游来源、运行时验证限制和双 Provider 用量比较方法。

## 3.1.2-local - 2026-09-09

- 将 direct、delegated、approval_required 统一到一套任务协议。
- 新增 .ai/scripts/control.py 作为主要 CLI，保留 ai.py 和 delegate.py 兼容入口。
- 删除重复的 .ai/VERSION，根目录 VERSION 成为唯一版本源。
- 将文档改为统一工作流、执行模式和技术说明。
- CI 只验证统一 CLI，并加入门面路由测试。

## 3.1.1-local - 2026-09-09

- 将远程 API Adapter、SQLite 协调层、CLI、配置和 CI 检查移到归档分支。
- 将本地委派作为主工作流，保留任务、风险、回执和 Worktree 保证。
- 更新安全、贡献指南、Issue 和 Pull Request 模板。

## 3.1.0-local - 2026-09-09

- 增加继承真实终端的交互启动和一次明确确认的恢复，每次启动保留独立日志；
  重定向的交互会话在改变状态前被拒绝。
- 将权限拒绝或缺少回执的退出识别为 NEEDS_ATTENTION，提供脱敏诊断分类并加强
  Worktree 执行约束。
- 记录一次人工辅助的真实任务验证及未解决的无人值守限制。
- 增加显式 `--full-access --approve`，仅用于可信一次性 Worktree；默认仍需交互确认。
- 增加本地路由、Worktree 准备、agy Adapter、精简回执、仓库 Skill 和用量测量指南。
- 增加离线 Git/进程集成测试；不提供自动合并或无限重试。

## 3.0.0-lite - 2026-08-30

- 曾加入 SQLite 运行协调、Lease/Heartbeat、Antigravity 执行 Adapter、
  GPT-5.6 Sol 审查 Adapter、自动 READY 到审查循环及高风险人工批准门。
- V2 任务契约、回执、风险门、ADR、状态目录与 Worktree 隔离继续作为协议层。

## 2.0.0 - 2026-08-30

- 增加结构化 `task.yaml`、目录状态机、三级风险门、Executor/QA Receipt、
  `GEMINI.md` 入口、Git Worktree 隔离、架构权限门、REWORK 历史和纯 Python 辅助脚本。
