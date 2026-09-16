# 优先读取精简回执

执行者在上下文或启动提示词指定的绝对路径写核心协议回执，只提交实现，不修改任务状态。
主控拥有状态迁移权限，执行分支上的任务副本为历史契约，不是第二个活动队列。

本地 agy 的 `collect` 核验身份、版本和声明的必要证据，校验工作区 base/head/branch/path
并核验 Git 实际观测，拒绝格式错误的回执与证据（如非规范的 SUCCESS/COMPLETED 状态、
PASSED 结论、id/status 混用等）。计数对象是必要命令，不能编造单项测试总数。
验收仍是执行者声明，不生成独立 PASS；证据完整时迁入 REVIEW，检查失败时迁入 BLOCKED。
只有与 task.checks.optional 精确匹配且 reason 非空的结构化 NOT_RUN 可选检查项允许保留未验证；
必要检查缺失或未通过依然判定为 BLOCKED。
已报告的已知问题以原始文本和非 PASS 标记（如 REPORTED）进入 REVIEW，不直接阻断进入审查。

原生 Codex 填写相同执行回执并记录实际身份。Root 显式核验范围、版本、命令和验收，
不运行 agy collect。模型或运行信息不可得时写 UNKNOWN；补充身份、模型、状态与 Diff
证据可存入报告并从现有 notes/evidence 字段引用，不新增回执格式。

两条路径均交接精确工作区、base/head、变更与新增文件、未提交 Diff。
tester 和 reviewer 检查该快照，而非默认工作区。只读审查者返回发现，
Root 如实写入 QA/Review；后续实现或测试变化须更新受影响证据。

先读摘要、选定 Diff、相关测试和证据，独立核验关键声明，再写
`review.yaml` 和 `receipt.qa.yaml`，按审查结论迁移。
存在已知问题时，DONE 要求一对一独立 QA 处置（known_issues_review）、核验证据（evidence_checked）、
风险责任人批准接受残余风险（risk_owner_approval 与 ACCEPTED_RESIDUAL 处置）、
QA/Review 一致的 PASS_WITH_NOTES 结论，以及既有的高风险人工合并审批门。
合并与发布保持显式，不能用旧分支任务副本覆盖主控状态；按要求手工协调
`PROJECT_STATE.yaml`。

REWORK 从 REVIEW 执行 `control.py transition TASK-ID READY`，
自动归档回执并增加 attempt。BLOCKED 按恢复流程处理。
新 Worktree 准备前提交主控文件；失败准备也消耗本地预算。达到上限交由 Codex/人类
调整计划，不删除历史重置预算。收集不自动合并、重试、重跑测试或调用远程 API。
