# 项目验收

## 高级任务的完成标准

- 修改满足相关需求，契约范围、Git 快照、检查记录及验收证据一致。
- 必要检查通过，无未处理的阻塞发现；可选 NOT_RUN 必须符合契约并说明理由。
- 执行回执为 COMPLETE，独立 QA 为 REVIEWED，QA/Review 结论一致。
- 高风险或启用控制项满足事前审批、跨家族审查或记录豁免、人工合并批准、回滚要求。
- Root 检查实际证据；控制器接受结构化字段不替代人工判断。

## 开发检查

日常 run 的交接还须满足：有效执行器报告、真实退出码、范围和 Git 历史检查，
以及全部调用者检查通过。没有提供检查时明确为 NOT_RUN，最高状态为 READY_FOR_REVIEW，
不以轻量交接替代本页高级任务的 DONE 门。

在仓库根目录执行，命令与 `.github/workflows/ci.yml` 对齐：

```powershell
python -m pip install -r .agents/skills/antigravity-delegate/scripts/requirements-local.txt
python -m compileall .agents/skills
python -B .agents/skills/antigravity-delegate/scripts/control.py --help
python -B .agents/skills/antigravity-delegate/scripts/control.py check-orchestration
python -B .agents/skills/antigravity-delegate/scripts/control.py --repo tests/fixtures/control-project check-orchestration
python -B -m unittest discover -s tests -v
powershell -NoProfile -ExecutionPolicy Bypass -File tests/test_multi_agent_protocol.ps1
```

外层根目录和固定夹具均需通过配置一致性检查。夹具 PASS 只证明样例一致，
不能代替真实目标项目检查；两者都不证明实际模型可用。
CI 另包含 YAML 解析与 PowerShell 脚本解析；详见[贡献指南](../../CONTRIBUTING.md)。

只改文档时检查本地链接、示例参数和示例契约即可；修改协议、Scope、回执或状态门时运行相关回归及完整必要检查。
无 Provider 调用的测试不能证明真实 agy 登录、模型路由、编码质量或节省成本。

3.5.0-local 还验证自适应 route/start 一致性、显式审批不降级、独立 verify 的分阶段短路，
以及共享检查模块的原生参数引用、缺失程序和超时子进程清理。Skill 同步测试须进入 unittest，不能仅定义 pytest 函数而未执行。

## 发布、合并与回滚

任务从 REVIEW 请求 DONE 通过后，仍需按仓库流程人工合并已审查快照。
高风险任务保留实际审批人、批准时间和可执行回滚内容。
版本号、CHANGELOG 和行为必须一致；纯文档整理不自动升级运行版本。
当前任务未完成项与本次文档检查记录见[状态页](../../docs/STATUS.md)。
