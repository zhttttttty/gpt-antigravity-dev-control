# 日常一次委派

本路径用于普通有界修改；架构、安全、迁移、部署和已有受控任务使用[完整协议](workflow.md)。

## 一个命令

在安装了 Skill 的 Git 项目根目录执行：

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py run "补充 README 安装说明" --allow README.md --check "git diff --check"
```

需要已有 HEAD、干净源仓库、Python/PyYAML 与可用 agy，不需要 init 或模型配置。
只有已提交文件进入执行工作树；未提交内容和被忽略的 .env、依赖目录等不复制。
当前有未提交工作时先自行保存或提交，控制器不会擅自 stash、提交或丢弃。

只看计划，不调用 agy、不创建任何运行目录或工作树：

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py run "补充 README 安装说明" --allow README.md --dry-run
```

预览中的 source_clean=false 表示真实执行会被拒绝。
外部调用可用绝对脚本路径和 --repo，但目标必须是实际 Git 根目录。

## 执行与证据

1. 检查源仓库和 agy 参数能力，以 HEAD 创建 codex/agy-* 分支和新工作树。
2. 向 agy 提供一份上下文，仅要求简短 JSON 结果；不创建 task.yaml、QA 或 Review。
3. agy 退出后，控制器核对实际 HEAD、分支、改动与保护路径，再执行调用者提供的检查。
4. 检查结束后再次观察实际变更，将最终结果交给 Codex/用户审查。

--allow 可重复，未指定时允许普通路径，但 .git、.ai、.agents、.codex、.github、AGENTS.md、GEMINI.md 始终保护。
模式采用现有 fnmatch 规则；例如 src/** 与 tests/**。保护与范围检查都是事后核验，不是系统权限约束。

--check 可以重复，默认拆成原生 argv 在工作树执行，并记录真实退出码，不解释 shell 语法。
确需 &&、管道或重定向时显式增加 --shell-checks；此时 Windows 使用 cmd.exe，Unix 使用 /bin/sh。
PowerShell 专用语法需显式调用 powershell。命令默认使用本机参数引用规则，Windows 路径含空格时使用双引号。
不会执行模型报告中的命令。未提供检查时 checks_status=NOT_RUN，不伪装成测试通过。
--timeout 默认 1260 秒，--check-timeout 默认每条检查 300 秒，--total-check-timeout 默认合计 900 秒。
检查共用高级 verify 的进程执行模块；超时尝试清理进程树，每条检查后重新核验范围和 Git 历史。
总预算耗尽后余项标 NOT_RUN。超时或中断后仍保留现场，核对实际进程再重试或清理；清理不是系统沙箱。
Windows 指定原生 agy.exe 可用 --executable；需要真实终端时使用 --interactive。
不提供自动权限绕过或自动恢复。

## 结果与保留文件

运行目录位于 `git rev-parse --path-format=absolute --git-common-dir` 输出目录的 agy-runs/<id>/：

```text
<git-common-dir>/agy-runs/<id>/
├── workspace/       执行工作树，业务修改保留在这里
├── context.md       本次请求与范围
├── executor.json    执行器声明，尚非验收
├── launch/          agy 日志与可用的事件记录
├── check-N.log      调用者指定检查的实际输出
├── tracked.diff     已跟踪文件的 Diff
└── result.json      完整结果、所有变更与未跟踪文件清单
```

控制台只预览最多 20 个路径和 2,000 字符的执行器摘要。Codex 应读取 result_file，再查看
完整 Diff、所有 untracked_files 对应内容及检查日志；新增文件内容不在 tracked.diff 中。

| 状态 | 含义 |
|---|---|
| DRY_RUN | 只预览参数和源状态，未调用 Provider |
| READY_FOR_REVIEW | 执行报告与已配置检查符合交接条件，独立验收仍为 PENDING |
| CHECK_FAILED | 一条或多条调用者检查失败或超时，保留实际输出 |
| BLOCKED | 准备/启动失败、权限问题、缺报告、格式错误、范围违规或 Git 历史变化 |

READY_FOR_REVIEW 和 DRY_RUN 返回 0，其余返回 2；0 不是 DONE 或合并证明。
轻量运行不进入持久任务队列，因此 status --json 只列高级协议任务，不列这些运行目录。
默认保留所有运行工作树，读取 result.json 中的确切路径和分支后再决定合并或移除。
处理好业务修改后按 Git 自身的 worktree 管理流程清理，不要直接递归删除 Git 元数据目录。

## 真实效果验证

先选一个实际小任务，对比直接用 Codex 和本入口的完成时间、返工、人工介入及可归因用量。
记录 result.json 的 elapsed_seconds 和检查结果，但另计 Codex 审查与人工时间。
usage=UNKNOWN 表示没有 Provider 用量数据；日志大小不是 Token，离线假执行器不是生产任务结果。
独立安装的 Skill 可阅读[成本测量指南](cost-metrics.md)；本项目实测记录仍见根目录 COST_METRICS.md。
