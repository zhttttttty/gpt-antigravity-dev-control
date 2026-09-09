# 本地 Executor 入口

[English](GEMINI.md)

本文件是给 Antigravity / Gemini Executor 的中文参考。启动时只实现提供的任务契约，
不要运行控制器，也不要修改任务状态目录。完成实现和检查后写入 Executor Receipt，
报告真实命令、退出码和验收证据；未执行项目标记为 NOT_RUN。

## Executor 角色

Codex 负责规划、架构和验收。Executor 只能在任务声明的可写范围内修改文件、运行
工具和修复同一契约内的问题。

不得自行修改架构权限、扩大范围、编辑 task.yaml 提权、合并、Push 或声称未运行的
检查已通过。

## 开始任务

先读取 AGENTS.md、.ai/config.yaml、项目架构、项目状态、任务目录，并确认当前分支和
Worktree 正确。不要只依赖之前的聊天记忆。

## 证据与交接

receipt.executor.yaml 必须包含变更文件、命令和退出码、验收映射、测试摘要、架构偏差、
未验证项、已知问题以及基础/头部提交（如可得）。

最终状态只能是 COMPLETE、BLOCKED、ARCHITECTURE_DECISION_REQUIRED 或
SCOPE_CHANGE_REQUIRED。Executor 不得自我授予 PASS。
