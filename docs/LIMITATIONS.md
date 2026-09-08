# V3.1 local limitations

The local path is implemented separately; see [its recovery and limitation
details](LOCAL_DELEGATION.md). It needs actual agy login/tool permissions and does
not automate merge, independent verification, retries, runtime backup or crash
recovery. Compact receipts distinguish observed Git state from executor-reported
tests. The original V2/V3 Lite limitations below remain relevant to those paths.

# Current Limitations

V3 Lite is intentionally a lightweight reference implementation, not a production distributed scheduler.

## Current boundaries

- Provider adapters depend on external API contracts and model/agent identifiers that can change. Keep `.ai/orchestrator/config.yaml` configurable and verify provider compatibility before real use.
- SQLite is local coordination state. It is not designed for multi-host distributed locking.
- `max_workers` exists as configuration, but the current implementation dispatches tasks sequentially from one process; true concurrent worker scheduling is future work.
- The repository protocol is more mature than the automation layer. Git, task contracts and receipts remain the recovery source if Orchestrator runtime state is lost.
- Real provider calls require your own API keys and may incur usage costs.
- High-risk work should remain human-supervised even when automation is enabled.

## Non-goals for V3 Lite

Redis, RabbitMQ, Kubernetes, a web dashboard, multi-machine workers and enterprise RBAC are deliberately excluded until real usage demonstrates a need.
