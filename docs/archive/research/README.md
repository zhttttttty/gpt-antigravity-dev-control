# 历史研究资料

本目录由原根目录 `gpt-gemini/` 整理而来，保留早期方案与上游资料供溯源。
它们未在本次整理中进行在线核验，不能据此判断当前模型能力、额度或配置兼容性。

| 内容 | 文件 |
|---|---|
| 两套早期模型分工方案，原文合并 | [方案合集](model-routing-proposals.md) |
| Herdr 与上游编排项目的说明，原文合并 | [说明摘录](upstream-readme-excerpts.md) |
| Astra / Luna 方案网页原件 | [HTML 原件](sources/astra-luna-orchestration.htm) |
| Luna Max 方案网页原件 | [HTML 原件](sources/luna-max-workflow.htm) |
| 上游编排项目的局部文件快照 | [配置与指南目录](orchestrator_repo/) |

`orchestrator_repo/` 是局部参考快照，没有完整安装器；不要将其视为本项目的运行配置。
旧网页中的外部资源未作离线完整性核验，HTML 文件本身保持原字节。

## 原文件对应关系

| 原 `gpt-gemini/` 路径 | 当前位置或处理方式 |
|---|---|
| `方案1.md`、`方案2.md` | 合并到 `model-routing-proposals.md`，各自正文完整保留 |
| `herdr_readme.txt`、`repo_readme.txt` | 合并到 `upstream-readme-excerpts.md`，各自正文完整保留 |
| `887c1b9f-4ba4-4f3c-9f4b-3fa65cbae5d0.htm` | `sources/astra-luna-orchestration.htm` |
| `dfa910ab-ca6b-49e9-bb61-bd1b63e6f7ba.htm` | `sources/luna-max-workflow.htm` |
| `file1_text.txt`、`file2_text.txt` | 已移除；逐行去除空白后，每行均能在对应 HTML 可见文本中找到 |
| `orchestrator_repo/` | 内部文件及相对目录原样保留 |

项目外的恢复备份及具体校验结果见[整理记录](../../maintenance/cleanup-2026-10-28.md)。
