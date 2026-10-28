# Codex → Antigravity 日常委派工具

[English](README.md)

让 Codex 用一次调用把边界明确的修改交给 agy：自动隔离工作树、保存日志、执行指定检查，
再把实际改动交回 Codex 验收。复杂或高风险任务使用风险自适应的完整任务协议。
本版整合 GitHub main `db1426b`，保留本地轻量入口、安全安装、状态 JSON 和权限修正。

当前版本：**3.5.0-local**。主要交付物为 `.agents/skills/antigravity-delegate/`。

## 最短使用路径

需要 Git、Python 3.11+、可用的 agy 安装；复制整个 Skill 到项目后安装 Python 依赖。
源项目必须已有提交且工作区干净，未提交文件和被忽略文件不会复制到执行工作树。

```powershell
python -m pip install -r .agents/skills/antigravity-delegate/scripts/requirements-local.txt
python .agents/skills/antigravity-delegate/scripts/control.py run "补充 README 的安装说明" --allow README.md --check "git diff --check"
```

不需要先 init、配置模型、创建 task.yaml 或填写回执。先预览且不调用 agy：

```powershell
python .agents/skills/antigravity-delegate/scripts/control.py run "补充 README 的安装说明" --allow README.md --dry-run
```

命令返回结果 JSON、工作树、Diff 和检查日志路径。完整结果保存在 Git 公共元数据目录
`agy-runs/<run-id>/result.json`；控制台只展示最多 20 个变更路径。
READY_FOR_REVIEW 只表示可交回审查，检查没有配置时会明确显示 NOT_RUN。
检查默认原生 argv；确需 shell 语法时显式增加 --shell-checks。共享执行内核提供单命令与总超时，逐条复核变更。
不会自动提交、合并、重试或删除执行工作树。

## 什么时候使用完整流程

架构、安全、迁移、部署、需要持久审批或多轮返工的任务，使用
[高级任务流程](.agents/skills/antigravity-delegate/references/workflow.md)：
init → create → validate/route → start 或 prepare/launch/verify/collect → 独立审查。
路由按判断强度和上下文连续性选择后端；agy 实现后由控制器独立 verify，不以模型声明代替命令证据。
原 schema v2、审批、回执和 DONE 门保持兼容。

## 权限与验证边界

--allow 与保护路径用于检查实际改动，Git 工作树只隔离 Git 状态；它们不是系统沙箱。
Codex 原生子代理继承父会话权限，代理文件中的 sandbox_mode 不产生独立只读权限。
可选模型配置只服务高级编排，安装或离线配置 PASS 都不证明实际模型可用。
本轮使用伪执行器完成工程验证；真实 agy 登录、编码效果和用量仍需实际测量。

## 文档

- [日常使用指南](.agents/skills/antigravity-delegate/references/quick-start.md)：参数、结果、失败与后续审查。
- [文档导航](docs/README.md)、[命令参考](.agents/skills/antigravity-delegate/references/cli.md)。
- [本轮整合记录](docs/maintenance/upstream-integration-2026-10-28.md)、[当前状态](docs/STATUS.md)。
- [贡献指南](CONTRIBUTING.md)、[安全策略](SECURITY.md)、[成本测量](COST_METRICS.md)。

历史资料、旧任务和独立嵌套仓库保留用于溯源，见文档导航。许可证：[MIT](LICENSE)。
