# 成本与效率测量

比较 direct 与 Antigravity 时，以“通过独立审查的候选”为单位，不以首次 exit 0、输出
字节或单次模型响应为单位。每个任务记录：

- planner、executor、verify、reviewer 的墙钟耗时；
- implementation attempts、infra retries、超时和语义返工次数；
- adversarial、fast、final gate 的运行次数及重复命令数；
- context、diff、日志与 receipt 字节数；
- 独立审查的 P0/P1 数和最终 PASS/REWORK/BLOCKED；
- Provider 实际返回的 Token。未返回时写 `UNKNOWN`，不得从输出字节推算。

优先比较 `independent PASS / 总耗时`、`independent PASS / 已知 Token` 和每个接受候选的
返工次数。同一账号的额度百分比受其他会话影响，只能作为粗粒度旁证。A/B 比较必须使用
相同仓库基线、任务契约、验收与审查强度；否则只能报告定性观察。

控制器 compact receipt 中的 `usage` 缺失值保持 `null`/`UNKNOWN`。未来 Provider 暴露
可靠用量字段时再写入，不得由模型自行声明精确节省比例。
