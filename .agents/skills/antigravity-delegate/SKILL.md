---
name: antigravity-delegate
description: "将 Codex 的有界修改交给本地 agy：日常一条 run 命令返回实际改动与检查；复杂或高风险任务使用完整任务协议。"
---

# Codex 调用 Antigravity

本 Skill 自带控制器、Adapter、模板和文档。主控负责需求、范围和最终验收；
agy 实现有界修改。已有用户授权按当前会话适用，小改可由主控直接完成。

## 日常入口

适合范围清楚、低判断且可确定验收的机械修改，不需要额外创建 Codex 中转子代理。
在已安装 Skill 的目标 Git 项目根目录运行：

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py run "清楚描述需要的修改" --allow "src/**" --allow "tests/**" --check "python -m unittest discover -s tests -v"
```

run 无需 init、模型配置或七文件契约，要求干净且已有提交的源仓库。
它自动创建 codex/agy-* 分支和工作树，保存简短执行器报告、日志、实际 Diff 和调用者检查结果。
未提交和被忽略文件不复制；不要为了运行而擅自丢弃或提交用户已有修改。
用 --dry-run 预览；指定 Windows 原生 agy 可执行文件时用 --executable。
需要真实终端处理确认时显式使用 --interactive，不静默绕过权限。

收到 READY_FOR_REVIEW 后读取 result_file、Diff、全部未跟踪文件和检查日志，核对实际结果。
控制台列表最多 20 项，完整清单保存在 result_file；tracked.diff 不包含新增未跟踪文件。
检查未提供时为 NOT_RUN，非零退出、无效报告、范围违规或失败检查不能当成完成。
不要自动合并、重试、删除现场，或将执行器的 COMPLETE 当作独立验收。
详见[日常指南](references/quick-start.md)与[命令参考](references/cli.md)。

## 什么时候升级为完整协议

架构、认证、安全、迁移、部署、破坏性或需要持久审批/多轮返工的任务，先建立完整任务契约。
使用 init/create/validate/route，再选择 direct 的 start 或本地委派 prepare/launch/collect。
高级 route 同时返回 mode 和 backend。高判断、语义、安全、架构、强连续性或验收不确定的工作默认 direct；
Root 选择 direct 后可明确派发有界 worker，不必先等待 agy 故障。
agy 只写 IMPLEMENTED，退出后运行 verify 的获批检查矩阵，再 collect；不能把实现声明当成验证完成。
高风险审批、独立 QA、回执和 DONE 门见[统一控制流程](references/workflow.md)。
不要将已有受控任务改走 run 来绕过其审批或清空尝试历史。
原生代理与 agy 的总容量、模型偏好和文件所有权见[编排规则](references/orchestration.md)。
只有存在独立工作且实际获准时才派发原生代理，不为转发 agy 增加一层模型代理。
只有需要多个独立审阅分片时才使用[多代理脚本](references/coordination-protocol.md)。

## 权限与配置

工作树隔离 Git 状态，不是操作系统沙箱。Scope 是事后检查，不能阻止拥有系统权限的进程越界。
原生 Codex 子代理继承父会话权限；“不修改实现”是角色指令，不代表独立只读系统权限。
代理文件内的 sandbox_mode、approval_policy、model_provider、mcp_servers 不覆盖父会话设置。

高级流程可选安装默认角色与项目配置：

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py init --install-codex-profile
python .agents/skills/antigravity-delegate/scripts/control.py check-orchestration
```

安装前预检冲突，默认保留不同内容；只有审查差异并获准替换后才加 --overwrite-codex-profile。
配置检查只证明离线一致性，不能证明实际模型、权限或登录可用。不要虚构执行身份或用量。
恢复既有任务先核对主控任务目录、Git、运行记录和实际进程，见[故障恢复](references/failure-recovery.md)。
