# 优先读取精简回执

Print 模式优先有界同步命令。实际返回 TaskId 时使用 manage_task status；返回
CommandId 时使用 command_status；不得用定时器、schedule 或被动叙述替代轮询。
Windows 搜索使用工作树 cwd 下的相对路径。能力门控的 stream-json 保留原始事件，
记录 tool_info.output（兼容 result）、句柄与完成状态；缺失时间戳写 UNKNOWN，
不推断未返回的 exit code，也不把 CLI exit0 当验收 PASS。

控制器自修复例外不是通用 .agents 写权限：仅限脚本列出的批准任务版本及精确路径，
要求真实 Git top-level、与执行源码相同的 canonical common-dir、可信 commit anchor
祖先关系和匹配契约的前置审批，显式 protected 永远优先。复制到其他安装目录后，
跨仓库自修复会 fail closed；该用途应运行已审查控制器仓库中的入口。

## 派发时固定格式与版本

向执行者提供实际 receipt.executor.yaml 模板、绝对回执路径、task_id、revision、
attempt 和 run.json 中的 workspace/branch/base_commit。head_commit 在提交后读取。
不得用当前主控 HEAD 猜 base；主控状态提交可能晚于 Worktree 的创建。

完成状态使用 `COMPLETE`，不是 SUCCESS/COMPLETED。命令使用 `command`、
`exit_code`、`result: PASS`，不是 status/PASSED；验收使用 `acceptance_id`、
`result: PASS` 和非空 evidence，不是 id/status。填写真实失败和未运行结果。
Root 在 collect 前比较回执 workspace 与 Git/run.json，不能让覆盖字段掩盖错 base。
格式错误由执行者在获批返工中修正；Root 不代填执行者成功回执。

optional NOT_RUN 和已声明残余风险不等于必需检查失败，也不等于已经接受。
保留精确命令、原因和风险原文，独立 QA 核对，Sol 决定风险 disposition。
已知问题保留原文及 REPORTED 标记进入 REVIEW，不自动接受风险。只有与 optional
精确匹配且 reason 非空的结构化 NOT_RUN 可保留；必要检查失败仍阻断收集。
DONE 要求 known_issues_review 一对一原文映射、evidence_checked，以及接受残余风险
时结构化 risk_owner_approval（approved_by、result: APPROVED、evidence）。不接受别名
或纯字符串批准；QA/Review 须一致 PASS_WITH_NOTES，既有人工合并门保持有效。

执行者在上下文或启动提示词指定的绝对路径写核心协议回执，只提交实现，不修改任务状态。
新流程由执行者填写身份、验收、偏差和问题并设置 `IMPLEMENTED`；控制器
`verify --approve --approval-file PATH`
执行 task.yaml 中的精确命令，填充 commands、workspace、changed_files、scope_check，并将
状态改为 COMPLETE 或 FAILED。控制器不得替执行者编造验收声明，也不得把 FAILED
执行结果升级为 COMPLETE。仅含旧 `checks.required`、不含 staged gate 的兼容契约可直接
collect 旧执行者写出的完整 COMPLETE 回执；新 staged-contract 必须经过 VERIFIED。
主控拥有状态迁移权限，执行分支上的任务副本为历史契约，不是第二个活动队列。

本地 agy 的 `collect` 核验身份、版本和声明的必要证据，观测 Git 变更与保护范围，
保留完整回执和 Diff，输出精简 JSON。计数对象是必要命令，不能编造单项测试总数。
验收仍是执行者声明，不生成独立 PASS；有效证据迁入 REVIEW，检查或范围失败可能迁入 BLOCKED。
格式、工作区身份等前置错误可能直接报错并保留当前状态，需同时核对命令输出与实际任务目录。

原生 Codex 填写相同执行回执并记录实际身份。Root 显式核验范围、版本、命令和验收，
不运行 agy collect。模型或运行信息不可得时写 UNKNOWN；补充身份、模型、状态与 Diff
证据可存入报告并从现有 notes/evidence 字段引用，不新增回执格式。

两条路径均交接精确工作区、base/head、变更与新增文件、未提交 Diff。
tester 和 reviewer 检查该快照，而非默认工作区。只读审查者返回发现，
Root 如实写入 QA/Review；后续实现或测试变化须更新受影响证据。

先读摘要、选定 Diff、相关测试和证据，独立核验关键声明，再写
`review.yaml` 和 `receipt.qa.yaml`，按审查结论迁移。
合并与发布保持显式，不能用旧分支任务副本覆盖主控状态；按要求手工协调
`PROJECT_STATE.yaml`。

REWORK 从 REVIEW 执行 `control.py transition TASK-ID READY`，
自动归档回执并增加 attempt。BLOCKED 按恢复流程处理。
新 Worktree 准备前提交主控文件；失败准备也消耗本地预算。达到上限交由 Codex/人类
调整计划，不删除历史重置预算。收集不自动合并、重试、重跑测试或调用远程 API。
