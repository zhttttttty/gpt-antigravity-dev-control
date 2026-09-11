# 贡献指南

欢迎贡献。

## 原则

- 保持任务协议向后兼容；破坏性变化必须提供版本化迁移。
- Executor 必须受 task.yaml 权限和范围约束。
- 优先相信仓库证据，不直接相信模型声明。
- 保持本地优先、摘要优先，不向 main 增加远程调度或 Reviewer 服务。

## 开发检查

    python -m pip install -r .agents/skills/antigravity-delegate/scripts/requirements-local.txt
    python -m compileall .ai/scripts .ai/adapters .agents/skills
    python .agents/skills/antigravity-delegate/scripts/control.py status
    python .agents/skills/antigravity-delegate/scripts/control.py --help
    python -m unittest discover -s tests -v

修改任务 Schema、Risk Gate、Receipt 或状态迁移前，先更新文档和 CHANGELOG.md。
非 trivial 修改使用 Pull Request，并说明变更、原因、兼容性影响和测试结果。
