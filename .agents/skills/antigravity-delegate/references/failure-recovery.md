# 故障恢复

日常 run 先读取 result_file、工作树和检查日志；其 CHECK_FAILED/BLOCKED 不进入下面的持久队列。
检查默认 argv，管道等语法需要 --shell-checks；超时后先核对实际进程，再决定重试或清理。
完整工作流中的 verify 失败不自动重新实现；基础设施重试和实现返工预算分别记录。
配置检查指出代理 sandbox_mode 等字段无效时，应核对父会话权限，而不是换一个字段值宣称只读保障。

## Windows 路径与只读前检

初始化和 prepare 前，对照 PowerShell Resolve-Path、Python os.getcwd()/Path.resolve()
与 git rev-parse --show-toplevel；非 ASCII 路径显示乱码时区分终端显示与真实路径错误。
若目录实际误解码，立即停止写入，不重复 init/create。junction 解析仍可能回到原路径；
必要时使用经核对提交的真正 ASCII 路径副本，记录原仓库、复制提交与唯一主控位置。
不要自动覆盖原仓库或把副本成果合回；误生成内容先核对来源，再按授权恢复。

## 超时不是额度诊断

模型列表/READY 仅是能力和短请求证据；账号/额度未知则报告 UNKNOWN。
先检查运行日志是否在认证、工具批准、命令锁、网络、测试或模型请求处停顿；
没有证据不要归因额度。记录 PID、开始时间、执行命令和工作区；超时后确认该任务
进程及其子进程均退出，再审查或重派。只处理确认属于本任务的进程，不按名称批量终止。
Windows npm EBUSY 先记录失败及锁定状态，优先新干净 Worktree，不能强删用户依赖目录。

## BLOCKED 的有界返工

新契约用 `max_implementation_reworks` 约束语义返工，用 `max_infra_retries` 约束同一实现
attempt 内的启动/认证/Provider 恢复。旧 `max_execution_attempts` 继续表示总实现次数。
权限、空输出和传输失败先分类并消耗 infra budget；只有生成候选后被独立审查退回才消耗
implementation rework。两类预算都不得无限增长。

预算耗尽是计划复核点，不自动等于需要再次请求用户授权。若用户已明确授权修通
同一范围的路由/功能，Sol 可记录新证据、缩小任务并修订自定尝试预算，重新绑定
当前授权与新契约哈希；须公开说明调整，保留历史且不扩大权限。用户明确规定的硬
上限、权限变化、范围扩大或合并仍须新授权。不要机械地为同一已授权修复反复设
max1、失败、询问，形成流程死循环；也不得用“跑通”为名无限复用相同长任务。

先落实新增尝试/修订的授权依据（有效既有授权或新授权），保留旧 Worktree、原始执行回执和完整日志。
当前 BLOCKED→READY 不自动归档、增加 attempt 或重置回执；只有 REVIEW→READY
具备该行为。Root 须先保存 history/attempt-N，更新 revision/attempt 和
`max_implementation_reworks`（旧契约才更新 `max_execution_attempts`）
并重置当前模板身份，再绑定新契约哈希审批；不得删除 run-* 来重置预算。
修复已有代码时从对应执行提交建立专用返工基线，而不是从缺少代码的主控 HEAD 开始。
仅在核对纯治理 Diff 后转入所需治理状态，不互相混合实现，也不自动合入 main。
提交干净契约后按控制器返回的新 Worktree 执行；再次耗尽预算即停止请求决策。

若终止的 agy 只留下精确的未跟踪候选且没有实现提交，禁止 Root 代为提交、stash/apply
或复制代码。Sol 可在新 revision 明确允许复用，任务必须设置
`isolation.reuse_terminal_worktree: true`，writable 必须是无 glob 的精确候选清单，然后运行：

    control.py prepare TASK-ID --approve --approval-file PATH --reuse-terminal-worktree --confirm-previous-process-exited

Root 必须先按 PID/进程树证据确认旧执行器已退出；确认 flag 会被写入新 run。
控制器只接受紧邻的 `LAUNCH_FAILED`/`NEEDS_ATTENTION` run、匹配的任务/run/contract 身份、
同一 Git common-dir 中已注册且位于 `.worktrees` 下的原 Worktree/分支、
`HEAD == previous base_commit`、零 tracked/staged 修改且全部未跟踪路径与 writable 清单
完全相等的情况，并在重命名前再次核验。旧 base 必须是当前治理基线的祖先。
它保留目录和文件，重命名为新 attempt 分支，写入新的 context/receipt，
并把原 base_commit 写入新 run。任一检查失败即停止；不得退化为新 Worktree 搬运候选。

若留下的是 tracked/staged partial，可在新契约设置 `isolation.reuse_tracked_worktree: true`
并使用 `--reuse-tracked-worktree --confirm-previous-process-exited`。该路径额外要求当前契约的
结构化 approval；approval 必须同时绑定旧 contract hash、候选 binary diff hash 和当前
contract hash。只接受同一受管 Worktree、HEAD 仍等于旧 base、无未跟踪文件、
无删除/重命名/冲突，且全部 tracked added/modified 路径属于无 glob 的精确 writable 清单。新 attempt 必须重新运行
所有受影响 probes、verify 和独立审查。Root 仍不得复制、stash/apply 或代提交半成品。

## 本地 agy

从首个具体故障恢复，避免循环尝试：

1. 参数无效或不支持：停止，重新探测，仅映射帮助中支持的参数。
2. Worktree 路径不符：读取 `git worktree list --porcelain` 或创建脚本返回的路径。
3. 权限或条款提示：保持交互；无头运行出现 `headless mode cannot prompt`、`auto-denied`
   或 `no output produced` 时，即使 exit 0 也按失败处理。已有任务级明确授权时用
   `--auto-approve --approve` 重派；没有授权则停止，不从帮助命令成功推断登录或同意。
4. 并发失败：最多重试一次，降为单并发，保留首次日志；再次失败即停止。
5. stdout 为空、截断或报告缺失：检查固定报告路径与会话登记，不能仅凭退出码判定成功；
   严格格式任务还要验证输出结构，前置过程文字属于格式失败。
6. 清理脏目录：没有明确 `-Force` 不移除；强制清理前检查 Diff。

每次重试使用新尝试编号并保留旧日志。不要为同一任务启动第二个控制器，
静默用普通 Codex 子任务替代 Antigravity，或绕过独立审查合并。

## 原生故障与重新分配

原生工具不可用时如实报告，不模拟派发或仅凭配置声称使用了某模型。
保留失败代理身份，检查状态、输出和部分修改；活动未知时禁止新增写入，
待工作完成或停止后再重新分配。

Root 可在记录原因、保留证据、按 revision/attempt 规则更新契约后选择可用后端。
使用隔离工作区并遵守新后端审批协议。不要为原生任务生成 agy 运行记录、
清空历史获取重试次数或让原生 worker 启动 agy。验收前重新验证变更后的快照。
