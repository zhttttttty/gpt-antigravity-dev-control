# 项目架构

## 运行结构

统一入口 `control.py` 优先提供日常 quick_run，同时保留核心协议和完整本地委派模块。控制器在主控仓库读写任务，
执行器在指定工作区实现，Root 核验实际改动；高级流程另外维护契约、独立 QA 和完成门。
该结构是本地 CLI 与文件协议，没有常驻服务或数据库协调层。

| 组件 | 职责 | 状态与输出 |
|---|---|---|
| `scripts/control.py` | 解析 `--repo`、分派命令、统一部分错误输出 | 不单独持久化状态 |
| `scripts/quick_run.py` | 一次需求、工作树、执行与调用者检查，无持久任务 | Git 公共元数据目录 `agy-runs/<id>/` |
| `scripts/init_project.py` | 初始化模板、任务目录、忽略规则，预检可选配置安装 | `.ai/`，可选 `.codex/` |
| `scripts/ai.py` | 创建、验证、迁移任务，管理 direct 工作树 | `.ai/tasks/<state>/<id>/`、`.worktrees/<id>/` |
| `scripts/task_data.py` | YAML、契约摘要、共享自适应路由、审批与 DONE 证据门 | YAML 文件和契约哈希 |
| `scripts/process_utils.py` | 共用 argv/shell 检查、日志、超时进程树清理 | 检查日志与真实退出码 |
| `scripts/delegate.py` | 准备、启动、verify、收集、受控恢复与诊断 | `.ai/runtime/logs/<id>/run-N/`、委派锁 |
| `scripts/adapters/antigravity_cli.py` | 探测 agy、构造参数、启动进程、解析事件及诊断 | 日志、事件、执行结果 |
| `scripts/check_orchestration.py` | 比较显式配置、角色与任务模板 | 离线一致性 JSON |
| PowerShell 脚本 | 独立审阅工作树、依赖调度、报告汇总与清理 | `sessions.json`、`summary.json`、`handoff.md` |

以上 `scripts/` 均位于 `.agents/skills/antigravity-delegate/` 内。

## 日常数据流

run 先验证请求和干净 HEAD，在 Git 公共元数据目录 agy-runs/<id>/workspace 创建隔离工作树，
调用现有 Adapter，读取简短 executor.json，再执行调用者显式提供的检查。前后观察实际 Git 变更，
返回结果文件、tracked.diff、全部未跟踪文件和检查日志，状态最多 READY_FOR_REVIEW。
run 不自动提交、合并或删除工作树，不进入 status 的持久任务队列。

## 高级协议数据流

1. `init` 复制缺失模板；`create` 生成 READY 草稿，规划者补齐范围、检查和验收。
2. `validate` 检查契约，`route` 区分风险审批与后端，按工作类型、判断、连续性和确定性选择执行者。
3. direct 使用 `start`；本地委派使用 `prepare`，创建工作树、上下文与运行记录，再 `launch`。
4. direct 证据交回主控；agy 写 IMPLEMENTED 回执，由独立 verify 运行获批分阶段检查后改为 COMPLETE/FAILED，再 collect。
5. 有效证据进入 REVIEW；独立审查后，Root 显式请求 DONE，控制器执行证据门检查。
6. DONE 不执行 Git 合并。人工处理最终合并和工作树收尾。

## 持久化与所有权

- 任务状态由目录及 `task.yaml.status` 共同表达，唯一活动副本在主控仓库。
- `PROJECT_STATE.yaml` 是人工维护的摘要；当前命令不自动同步它。`status --json` 直接读取任务目录，提供计数、进行中及全部未完成任务。
- `receipt.executor.yaml`、`receipt.qa.yaml`、`review.yaml` 绑定任务和 attempt；前两者还绑定 contract_revision。
- REVIEW → READY 会在 `history/attempt-N/` 保留旧证据并重置回执。
- direct 工作树为 `.worktrees/<id>/`；本地委派为 `.worktrees/<id>-N/`，两者命名与清理方式不同。
- task attempt 与 run-N 分别记录任务尝试和本地运行；新契约区分实现返工与基础设施重试，旧总尝试预算仍兼容。

## 公共契约与安全边界

公共接口包括[命令参考](../../.agents/skills/antigravity-delegate/references/cli.md)、
[任务协议](../../.agents/skills/antigravity-delegate/references/task-protocol.md)、
[回执协议](../../.agents/skills/antigravity-delegate/references/receipt-protocol.md)。
公共命令或持久状态语义变化需先记录 ADR，再更新测试与迁移说明。

Worktree 提供 Git 隔离，不提供操作系统沙箱。Scope 由准备和收集检查约束，
不能阻止具备系统权限的执行进程越界。`--auto-approve`（旧名 --full-access）只改变 agy 工具确认参数。
审批 YAML 是可审计记录，不是身份的密码学证明。
原生子代理继承父会话权限，代理文件内的 sandbox_mode 不构成独立只读边界。

## 不变量与限制

- ARCH-INV-001：执行成功声明不能替代独立 QA 或人工合并批准。
- ARCH-INV-002：禁止用执行工作树的旧契约覆盖主控活动状态。
- ARCH-INV-003：必要证据缺失时拒绝完成，返工保留既有证据。
- ARCH-INV-004：任务范围、审批、回执与 Git 快照需相互对应。

本地委派有排他锁；原生代理与 agy 的合计预算依赖 Root 协调，没有共享进程锁。
运行记录没有跨多个文件的事务恢复保证。实际配置、任务和验证缺口见[当前状态](../../docs/STATUS.md)。
