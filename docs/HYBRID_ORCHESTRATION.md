# Codex 原生角色与 Antigravity 混合执行

本项目吸收 [codex-astra-luna-orchestrator 的 Plus 配置](https://github.com/donvito/codex-astra-luna-orchestrator/tree/014b1d7c48c39087beec8aa4f1ca022053ac17b3)，由一个 Root 协调两种执行路径。决策见 [ADR-002](../.ai/decisions/ADR-002-hybrid-orchestration.md)，规则以 [.ai/rules/ORCHESTRATION.md](../.ai/rules/ORCHESTRATION.md) 为准。

| 职责 | 项目默认值 |
|---|---|
| 规划、任务拆分、集成 | Luna max Root |
| 原生 explorer / worker / tester / researcher | Luna medium |
| 原生独立 reviewer | Astra low，只读 |
| 较大且边界明确的实现 | Antigravity / Gemini，独立 Worktree |
| 范围、回执、验收和合并 | 现有 `.ai/` 协议和风险门 |

按任务选择角色，不要求每次跑完整编队。小改动可以由 Root 直接完成，但仍须满足对应风险级别的独立审查。高风险任务必须事前审查，必要时提升推理档位或进一步审查；不能只靠最后一次 Astra low。不同模型名称不自动等于已完成跨模型家族的独立二次审查。

## 一次功能如何执行

以 CSV 导出为例：必要时先由 explorer 定位数据流，Root 明确范围和验收，再选定一个实现负责人。

- **原生 worker**：使用 `execution.mode: direct`，`roles.executor` 写实际角色（如 `worker`）。需要隔离时先运行 `control.py start TASK --worktree`，再把该 Worktree、契约、检查项和回执路径交给原生代理。Root 显式核对范围、回执和证据后，使用现有命令迁入 REVIEW。控制器不会替原生代理自动收集证据。
- **Antigravity**：使用 `execution.mode: delegated`、`roles.executor: antigravity`、`adapter: antigravity_cli`。继续经过 probe、route、prepare、launch、collect；高风险本地任务按原规则升级为 `approval_required`，绑定当前契约审批。

不要将原生代理传给 agy adapter，也不要发明第四种 execution.mode。Root 直接调度 Antigravity，不额外启动 Luna 来转发。实现完成后，tester 检查该 Worktree 和版本，reviewer 审查相同快照的 diff 与证据；修复后更新受影响的测试和审查证据。Root 记录 QA/Review 并按原状态机交付。`collect` 成功不等于验收通过，原生任务也不能绕过风险审批。

## 并发与失败处理

原生子代理同时打开的线程默认上限为两个；Root 另行协调原生代理与 agy 活跃任务合计最多两个，可以是两个原生任务、两个 agy 分片或各一个。这个总上限目前不是跨进程硬锁。启动占用两个槽位的 agy 批次前应结束原生工作；已有任务状态不明时暂停新派发。

同一 Worktree 一个写入者，包括产生缓存或修改测试文件的 tester。独立写入使用不同 Worktree；沙箱限制权限，不能防止同目录文件冲突。仅 HEAD 不足以识别未提交修改，交接时同时记录工作区 diff、状态和新增文件。

后端失败时保留失败记录，先检查部分修改，再由 Root 在原审批和重试边界内选择恢复或重新分配。禁止对状态不明的目录启动竞争写入者，也不能把失败报告为完成。

## 配置与验证

项目使用本地 `.codex/`，需要受信任的项目和支持这些配置的 Codex 版本。运行时显式模型/推理设置可能覆盖默认值，当前已启动的 Root 不会因为改文件自动切换模型。既有全局 `luna_worker` 保持不变；本项目实现角色名为 `worker`。合并配置时按键处理，不直接用安装器覆盖整个目录。

离线检查需要 Python 3.11+ 和现有 PyYAML 依赖：

```powershell
python .ai/scripts/control.py check-orchestration
python -m unittest discover -s tests -v
```

检查范围是 `.ai/config.yaml`、原生 TOML 角色与新任务模板的一致性。它不验证完整 Codex 配置格式、不读取全局覆盖、不调用模型或 agy，也不证明运行时沙箱生效。真实验证应在受信任项目中执行一个已授权的有界任务，记录实际角色、模型、推理档位、Worktree/版本和回执。

按 [用量测量](../COST_METRICS.md) 同时记录两侧 Provider 用量、耗时、返工和审查时间。不能把消耗转到 Antigravity 算成成本消失，也不承诺固定节省比例或 Plus 续航。
