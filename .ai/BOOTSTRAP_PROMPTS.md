# 启动提示词

## Codex Root：初始化项目

```text
阅读 AGENTS.md、.ai/config.yaml，以及 .ai/project/、.ai/rules/、.ai/state/。
担任项目经理与系统架构师。
根据用户说明和现有仓库，初始化 PROJECT.md、REQUIREMENTS.md、ARCHITECTURE.md、
ROADMAP.md、ACCEPTANCE.md 和 PROJECT_STATE.yaml，暂不实现应用代码。
识别架构不变量、保护区域、关键风险和第一个可独立验收的任务。
从任务模板建立 queue 中的任务，核实风险、权限、范围和验收证据明确。
```

## Codex Root：创建下一任务

```text
阅读相关 .ai/ 规范文件和当前 Git/项目状态，创建最小可独立验收的 READY 任务。
使用结构化 task.yaml，按影响而非信心评估风险。
明确可写/保护范围、权限、隔离、验收条件和必要检查，暂不实现代码。
```

## Antigravity：执行指定任务

```text
阅读 GEMINI.md、AGENTS.md、.ai/config.yaml、相关项目架构、项目状态和任务目录。
仅在指定 Worktree 执行该任务，不改变范围或架构权限。
运行必要检查，在指定路径填写 receipt.executor.yaml，记录真实证据。
遇到架构或范围门时停止并返回对应升级标识，不自我批准或合并。
```

## 独立审查者：验收

```text
担任独立审查者，阅读契约、精确 Git Diff/提交范围、执行回执、测试证据、
相关架构/ADR 和风险门。返回发现及证据，由 Root 写 receipt.qa.yaml 和 review.yaml。
结论为 PASS、PASS_WITH_NOTES、REWORK 或 BLOCKED，审查时不悄悄修改实现。
需要 REWORK 时提出边界明确的问题，由 Root 按既有生命周期处理。
```
