# 高级任务控制流程

普通有界机械修改先用[日常 run](quick-start.md)。本页适用于持久任务、审批、多轮返工和独立审查。
已有受控任务不能改走 run 绕过审批或尝试预算。参数见[命令参考](cli.md)。

## 1. 规划与自适应路由

Root 定义目标、范围、验收、风险、检查和真实角色，执行者实现，独立审查者核验同一快照。
在目标 Git 根目录 init 后创建草稿：

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py create TASK-001 --title "有界修改" --objective "可观察的结果" --risk low --mode delegated
```

补齐 queue/TASK-001 的七文件契约，检查 planning.work_type、judgment、context_continuity、
acceptance_determinism。默认只将低判断、可确定验收的机械工作交给 agy；语义、安全、架构、
高判断、强连续性或低验收确定性的工作默认 direct。风险和 authority 另决定是否需要审批。

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py validate TASK-001
python .agents/skills/antigravity-delegate/scripts/control.py route TASK-001
```

按 route 的 backend 决定 start 或 prepare，不只看原 execution.mode。
若 backend 变为 direct，先将 roles.executor 等身份规划改为实际执行者，并重新核对契约和审批。
直接后端不会降低任务显式要求的审批。高判断任务强制委派需结构化 routing_override 和独立契约审批。

checks 可分 adversarial_probes、fast_gate、final_gate；旧 checks.required 兼容为末尾必要检查。
创建草稿的验收与检查为空，需补齐后才能验证。命令按首次出现的字符串去重执行。

## 2. 提交执行基线

创建工作树前提交完整契约及预期修改，保持主控干净。isolation.base_branch 必须解析到包含
契约的当前 HEAD，可用 HEAD；不要沿用过期 main。执行工作树只持有已提交契约快照，
主控任务目录才拥有活动状态。一个工作树同时只允许一个写入者。

## 3A. direct

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py start TASK-001 --worktree
```

适用时加 --approval-file PATH。start 检查依赖、隔离和实际路由，可由 Root、人工或明确获准的
原生 worker 实现；不要求先发生 agy 故障。中高风险及契约要求隔离时不能省略工作树。
将真实证据交回 start 输出的主控回执路径，Root 检查后显式迁入 REVIEW：

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py transition TASK-001 REVIEW
```

direct 不运行 agy 的 launch、verify、collect。实际代理身份未知时写 UNKNOWN，不以模板名冒充。

## 3B. 本地 agy

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py probe
python .agents/skills/antigravity-delegate/scripts/control.py prepare TASK-001 --approve
python .agents/skills/antigravity-delegate/scripts/control.py launch TASK-001 --approve --interactive
python .agents/skills/antigravity-delegate/scripts/control.py verify TASK-001 --approve --approval-file .ai/runtime/verify-approval.yaml
python .agents/skills/antigravity-delegate/scripts/control.py collect TASK-001
```

prepare 的路由或风险要求审批时也需 --approval-file PATH。verify 始终要求 --approve 和绑定
当前契约的独立审批文件，因为它要执行确切的检查矩阵。两个 --approve 都不能替代审批 YAML。

agy 只实现、运行必要聚焦检查、提交实现并写 IMPLEMENTED 回执，然后退出。
verify 在工作树运行 adversarial → fast → final 检查，记录实际命令和工作区证据，
全部通过才转为 COMPLETE；失败后续阶段标 NOT_RUN，之后由 collect 核验并进入 REVIEW 或阻塞。
collect 不自动独立审查或 DONE。旧契约的兼容规则见[回执协议](receipt-protocol.md)。

检查默认 argv，shell:true 需在获批契约中明确声明。单命令默认 600 秒、总检查默认 1800 秒，
由共享进程模块执行及超时清理，并逐条复核分支、HEAD 和工作区。工作树不是操作系统沙箱。
终端授权问题使用真实交互模式处理，不静默启用 --auto-approve；--full-access 只是旧兼容名。

## 4. 独立审查与收尾

实现和验证退出后，再核验同一 HEAD、未提交 Diff、新增文件、命令与验收条件。
审查者只返回发现和建议，Root 写主控 QA/Review；后续修改须重新验证受影响证据。
有已知问题时须逐项处置和风险接受。DONE 的结构化门见[回执协议](receipt-protocol.md)。

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py transition TASK-001 DONE
```

DONE 不合并 Git。人工处理已审查快照的合并与工作树收尾。
PROJECT_STATE.yaml 仍为人工摘要，实时持久任务总览使用 status --json。

## 5. 返工与恢复

REVIEW → READY 归档旧证据并增加 task attempt。实现返工与基础设施重试使用独立预算；
旧 max_execution_attempts 继续按兼容逻辑工作，不能删除历史重置预算。
incremental 上下文优先提供上一轮 Review、失败和 Diff，避免重复灌入全部历史。

受控 partial 复用需精确清单、旧/新契约与 Diff 绑定审批，以及已退出进程的确认。
--reuse-terminal-worktree 与 --reuse-tracked-worktree 的条件不同，不能凭文件夹还在就直接重用。
详细结构与限制见[本地委派](delegation.md)、[任务协议](task-protocol.md)和[故障恢复](failure-recovery.md)。
收到“继续”先检查现有主控任务、回执、Git、运行记录和实际进程，不重复成功启动。
原生代理继承父会话权限，“不编辑”的角色指令不是独立只读系统权限；不能以配置 PASS 宣称运行保障。
