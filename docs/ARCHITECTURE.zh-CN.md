# 架构

[English](ARCHITECTURE.md)

## 本地控制路径

Codex Skill → control.py → 任务协议或本地 agy Adapter → 隔离 Git Worktree →
精简回执 → Codex 独立 Review → 人工合并。

所有执行模式共用同一状态机。控制器不调用远程 Reviewer、不运行后台调度器，
也不维护第二套任务数据库。

## 持久化协议层

- 项目需求、架构和 ADR；
- 结构化任务契约和状态目录；
- Risk Gate、Executor/QA Receipt；
- Git 历史、提交和 Worktree；
- REWORK 的尝试历史。

这是兼容边界，Executor Adapter 可以替换而不改变任务语义。

## 仓库目录

| 路径 | 职责 |
|---|---|
| .ai/config.yaml | 状态机、角色权限、Risk Gate、隔离和 Review 策略 |
| .ai/tasks/ | queue、active、review、blocked、done、archive |
| .ai/templates/task/ | 任务、上下文、回执、Review 和回滚模板 |
| .ai/scripts/control.py | 公开命令入口和路由 |
| .ai/scripts/ai.py | 校验、状态迁移和 Worktree 辅助 |
| .ai/scripts/delegate.py | agy 准备、启动、诊断和证据收集 |
| .ai/adapters/ | Executor 接口和 agy 参数 Adapter |
| .ai/runtime/ | 被忽略的锁、运行记录、日志和精简回执 |

## 状态生命周期

    queue/READY
       ├── start/prepare ──> active/IN_PROGRESS
       │                         ├── collect ──> review/REVIEW
       │                         └── failure ──> blocked/BLOCKED
       ├── validation failure ─> blocked/BLOCKED
       └── completed review ───> done/DONE ──> archive/ARCHIVED

执行尝试期间契约不能被修改。契约摘要会绑定审批文件、上下文包、回执和收集检查。
运行记录可丢弃；任务目录和 Git 历史才是恢复依据。

## 权限边界

Codex 负责架构、规划和独立验收；Antigravity 负责受限实现和证据；人类负责高风险
审批和最终集成。

缺失证据只能产生 UNKNOWN、NOT_RUN、NEEDS_ATTENTION 或 BLOCKED，不能推断为 PASS。
