# 文档索引

[English](README.md)

本项目围绕一套本地任务控制流程组织。以下文档分别说明如何使用，以及内部如何实现。

## 使用项目

1. [快速开始](QUICK_START.zh-CN.md)：安装、创建任务、路由、执行、验收和关闭。
2. [统一控制流程](CONTROL_WORKFLOW.zh-CN.md)：规划、执行、Review、收尾和恢复。
3. [本地委派操作](LOCAL_DELEGATION.zh-CN.md)：agy 探测、交互审批、全权限、恢复和回执。
4. [执行模式](EXECUTION_MODES.zh-CN.md)：direct、delegated、approval_required 的选择。

## 理解实现

1. [架构](ARCHITECTURE.zh-CN.md)：控制层、权限边界、状态所有权和失败行为。
2. [当前限制](LIMITATIONS.zh-CN.md)：仍保持本地或人工处理的能力。
3. [用量测量](../COST_METRICS.zh-CN.md)：用实际数据比较直接执行和委派执行。
4. [风险门](../.ai/rules/RISK_GATES.md)：低、中、高风险的证据与审批要求。

## 仓库约定

- .ai/ 保存任务契约、状态目录、模板、规则和本地运行记录。
- .ai/scripts/control.py 是主要命令入口。
- ai.py 与 delegate.py 是入口后的兼容模块。
- GEMINI.md 描述受限 Executor 的职责。
- CONTRIBUTING.md 和 SECURITY.md 分别说明开发和安全要求。
