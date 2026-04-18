# Copilot Collaboration Defaults

These defaults apply to every response in this workspace.

1. Update README when there is significant, user-visible progress.
2. Use simple explanations: what changed, why it improved, or why it became worse.
3. Automatically brainstorm the next best stage after each major result.

## Guardrails

- Keep changes minimal and focused.
- Do not update README for trivial or no-op progress.
- If a result is mixed, explain both gains and regressions clearly.

## Direction Anchor (Mandatory)

Before major planning or implementation, consult `docs/research/openclaw_local_evolution_6m_execution_plan.md` and align actions to its month/week deliverables.

## Capability Expansion Mandate

For work that advances project goals, the agent is allowed to use additional local or external resources when useful, including:

- new local or hosted LLM choices for benchmarking and comparison
- internet research for architectures, papers, and implementation patterns
- downloading open-source assets, tools, or reference implementations

When a removable technical constraint blocks progress, the agent should propose and implement a safe removal path rather than defaulting to narrow local minima.
