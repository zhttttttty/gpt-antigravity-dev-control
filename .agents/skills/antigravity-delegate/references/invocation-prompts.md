# 调用提示词

本页给出 `Sol high + Luna high + Antigravity` 的可复制调用方式。通常只需在任务开头
显式写出 `$antigravity-delegate`；Codex 也可能根据任务描述自动选择本 Skill，但显式调用
更容易固定工作流和停止点。

## 推荐：一次调用完成完整流程

日常任务优先使用下面的短提示词：

```text
使用 $antigravity-delegate 按 Sol high + Luna high + Antigravity 默认流程完成：

【在这里写需求、目标仓库和验收条件】

先由 Luna 只读探索，Sol 制定任务契约和路由；需要编码时交给 Antigravity；
Antigravity 完全退出后由 Luna 独立审查，最后由 Sol 给出 PASS、REWORK 或 BLOCKED。
不要自动合并。
```

如果任务较复杂，使用完整版本：

```text
使用 $antigravity-delegate 完成以下任务：

目标仓库：【路径】
需求：【需求描述】
验收条件：【可执行测试、预期行为或交付物】
限制：【不能修改的文件、兼容性、时间或安全要求】

按默认流程执行：
1. Luna high 只读探索代码、定位影响范围、风险和可运行的验证命令。
2. Sol high 根据证据作出决策，创建有界任务契约，并选择 direct、delegated 或
   approval_required。
3. 若为 delegated，在独立 Worktree 中交给 Antigravity 实现；不得静默改用原生
   Luna worker。
4. Antigravity 完全退出后，Luna high 针对同一快照独立测试和审查。
5. Sol high 核对契约、差异和证据，最终给出 PASS、REWORK 或 BLOCKED。
6. 不要自动合并；报告任务 ID、实际路由、提交、测试结果和剩余风险。
```

一次调用的好处是 Task ID、基线、Worktree 和验收条件由同一个主控连续维护。除非需要
人工审批、跨会话协作或只想执行其中一个阶段，否则不必把三种角色拆成三次调用。

## 三种工作的单独调用方式

### 1. Sol：少量但高价值的决策

适合架构取舍、范围划分、风险分级、任务契约和最终验收。下面的提示词只做决策，不编码：

```text
使用 $antigravity-delegate，仅完成 Sol high 的决策与计划阶段。

任务：【任务描述】
目标仓库：【路径】

允许 Luna high 做有界只读探索并返回证据。随后由 Sol：
- 明确目标、非目标、文件边界、风险和验收条件；
- 选择 direct、delegated 或 approval_required，并说明理由；
- 若需要委派，生成可供 Antigravity 执行的任务契约和 TASK-ID；
- 输出验证命令、回滚思路和未决问题。

到 READY 停止。不要 prepare、launch、修改代码或自动合并。
```

如果已有探索证据，可以加一句：`不要重复探索，以我提供的证据为输入。`

### 2. Luna：大量读代码、找证据和审查

适合边界不清、需要定位实现、确认测试入口或独立审查的任务。探索提示词：

```text
使用 $antigravity-delegate，仅执行 Luna high 的只读探索阶段。

问题：【需要查清的问题】
目标仓库：【路径】

查找相关文件、调用链、现有测试、潜在回归和可运行的验证命令；所有结论附文件路径、
行号或命令证据。区分已确认事实、条件成立的判断和假设。不要修改文件，不要启动
Antigravity，不要代替 Sol 作最终路由或验收决定。输出给 Sol 的精简证据包后停止。
```

Antigravity 实现完成后的审查提示词：

```text
使用 $antigravity-delegate，对 TASK-ID【任务 ID】执行 Luna high 独立审查。

只审查任务记录的精确 Worktree、base 和 head。核对任务契约、实际 diff、P0/P1 风险、
测试结果和覆盖情况；必要时运行只读或测试命令，但不要修改实现。输出带路径和行号的
发现，并建议 PASS、REWORK 或 BLOCKED。最终决定仍交给 Sol。
```

### 3. Antigravity：消耗自身模型额度执行编码

适合已有明确契约的多文件修改、测试补充和可验证重构：

```text
使用 $antigravity-delegate，执行已经 READY 的 TASK-ID【任务 ID】。

先验证任务契约和 agy 能力，再按 prepare -> launch -> collect 流程让 Antigravity 在
指定独立 Worktree 中实现。严格遵守文件范围、验收条件和禁止事项；保存提交、测试、
日志和回执证据。不得静默切换到原生 Luna worker，也不要自动合并。

收集完成后停在 REVIEW，等待 Luna 独立审查和 Sol 最终验收。
```

分阶段调用时，每次都要复用同一个 `TASK-ID`，并以任务记录中的精确 base、head 和
Worktree 为准；不要只凭聊天摘要猜测当前快照。

## 按任务类型选择提示词

| 情况 | 推荐路由 | 调用方式 |
| --- | --- | --- |
| 修改 1 个文件、低风险、预计 10 分钟以内 | `direct` | 使用短提示词并补充“若探测确认仍是小改，由 Sol 直接完成” |
| 修改多个文件、有明确测试 | `delegated` | 使用“一次调用完整流程”或已有契约的 Antigravity 执行提示词 |
| 边界不明确 | 先探索 | 先用 Luna 只读探索提示词，再让 Sol 决定路由 |
| 架构、安全、迁移、部署 | `approval_required` | 使用高风险模板，在启动执行前等待人工批准 |
| Antigravity 已完成 | Luna reviewer | 使用 Luna 独立审查提示词，随后交给 Sol 最终验收 |
| P0/P1 或重要生产改动 | Sol `max` 验收 | 在 Codex 中为最终验收任务选择 Sol Max，再使用最终验收模板 |

小型直接修改模板：

```text
使用 $antigravity-delegate 处理这个小型低风险任务：【任务描述】。
先快速确认范围；如果确实只涉及 1 个文件且预计 10 分钟以内，路由为 direct，由 Sol
直接修改并验证。如果实际范围扩大，停止直接执行并重新选择 delegated 或
approval_required。不要为了形式启动 Antigravity。
```

高风险审批模板：

```text
使用 $antigravity-delegate 规划此高风险任务：【任务描述】。
路由为 approval_required。先由 Luna high 只读调查，Sol 输出影响范围、风险、回滚计划、
任务契约和拟执行命令；在启动 Antigravity 或产生受控变更前停止并等待我的明确批准。
批准后执行仍须经过 Luna 独立审查和 Sol 最终验收，不要自动合并。
```

最终验收模板：

```text
使用 $antigravity-delegate，由 Sol 对 TASK-ID【任务 ID】做最终验收。
读取 Luna reviewer 的发现、任务契约、精确 diff、测试和回执证据；逐项判断验收条件，
输出 PASS、REWORK 或 BLOCKED 及理由。P0/P1 或重要生产改动使用 Sol Max。
不要修改代码，也不要自动合并。
```

提示词中的“使用 Sol Max”不能保证在当前任务中自动切换模型或推理强度。重要生产验收
应在 Codex 模型选择器中明确选择 Sol 与 `max`，或者新建一个使用该设置的验收任务。

## 停止点和人工责任

| 阶段 | 正常停止点 | 交付内容 |
| --- | --- | --- |
| Sol 规划 | `READY` | TASK-ID、路由、范围、验收条件和风险 |
| Antigravity 执行 | `REVIEW` | 提交、diff、测试、日志和回执 |
| Luna 审查 + Sol 验收 | `PASS` / `REWORK` / `BLOCKED` | 独立发现和最终结论 |
| 合并 | 人工操作 | 本 Skill 不自动合并 |

## 常见问题

- 找不到 Skill：确认目标仓库包含 `.agents/skills/antigravity-delegate/SKILL.md`，在
  Codex 中检查 `/skills`；刚安装或修改后必要时重启 Codex。
- Antigravity 不可用：停止并报告探测结果。只有 Root 明确记录原因并批准后，才能改用
  原生 Luna worker，不能静默降级。
- 交互式启动需要终端或审批：按当前环境完成所需交互；不要用提示词绕过权限控制。
- 只想调用某一阶段：明确写“仅执行……阶段”和停止点，并提供已有 TASK-ID；否则默认
  采用完整闭环。
