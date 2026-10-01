# ADR-004：风险自适应委派与控制器验证

状态：接受，2026-10-01。

## 背景

固定把所有 `delegated`/`approval_required` 任务交给 Antigravity，会让语义判断、架构、
安全和强上下文连续性任务发生长时间空转或无效返工。让执行器自行完成全部测试并填写
命令证据，又会把实现和验收混在同一模型会话中，增加上下文与证据可信度问题。

## 决策

- 风险只决定是否需要审批；实际后端由工作类型、判断强度、上下文连续性和验收确定性决定。
- 低判断、范围明确且可确定验收的机械任务优先交给 Antigravity。
- 语义、安全、架构、高判断、强连续性或低确定性任务默认使用 direct Codex；覆盖必须同时
  有结构化 `routing_override` 声明和绑定当前契约的独立 approval artifact。
- Antigravity 只实现、运行聚焦检查、提交候选并把回执标为 `IMPLEMENTED`。
- agy 完全退出后，由控制器按 adversarial probes、fast gate、final gate 顺序执行契约命令，
  填写工作区和命令证据，再将回执转为 `COMPLETE` 或 `FAILED`。
- Provider/启动失败消耗 `max_infra_retries`；独立审查退回候选才消耗
  `max_implementation_reworks`。旧 `max_execution_attempts` 仅用于旧契约兼容。
- 受控复用 partial 必须有精确 writable 清单、已退出进程证据和结构化审批；不得复制、
  stash/apply 或由 Root 代提交候选。

## 结果

机械工作仍能转移到本地模型以节省原生额度，高价值判断留在 Sol。确定性验证从模型会话
中分离，失败能区分基础设施重试和实现返工。代价是任务契约字段更多，且委派流程增加一次
显式 `verify --approve`。

## 验证与回滚

单元测试覆盖自适应路由、结构化覆盖、分阶段验证、失败短路、增量上下文和两类 partial
复用。回滚须同时恢复任务模板、控制器、回执协议和说明文档；不得只恢复路由文案而保留
不兼容的运行状态。
