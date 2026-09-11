# ADR-001：在统一控制平面中使用本地委派

状态：已接受，并与统一任务协议合并。

保留任务契约、状态机、Receipt 和合并门；通过可替换 Executor Adapter 使用本地 Git
Worktree 委派。control.py 是统一入口，旧 Python 文件仅作为兼容模块。

规划者选择 direct、delegated 或 approval_required。每次本地启动都需要确认。CLI 探测
不等于登录成功或无头执行成功；启动成功也不等于实现完成。collect 只生成用于独立
Review 的精简证据，不自动合并，也不调用 Reviewer API。

第一阶段不实现无人值守循环、自动重试、依赖调度、控制器自动重跑测试和 Token 节省保证。

历史范围说明：后续可选 agy 启动器增加了依赖 DAG 和最多一次重试，单任务生命周期
仍保持显式。原生/本地协调和模型默认值由 [ADR-002](ADR-002-hybrid-orchestration.md) 扩展。
