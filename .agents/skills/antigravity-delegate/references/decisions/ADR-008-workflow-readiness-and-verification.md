# ADR-008：日常自检、运行查询与验证快照绑定

状态：3.6.0-local 已实现，2026-11-01 提交前补记。本文记录现有实现，不追溯声称实现前已存在本决策文件。

## 决策

日常统一使用 doctor → run → runs。doctor 以标准库启动，只读检查依赖、Git、源状态及 agy 帮助，
不创建 `.ai` 或模型会话；缺 PyYAML 时仍能提供安装指引。统一入口禁止生成宿主项目字节码缓存。
runs 从 Git 公共元数据目录读取既有运行，提供列表、ID 和最近更新记录查询，不隐式重试、接受或清理。

agy 和检查共用有界进程执行；POSIX 交互子进程保留控制终端并获得前台进程组。
超时尝试清理本任务的进程树，工作树及日志继续保留，不将该机制称为系统沙箱。

高级 verify 执行前预检完整检查矩阵，持久化 VERIFYING 状态、检查进度及独立回执副本。
完成后记录当时 HEAD 与回执 SHA-256，collect 对 VERIFIED 和 VERIFICATION_FAILED 都检查该绑定。
验证后替换代码或回执不得继承旧检查结果。

## 兼容与恢复

- schema v2 和原有任务目录不迁移；新增公共命令不改变 status 的持久任务查询语义。
- 旧版已验证但缺少绑定的记录不能直接收集为新版本的已验证结果；保留现场，经主控审查建立新尝试和验证证据。
- 仅含 checks.required、无 staged gate 的直接收集兼容路径继续允许执行者完整回执，但必须明确是执行者声明。
- 意外退出停在 VERIFYING 时检查进度、日志与实际进程，不自动删锁或重跑不完整验证。
- READY_FOR_REVIEW 与 REVIEW 都不代表独立验收或合并。真实 Provider 质量、模型可用性和成本仍需另行测量。

## 验证

tests/test_daily_workflow.py、tests/test_adapter_readiness.py、tests/test_process_utils.py、
tests/test_local_delegation.py 及 tests/test_init_project.py 覆盖上述行为；PowerShell 保留独立协议测试。
最终 Python 套件为 159 项，Linux、Windows CI 均通过；Windows 跳过 POSIX 专属回归。
