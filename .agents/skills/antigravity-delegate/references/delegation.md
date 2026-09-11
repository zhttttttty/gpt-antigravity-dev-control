# 本地委派操作

Codex 负责规划和 Review，Antigravity 负责实现，人类负责合并。整个控制流程由
Codex 在仓库内执行，不需要 Hermes、远程 Reviewer API 或后台调度器。

## 安装与探测

本地 agy 生命周期需要 Python 3.10+ 和 Git；运行 check-orchestration 或完整项目
测试集时使用 Python 3.11+。

    python -m pip install -r .agents/skills/antigravity-delegate/scripts/requirements-local.txt
    python .agents/skills/antigravity-delegate/scripts/control.py --help
    python .agents/skills/antigravity-delegate/scripts/control.py probe

Windows 上 agy 不在 PATH 时：

    python .agents/skills/antigravity-delegate/scripts/control.py probe --executable C:\path\to\agy.exe

探测会检查 `--version`、`--help`、`agent`、`agents` 和 `agent list`，并从帮助文本
动态解析实际参数与模式。不要假设固定版本，也不要把控制器的 `direct` 当成 agy
模式。真实登录、条款、隐私选项和文件夹信任需要在交互终端中完成。

Adapter 默认从隔离 Worktree 运行，非交互模式使用 `-p <prompt>`，不会将 stdout
当作 JSON；结构化结果必须写入回执文件。模型保持 agy 当前配置的默认值。
探测成功不能证明认证和工具权限。自定义版本参数可用 `launch --args-file local-argv.json`
传入 JSON 字符串数组，支持 `{worktree}`、`{context}`、`{receipt}` 占位符；
参数直接传给进程，不经过 Shell。Windows 批处理包装器会被拒绝，应使用原生可执行文件。

## 交互执行

    python .agents/skills/antigravity-delegate/scripts/control.py launch TASK-001 --approve --interactive --executable /path/to/agy

必须在真实终端中运行，不要重定向 stdin/stdout。启动后让 Executor 完成契约、测试
和 receipt，然后退出 agy，回到 Codex 执行 collect。

交互输出包含 TUI 和最终控制器 JSON，不是纯 JSON 流；终端画面不写入 launch.log，
agy.log 可能含路径、Prompt 或私有代码，应只保存在本地并在外发前脱敏。

## 全权限模式

可信的一次性 Worktree 可以显式使用：

    python .agents/skills/antigravity-delegate/scripts/control.py launch TASK-001 --approve --interactive --full-access

该选项只向 agy 传递 permission-bypass 参数，不授予管理员权限，也不会移除 Scope、
Receipt、Review 或人工合并门。永远不要静默启用。

## 多代理审阅协议脚本

需要多个边界清晰的审阅分片时，使用 Skill 自带的确定性脚本：

    powershell -File .agents/skills/antigravity-delegate/scripts/probe_agy.ps1 -Executable agy -OutputDir .ai/runtime/logs/probe
    powershell -File .agents/skills/antigravity-delegate/scripts/create_review_worktree.ps1 -Name review -OutputFile .ai/runtime/review-worktree.json
    powershell -File .agents/skills/antigravity-delegate/scripts/launch_agents.ps1 -ConfigPath .ai/runtime/agents.json -OutputDir .ai/runtime/review-run -MaxConcurrency 2
    powershell -File .agents/skills/antigravity-delegate/scripts/collect_reports.ps1 -OutputDir .ai/runtime/review-run
    powershell -File .agents/skills/antigravity-delegate/scripts/cleanup_worktree.ps1 -Path <JSON 中的 path>

默认并发两个代理，硬性最大值为四个。请求三个或四个时会先启动两个，首个任务成功后
才提升到目标并发。大型只读或多文档任务可以使用三到四个；写入任务默认仍限制为两个，
除非显式传入 `-AllowHighWriteConcurrency`。任务可以声明 `depends_on`、`max_retries` 和
`timeout_seconds`。依赖关系会按 DAG 校验；只读代理可以共享 Worktree，并发任务中只要
有一个具备写权限，该 Worktree 就会被独占。首次失败最多自动重试一次，并将本次运行
剩余阶段降为单并发。用户级启动锁会阻止两个调度器同时占用 agy。
`sessions.json`、分次报告、stderr 和执行日志固定保存在同一目录，最终生成
`summary.json` 和 `handoff.md`。覆盖统计以 `git ls-files` 加未忽略未跟踪文件为权威清单；
枚举文件不等于完成语义阅读。

这些锁和限制只覆盖 agy 启动器。Root 还需把原生 Codex 工作计入合计预算（默认
两个活跃单元），使用更高本地容量前先协调调整预算。见 [混合执行](HYBRID_ORCHESTRATION.md)。
单任务由 control.py prepare 创建隔离目录；上面的 review-worktree 脚本用于独立分片，
不要为同一任务重复准备第二个 Worktree。

## 单任务流程

先用 `control.py create` 或任务模板建立任务，补齐可写范围、真实验收条件和检查命令，
再提交契约。主控工作区必须干净，`isolation.base_branch` 必须解析为包含该契约的当前
HEAD；本地委派始终要求 Worktree 隔离。持久依赖必须已是 DONE 或 ARCHIVED。

    python .agents/skills/antigravity-delegate/scripts/control.py validate TASK-001
    python .agents/skills/antigravity-delegate/scripts/control.py route TASK-001
    python .agents/skills/antigravity-delegate/scripts/control.py prepare TASK-001 --approve
    python .agents/skills/antigravity-delegate/scripts/control.py launch TASK-001 --approve --interactive
    python .agents/skills/antigravity-delegate/scripts/control.py status TASK-001
    python .agents/skills/antigravity-delegate/scripts/control.py collect TASK-001

prepare 会创建隔离 Worktree、记录基础提交和契约摘要，并写入上下文包。collect 会
检查 Git 祖先关系、分支状态、变更范围、回执身份、检查命令和验收证据。

高风险或 authority 标志启用时，route 会升级为 approval_required。人类在被 Git 忽略的
`.ai/runtime/` 创建包含 `task_id`、`contract_sha256`、`result: APPROVED`、
`approved_by` 和 `evidence` 的审批 YAML，并通过 `prepare --approval-file PATH` 传入。
该记录绑定当前契约，不能证明身份，也不代表批准最终合并。

## 证据与审查

完整日志保存在 .ai/runtime/logs/TASK-ID/，默认先读取 compact JSON。缺失证据会阻塞；
collect 成功只会进入 REVIEW，不会独立生成 PASS，也不会自动合并。

上下文包是 task、brief、context 和 rollback 的 UTF-8 内容，硬上限 32KB；超限会拒绝，
不会静默截断。Executor 在 Worktree 的 `.ai/runtime/delegation/receipt.executor.yaml`
写回执，只提交实现文件。collect 检查增加、修改、删除和重命名前后的路径；控制文件
始终受保护。Worktree 隔离 Git 状态，不是操作系统安全沙箱。

精简 JSON 包含 SHA、文件数量和预览、范围结果、声明通过的命令/验收计数、耗时和
证据路径。它不编造测试总数、Token 或独立 PASS；必要时从执行日志核实真实结果。

Codex 应检查精确 Diff、Receipt、测试日志和验收条件，再写 receipt.qa.yaml 与
review.yaml。高风险任务还必须满足额外 Risk Gate 和人工审批。

## 故障恢复

无回执、权限阻塞或非零退出时：

    python .agents/skills/antigravity-delegate/scripts/control.py diagnose TASK-001

先检查运行记录、Worktree 和日志，再显式确认一次交互 recovery。禁止盲目重试或把
退出码 0 当作成功。REWORK 会保留之前尝试的证据。

- print 模式退出 0 但没有最终回执时标记 NEEDS_ATTENTION；`diagnose` 只扫描本次日志
  的有界尾部并输出脱敏分类。
- NEEDS_ATTENTION 或 LAUNCH_FAILED 经检查后，可明确确认一次
  `launch --approve --interactive --recover`。初次启动和一次恢复分别保留日志；再次失败停止。
- 缺失或脏回执可以在保留现场后修正再 collect；范围或证据失败会迁入 BLOCKED。
- REVIEW 到 READY 会归档旧回执并增加 attempt；准备失败也消耗预算，不能删历史重置。
- PREPARING/LAUNCHING 中断或锁残留时，先检查 run.json、进程、Worktree 和分支。
  控制器不保证跨多个文件的崩溃安全事务，也不自动清理或备份运行记录。

离线测试使用临时 Git 仓库和伪 agy，不消耗 Provider 额度，也不能证明真实编码质量、
无人值守可靠性或 Token 节省。真实效果按 [用量测量](../COST_METRICS.md)记录。
