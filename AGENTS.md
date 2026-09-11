# 代理控制平面：通用入口

> 规范来源为 `.ai/`。本文件与其冲突时，以 `.ai/` 为准。

## 角色

- **Codex Root（默认 Luna max）**：项目管理、架构、规划与集成负责人。
- **原生代理（默认 Luna medium）**：有界探索、实现、测试与调研。
- **Antigravity / Gemini**：本地执行、开发及证据生成。
- **独立审查者（默认 Astra low）**：返回发现与验收建议。
- **人类**：拥有最终决定权。

模型偏好位于 `.ai/config.yaml`，更换模型不会改变权限。混合执行使用现有
`antigravity-delegate` Skill 和 `.ai/rules/ORCHESTRATION.md`。按需选择角色，
不要仅为转发 Antigravity 任务启动原生代理。Root 在独立证据齐备后记录审查与状态。

## 按需阅读

先读本文件、当前任务或请求，以及相关代码与测试。选择执行路径或调整角色时阅读
`.ai/config.yaml` 和编排规则；验收或受控变更时阅读风险与权限规则。

对已初始化的目标项目，读取其状态和相关项目规格、ADR。本控制器模板中的
`.ai/project/` 和项目状态文件含有接入占位内容，不代表实际产品需求。维护控制器时，
以 `docs/ARCHITECTURE.md` 和控制器测试为依据，按阶段读取
`docs/CONTROL_WORKFLOW.md` 中的正式流程。

## 必须遵守的规则

1. 执行者一次只实现一个任务契约。
2. 执行者不得修改 `task.yaml` 扩大自身权限。
3. 架构受控变更须先获得指定架构师或人类批准。
4. 声明不是证据，必须记录命令、结果和变更文件。
5. 执行者的 `COMPLETE` 不等于审查者的 `PASS`。
6. 高风险工作必须满足 `.ai/rules/RISK_GATES.md`。
7. 每个任务或尝试优先使用新的执行上下文。
8. 契约要求 Worktree 时必须隔离执行。
9. 必要证据不可用时记录 `NOT_RUN`、`UNKNOWN` 或 `BLOCKED`，不得推断成功。
10. 重要决定写入仓库文件，不能只留在聊天中。

## 架构门

未经明确授权，以下变更须暂停实现：数据库结构或迁移、公共 API、认证授权、
安全或秘密边界、核心框架或运行时或存储引擎、部署拓扑、新外部服务、
持久状态语义、重大依赖、大范围跨模块重写，以及兼容性策略。

返回以下协议标识并说明原因、选项、建议与影响：

```text
ARCHITECTURE_DECISION_REQUIRED
Task: <TASK-ID>
Reason: <原因>
Options: <方案>
Recommendation: <建议>
Impact: <影响>
```

## 任务状态机

```text
READY(queue) -> IN_PROGRESS(active) -> REVIEW(review)
REVIEW -> DONE(done)       # PASS / PASS_WITH_NOTES
REVIEW -> READY(queue)     # REWORK
REVIEW -> BLOCKED(blocked)
BLOCKED -> READY
DONE -> ARCHIVED(archive)
```

完整合法迁移见 `.ai/rules/STATE_MACHINE.md`。

## 完成标准

目标满足、验收证据齐全、必要风险门通过、范围合规、无未授权架构变更、
执行回执和 QA 完整，独立审查结论为 `PASS` 或 `PASS_WITH_NOTES`，
并完成项目状态协调后，任务才可视为 DONE。

## 文档语言

所有目录的 README 保留 `README.md`（英文）和 `README.zh-CN.md`（中文）。
其他维护文档仅保留中文，统一使用无语言后缀的 `.md` 文件名。
保留命令、字段、状态枚举和工具要求的文件名；更新引用时同时检查文件与章节链接。
