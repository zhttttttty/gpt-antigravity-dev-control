# 变更记录

[English](CHANGELOG.md)

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

- 增加交互式启动、一次确认恢复、权限诊断和精简回执。
- 增加显式的 full-access 选项，默认仍然需要交互确认。
- 增加本地路由、Worktree 准备、agy Adapter、离线测试和 Codex Skill。

更早版本记录保留在英文变更记录中，便于追溯历史实现。
