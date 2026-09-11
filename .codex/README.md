# Codex Project Model Routing

`.codex/config.toml` provides project defaults: Luna max for planning and
integration, Luna medium for native execution, and Astra low for independent
review. The `.ai/` control plane remains authoritative for task state, scope,
risk gates and receipts.

Choose the bounded roles in `.codex/agents/` as needed. Native threads default
to two; the root coordinates native and agy work at a combined maximum of two
active units. This is a coordination rule, not a cross-process lock. See the
[Hybrid Orchestration guide](../docs/HYBRID_ORCHESTRATION.md) for lifecycle,
limitations and validation. Model defaults do not change task authority or
override explicit user choices.
