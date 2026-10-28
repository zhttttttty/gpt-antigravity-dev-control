# 文档维护记录 — 2026-10-28

本轮只整理 Markdown。以当前外层仓库实现、分发模板、测试、CI 及任务记录为依据，
未修改运行代码、配置、任务状态或既有回执；未将嵌套仓库的较新版本合并进来。

## 主要改动

- 补齐 `.ai/project/` 中原为空模板的项目说明、架构、需求、验收和后续工作。
- 重写中英文 README，保留定位与快速开始，将参数、完整流程移到各自唯一维护位置。
- 新增[命令参考](../../.agents/skills/antigravity-delegate/references/cli.md)和[当前状态](../STATUS.md)。
- 重写统一控制流程，拆开 direct 与 agy 步骤；扩充任务字段、允许状态边和审批结构。
- 修正 collect 失败不一定迁入 BLOCKED、BLOCKED 重排不自动增加 attempt、上下文限制为 32,000 字节等细节。
- 更新文档导航、贡献指南、配置边界及故障排查，保留分发模板和历史 ADR 原文。

## 核实并公开的缺口

1. 外层缺少 `.ai/config.yaml` 和 `.codex/`，根目录配置检查实际 FAIL；夹具 PASS 不等于外层配置有效。
2. 普通 init 不安装 Codex profile，显式安装可能覆盖同名配置，且不生成 `.ai/config.yaml`。
3. `PROJECT_STATE.yaml` 仍是 READY / 空 active_tasks 摘要，控制器不会自动同步它。
4. status 等任务命令通过 Git 查找根目录，普通子目录不是隔离项目；配置检查则按指定目录读取。
5. 任务目录仍有 3 个 REVIEW、1 个 BLOCKED；review PASS 不等于 DONE，也不证明旧快照已经合并。

## 验证范围

- 5 项 CLI 路由测试、7 项配置一致性测试通过，共 12 项；均无 Provider 调用。
- 在独立临时 Git 仓库验证 init 保留已有项目说明、草稿需补齐、示例契约验证、direct 路由、
  已提交 HEAD 基线、start 创建工作树、主控 IN_PROGRESS 与工作树 READY 快照、单任务 JSON 状态。
- 检查维护范围内 Markdown 的本地链接、示例 YAML、状态表与实际状态机、CLI 示例参数及 Git 空白错误。
- 对照本轮前的 SHA-256 清单检查非 Markdown 文件未变化。

最终检查结果：35 份维护范围内文档、135 个本地链接、3 段 YAML 示例全部通过；
状态图的 9 条迁移与 `ai.py.ALLOWED` 一致，文档中原样提取的任务片段通过实际 validate。
707 个非 Markdown 文件与本轮基线逐一匹配，无新增非 Markdown 文件。

本次未运行完整回归、PowerShell 调度测试或真实 agy；历史任务的测试声明仍是历史证据。
本地链接检查排除原样保存的上游局部快照，不能保证其外部资源可用。

## 恢复依据

本轮修改前文档与非 Markdown 哈希清单保存在：

```text
C:\Users\Administrator\AppData\Local\Temp\codex-docs-before-20261028-154942\
```

其中 `documents-before.zip` 保存修改前文档，`non-markdown-before.json` 为完整性基线，
`example-validation.json` 和 `documentation-validation.json` 保存本轮检查摘要。
这是系统临时目录，长期保留前应另行复制。恢复前比较当前 Diff，避免覆盖后续修改。
