# 命令参考

统一入口为 Skill 内的 `scripts/control.py`。以下命令在已安装 Skill 的目标 Git 项目根目录执行。
`ai.py`、`delegate.py` 是兼容入口，新文档只使用 `control.py`。

## 目标仓库与帮助

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py --repo D:\Projects\my-app status
python .agents/skills/antigravity-delegate/scripts/control.py --help
python .agents/skills/antigravity-delegate/scripts/control.py launch --help
```

`--repo` 接受目标路径；外部调用时脚本路径应为实际安装位置的绝对路径。
显式 `--repo` 对任务命令必须指向实际 Git 根目录，指向普通子目录会报错，不会静默操作外层任务。
不指定 --repo 时，任务命令仍从当前目录查找所属 Git 根。init 也要求实际 Git 根目录。
check-orchestration 按指定目录读取配置，允许检查无独立 Git 的样例夹具。
缺少或重复的 --repo、空路径和不存在的目标会返回明确错误，退出码为 2。

顶层帮助列出状态输出与配置检查；子命令 --help 列出各自参数。

## 日常一次委派（无需 init）

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py run "补充 README 安装说明" --allow README.md --check "git diff --check"
```

| run 参数 | 默认或含义 |
|---|---|
| `"需求"` | 一个非空请求，含辅助说明的上下文总包上限 32,000 UTF-8 字节 |
| `--allow PATTERN` | 可重复，相对路径模式；默认普通路径均可，控制文件始终保护 |
| `--check COMMAND` | 可重复，默认原生 argv；只执行调用者提供的命令 |
| `--shell-checks` | 显式允许调用者检查使用系统 shell 语法 |
| `--executable PATH` | 默认 agy，Windows 使用原生可执行文件 |
| `--interactive` | 需要真实终端时显式启用，不绕过权限确认 |
| `--timeout SECONDS` | agy 进程默认 1260 秒 |
| `--check-timeout SECONDS` | 每个调用者检查默认 300 秒 |
| `--total-check-timeout SECONDS` | 检查总预算默认 900 秒，耗尽后余项 NOT_RUN |
| `--dry-run` | 不调用 agy、不创建运行目录；source_clean=false 提示真实执行会拒绝 |

真实执行要求源仓库有提交且干净，创建独立 codex/agy-* 分支，数据保存在 Git 公共元数据目录 agy-runs 下。
JSON 返回完整结果文件、Diff、日志和最多 20 项路径预览。READY_FOR_REVIEW 不等于验收通过；
无检查时为 NOT_RUN。run 不创建持久任务、QA 或 Review，详见[日常指南](quick-start.md)。

## 初始化与任务

| 命令 | 参数 | 行为 |
|---|---|---|
| `init` | 可选 `--install-codex-profile`、`--overwrite-codex-profile` | 创建缺失模板、状态目录和忽略项；要求实际 Git 根目录 |
| `create TASK-ID` | 必需 `--title`、`--objective`；可选 `--risk low/medium/high`、`--mode direct/delegated/approval_required` | 创建 READY 草稿，不覆盖同名任务；默认 low/direct |
| `validate TASK-ID` | 无 | 检查契约、目录状态及必要产物；不执行测试 |
| `route TASK-ID` | 无 | 输出 mode、实际 backend、风险/判断依据和契约哈希 |
| `status` | 无任务 ID；可选 `--json` | 按目录列出实时任务状态；JSON 包含六类任务、计数、in_progress_tasks 和 unfinished_tasks |
| `status TASK-ID` | 无 | 输出任务详情和存在的本地运行记录；不会启动执行器 |
| `transition TASK-ID STATE` | 六种状态之一 | 检查允许边，移动主控任务目录；DONE 额外验证证据 |

普通 `init` 保留已有模板和状态文件，但会补充忽略规则与 `.gitkeep`。
`--install-codex-profile` 同时安装 `.codex/` 和 `.ai/config.yaml`，已有相同内容不重写。
安装前统一检查冲突；不同内容默认报错，不产生部分 profile 安装。
审查差异后可增加 `--overwrite-codex-profile`，仅覆盖分发 profile 对应文件；不覆盖已有项目说明或任务模板。
配置安装拒绝链接目标及文件/目录冲突。若项目已有自定义任务角色，仍需核对其与配置的一致性。
`status --json` 校验任务 ID、目录状态和重复目录，只读任务文件，不同步 PROJECT_STATE 摘要。

## direct 执行与工作树

| 命令 | 参数 | 行为 |
|---|---|---|
| `start TASK-ID` | `--worktree`、`--approval-file PATH` 可选 | READY → IN_PROGRESS，按实际 direct backend 检查依赖、隔离及审批 |
| `worktree-create TASK-ID` | 无 | 按契约基线创建 `.worktrees/TASK-ID`；不单独推进状态 |
| `worktree-remove TASK-ID` | `--force` 可选 | 移除上述 direct 工作树；强制前先检查未提交修改 |

`start --worktree` 和 `worktree-create` 要求主控干净，配置的基线等于当前 HEAD，且新任务分支尚不存在。
`worktree-remove` 不按委派的 `TASK-ID-N` 命名查找工作树，委派收尾需先核实实际 Git 登记。

## 本地委派

| 命令 | 参数 | 行为 |
|---|---|---|
| `probe` | `--executable PATH`，默认 `agy` | 探测版本和参数能力，写本地日志；不证明认证成功 |
| `prepare TASK-ID` | 必需 `--approve`；适用时 `--approval-file PATH` | READY 下创建 `.worktrees/TASK-ID-N`、上下文和运行记录，成功后进入 IN_PROGRESS |
| `launch TASK-ID` | 必需 `--approve`；其余见下表 | 启动已准备的执行器，不单独声明完成 |
| `verify TASK-ID` | 必需 `--approve --approval-file PATH`；可选 `--timeout` 默认 600、`--total-timeout` 默认 1800 秒 | 执行获批分阶段检查，填充真实证据，IMPLEMENTED → COMPLETE/FAILED |
| `collect TASK-ID` | 无 | 核验回执及 Git 证据，成功进入 REVIEW；失败依具体分支报错或进入 BLOCKED |
| `diagnose TASK-ID` | 无 | 读取最近运行，输出有界日志诊断及下一步建议 |

| launch 参数 | 默认或约束 |
|---|---|
| `--executable PATH` | `agy`；Windows 使用原生可执行文件，拒绝批处理包装器 |
| `--interactive` | 继承真实终端；不能以重定向 stdin/stdout 代替终端 |
| `--timeout SECONDS` | 1260 秒，必须大于 0 |
| `--mode accept-edits/plan` | 默认 accept-edits；需探测到实际支持，不是 execution.mode |
| `--args-file PATH` | JSON 字符串数组；支持 `{worktree}`、`{context}`、`{receipt}` 占位符 |
| `--recover` | 仅允许显式确认的一次交互恢复；需处于 NEEDS_ATTENTION 或 LAUNCH_FAILED |
| `--auto-approve` | 额外传递跳过工具确认参数；要求 `--approve`，不授予管理员或沙箱能力 |
| `--full-access` | --auto-approve 的旧兼容别名，不建议新调用使用 |

新契约分开设置 max_implementation_reworks（默认 1）与 max_infra_retries（默认 1）。
旧 max_execution_attempts 仍兼容；不得删除 run-N 重置预算。
prepare 可显式使用 --reuse-terminal-worktree 或 --reuse-tracked-worktree，需 --approval-file 和
--confirm-previous-process-exited；具体清单与契约绑定规则见本地委派指南。
上下文总包上限为 **32,000 UTF-8 字节**，单个输入文件也检查相同上限。
默认模型为 `configured_default`；单任务委派不接受以 execution.model 切换其他模型。

## 配置检查、输出与退出码

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py check-orchestration
```

此命令要求目标目录有 `.ai/config.yaml`、`.codex/config.toml`、五个角色文件，
并检查项目或随 Skill 分发的任务模板。只验证离线一致性，不连接模型服务。
代理文件内的 sandbox_mode、approval_policy、model_provider 和 mcp_servers 会被报告为无效覆盖，
它们继承父会话设置；角色指令中的“不编辑”不能替代系统只读权限。

核心协议命令主要输出文本；委派命令通常输出 JSON，交互 launch 的终端内容可能混有 TUI。
不要把所有命令 stdout 都当成单个 JSON 文档。
常见退出码为 0（该命令完成）、2（参数、协议或执行错误），配置检查失败为 1。
进程异常也可能返回其他非零值。退出码 0 不代表 QA PASS、DONE 或已合并。

完整执行顺序见[统一控制流程](workflow.md)，异常恢复见[故障恢复](failure-recovery.md)。
