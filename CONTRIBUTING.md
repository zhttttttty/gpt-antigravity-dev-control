# 贡献指南

## 修改原则

保持 schema v2、任务身份、回执和生命周期的兼容性；破坏性变化提供版本化迁移说明。
修改任务验证、Scope、审批或 DONE 逻辑前，先更新相关规格与测试。
架构、公共契约或持久状态语义变化先记录 ADR，再实现。

执行者按 task.yaml 的范围实现，不自我批准；验收以 Git 快照和实际证据为准。
保持本地优先，不引入隐式远程调度、自动合并或不可验证的成本承诺。

## 开发检查

完整开发环境使用 Python 3.11+、Git、PyYAML；PowerShell 协议在 Windows 验证。
在外层仓库根目录执行：

```powershell
python -m pip install -r .agents/skills/antigravity-delegate/scripts/requirements-local.txt
python -m compileall .agents/skills
python -B .agents/skills/antigravity-delegate/scripts/control.py --help
python -B .agents/skills/antigravity-delegate/scripts/control.py check-orchestration
python -B .agents/skills/antigravity-delegate/scripts/control.py --repo tests/fixtures/control-project check-orchestration
python -B -m unittest discover -s tests -v
powershell -NoProfile -ExecutionPolicy Bypass -File tests/test_multi_agent_protocol.ps1
```

CI 另解析 YAML 与 PowerShell 脚本，完整步骤见 [.github/workflows/ci.yml](.github/workflows/ci.yml)。
Python 测试与 PowerShell 调度测试使用临时仓库及伪执行器，不调用真实 Provider。
CI 使用 fetch-depth: 0，确保历史控制器锚点可核验；Skill 同步测试已改为 unittest 并随全量检查执行。
测试夹具的配置 PASS 不能代替目标项目检查。当前外层已安装默认配置，实际模型可用性仍需单独验证，见[状态页](docs/STATUS.md)。

## 文档维护

- 入口与维护位置见[文档导航](docs/README.md)，不要另建一份内容相同的生命周期指南。
- 命令参数对照 argparse 与实际 `--help`；状态边对照 `ai.py.ALLOWED`，证据门对照 `task_data.py`。
- 项目规格填在 `.ai/project/`；分发模板保留通用占位符，不把当前项目状态写进模板。
- 区分模板偏好、实际配置、历史回执与本次运行结果。注明未运行的验证，保留历史记录。
- 纯文档变更检查本地链接、示例及 `git diff --check`；不以文档修正之名修改代码或任务状态。

## 提交与审查

非简单修改使用 Pull Request，说明具体问题、最终行为、兼容性及实际验证范围。
修改协议或行为时更新 CHANGELOG；纯文档整理不自动升级 VERSION。
报告日志前先脱敏，遵守[安全策略](SECURITY.md)。不要将测试通过等同于人工合并授权。
