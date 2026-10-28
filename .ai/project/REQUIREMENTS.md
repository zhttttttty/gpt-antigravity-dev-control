# 项目需求

以下编号描述当前实现的行为约束，不将历史计划或模板偏好当作已验证能力。

| 编号 | 需求 | 验收信号与实现证据 |
|---|---|---|
| FR-001 | 一个统一 CLI 分派初始化、核心任务及本地委派命令 | `control.py` 与 `tests/test_control_cli.py` |
| FR-002 | 在目标 Git 项目初始化最小运行目录，已有任务和项目模板不被普通 init 覆盖 | `init_project.py` 的缺失文件复制逻辑；完整 profile 默认拒绝冲突，仅显式覆盖参数可替换配置 |
| FR-003 | 任务按 schema v2 验证；创建结果必须补齐后才能执行 | `ai.py` 的 create/validate，`tests/test_task_protocol.py` |
| FR-004 | 状态迁移符合允许边，REWORK 保留历史 | `ai.py` 的 ALLOWED/transition，协议回归测试 |
| FR-005 | 风险及 authority 标志触发事前审批，本地委派验证契约绑定 | `task_data.py` 的 require_approval，共享 route_task 与 delegate.py 的 prepare |
| FR-006 | 本地委派使用已提交的当前基线、独立工作树和有界上下文 | `prepare` 拒绝脏主控、过期基线及超出 32,000 UTF-8 字节的上下文 |
| FR-007 | 收集时核验回执、实际 Git 快照、范围与必要证据 | `delegate.py` 的 collect，`tests/test_local_delegation.py` |
| FR-008 | DONE 要求当前执行回执、独立 QA、一致结论和适用风险门 | `task_data.py` 的 done_errors，协议回归测试 |
| FR-009 | 多代理启动器校验依赖、并发、工作树写入互斥并生成报告 | `launch_agents.ps1`、`collect_reports.ps1`、`tests/test_multi_agent_protocol.ps1` |
| FR-010 | 配置检查只报告离线一致性，缺失或漂移时失败 | `check_orchestration.py`、`tests/test_orchestration_config.py` |
| FR-011 | 显式目标仓库不得静默回落到父仓库，非法全局参数无 traceback | `tests/test_control_cli.py` 的边界测试 |
| FR-012 | 提供只读实时 JSON 总览，校验基本身份及目录一致性 | `status --json` 与 CLI 回归测试 |
| FR-013 | 普通任务无需初始化或持久契约即可隔离委派，保留实际改动和调用者检查 | `quick_run.py` 与 `tests/test_quick_run.py` |
| FR-014 | 配置检查不得将代理文件的无效字段当作权限隔离 | 移除代理 sandbox_mode，拒绝不会生效的父会话设置覆盖 |
| FR-015 | 高级任务的 IMPLEMENTED 由独立控制器 verify 验证，分阶段执行并绑定审批 | 上游验证用例及新增超时短路测试 |
| FR-016 | 日常与高级检查默认 argv，共享超时进程树清理并复核工作区 | process_utils 与跨入口测试 |
| FR-017 | 路由与 direct 启动保持一致，显式审批不得因自适应路由降低 | route_task、start 与衔接测试 |

## 非功能需求

- NFR-001：完整开发检查使用 Python 3.11+、Git、PyYAML；Windows 专属协议另行验证。
- NFR-002：不要求 Provider SDK 或远程审查服务。测试使用临时 Git 仓库和伪执行器。
- NFR-003：摘要优先，原始日志和恢复证据保留本地；不把输出字节当成计费 Token。
- NFR-004：权限、字段和证据异常应明确失败；不依赖模型自述宣告完成。

## 不变量

- INV-001：执行者和独立审查者身份必须不同。
- INV-002：collect 不自动 DONE、合并、重试或替代独立审查。
- INV-003：已知问题只有经过结构化独立处置及风险接受后，才可能以 PASS_WITH_NOTES 完成。
- INV-004：不能删除日志或尝试历史以重置预算。

测试文件是验证位置，不表示本次已重跑全部用例。检查范围见[验收](ACCEPTANCE.md)。
