# 当前仓库状态

本页是 **2026-10-28** 根据本地文件和只读命令生成的说明，不自动更新任务状态。
版本为 `3.5.0-local`，外层 HEAD 仍为 `2e8706e`，当前未提交源码已整合 GitHub main `db1426b`；不能用 HEAD 原始内容代表当前工作区。

## 已存在的能力与验证边界

| 内容 | 文件检查结论 |
|---|---|
| 统一 CLI、schema v2、direct/委派、证据门 | 有实现及离线回归测试；日常 run 保留，完整流程已整合上游自适应路由、verify、分离预算及受控恢复 |
| Skill 内 Codex 配置与角色 | 高级流程的可选模板，外层已安装；run 不依赖这些模型设置 |
| 外层 `.ai/config.yaml`、`.codex/` | 已安装默认配置；外层根目录 check-orchestration 实际 PASS/退出码 0 |
| `tests/fixtures/control-project/` | 含配置样例，可用于离线一致性检查；显式对夹具执行 status 会因不是 Git 根而拒绝 |
| `.ai/state/PROJECT_STATE.yaml` | 保留人工 READY / 空 active_tasks；当前没有 IN_PROGRESS，此空列表不构成错误。全部未完成任务由 status --json 实时读取 |
| 真实 agy、认证、模型路由、额度及成本 | 本轮未调用真实 Provider；模型可用性、额度和成本仍需实际验证 |

此前文档整理识别出缺少配置，本轮已通过安全安装补齐，并验证完整安装、重复安装和冲突保护。
新增 `status --json` 区分 IN_PROGRESS 与全部未完成任务；未据此更改已有任务或人工摘要。

## 日常入口与权限

run 为普通任务提供一次委派，不需要 init 或手工回执；创建独立工作树，检查由调用者指定，
状态最多 READY_FOR_REVIEW。完整清单保存在 Git 公共元数据目录 agy-runs 下，不计入下面的持久任务状态。
原生代理的无效 sandbox_mode 已从分发、安装文件和夹具中移除，检查器拒绝无效会话字段覆盖。
真实权限继承父会话，不将“不编辑”指令视作系统沙箱。
当前 run 和 verify 共用检查执行模块；默认 argv，日常 shell 需 --shell-checks，高级 shell 必须在获批契约声明。

## 持久任务快照

`control.py status` 显示 3 项 REVIEW、1 项 BLOCKED，没有 IN_PROGRESS 或 DONE。
目录状态不是操作系统进程检测，不能据此断言没有运行中的执行器。

| 任务 | 目录状态 | review.yaml 结论 | 现有记录的含义 |
|---|---|---|---|
| [TASK-CONTROL-001-CLASSIFICATION](../.ai/tasks/blocked/TASK-CONTROL-001-CLASSIFICATION/) | BLOCKED | BLOCKED | 两次尝试用尽，未提交修改保留；未授权新一轮恢复或合并 |
| [TASK-ROUTE-001-END-TO-END](../.ai/tasks/review/TASK-ROUTE-001-END-TO-END/) | REVIEW | REWORK | 旧快照的控制器身份校验存在问题，其他任务的修复不能改写其旧结论 |
| [TASK-ROUTE-002-SMOKE](../.ai/tasks/review/TASK-ROUTE-002-SMOKE/) | REVIEW | PASS_WITH_NOTES | 存在历史真实 smoke 记录；尚未 DONE 或自动合并 |
| [TASK-ROUTE-003-IDENTITY-BOOTSTRAP](../.ai/tasks/review/TASK-ROUTE-003-IDENTITY-BOOTSTRAP/) | REVIEW | PASS | 身份修复已获既有审查认可，最终合并与适用完成门仍未满足 |

表中执行和测试结果来自任务内既有回执与审查记录，本次未重新验证历史实现快照。

## 多个代码目录

外层根目录与 `gpt-antigravity-dev-control/` 为不同 Git 仓库，嵌套仓库 HEAD 为
`db1426b`，含未提交修改。外层另有 7 个注册工作树，其中 2 个含未提交修改。
本文和项目说明只描述外层仓库，不将嵌套仓库后续版本混入当前功能清单。

选择版本、继续旧任务、运行时配置核验和实际成本测量仍属于后续工作，见[工作索引](../.ai/project/ROADMAP.md)。
文档组织方式见[目录导航](README.md)，此前文档验证见[文档维护记录](maintenance/documentation-2026-10-28.md)，此前实现与清理见[优化记录](maintenance/optimization-2026-10-28.md)，此前轻量化见[计划及结果](maintenance/lightweight-plan-2026-10-28.md)，当前见[上游整合记录](maintenance/upstream-integration-2026-10-28.md)。
