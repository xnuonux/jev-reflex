---
name: jev-reflex
description: Use bounded Jev judgments for source triage, eligible model or tool advice, and coding investigation when this can reduce meaningful work. Keep reasoning and actions in the host agent.
---

# Jev Reflex for agents

Use the installed MCP tools, JSON CLI or Python API. Installation alone does not require a call. Read local status first when provider readiness or remaining budget is unknown. Never initialize, widen a budget, expose a key or reset accounting as part of an ordinary model decision.

## When to use a reflex

- You have several selected excerpts and need a reversible attention priority.
- A task can be routed among a roster the host has already approved.
- A bounded failure packet needs an investigation direction, not an asserted diagnosis.
- A patch needs a suggested review priority, or a claim needs an initial evidence-gap check.

Skip Jev when code can answer exactly, the judgment is trivial, required evidence must be read anyway, a call would exceed a disclosure boundary, or main-model reasoning is already needed. Do not offload permissions, numeric calculations, budget checks, credential choices, acceptance tests, or final completion declarations.

## Make one useful request

1. Use only selected authorized text. No secrets or ambient repository/chat upload. One batch is one disclosure boundary.
2. Form 1–8 independent items in one recipe/request. Dependent questions wait for the earlier result. The total provider packet is <=16 KiB.
3. Use stable project/task/request IDs. Pin current inputs with a source snapshot. For context, use `jev_reflex_context` / CLI `context` so the supplied content and pointers are hashed automatically.
4. Pin required constraints, failing evidence, user instructions and critical counterexamples. Preserve original text and recoverable pointers even for lower-priority chunks.
5. Read the whole result: outer `ok` does not mean an item proposed anything or got it right. On abstain or unavailable, reason normally. Do not poll or generate new IDs to retry an uncertain paid call.
6. Recheck source relevance before using advice. The host chooses tools, arguments, model changes and actions under its existing policy.

## Workflows

`context_triage/v1`, `routing_advice/v1`, `tool_advice/v1`, `failure_triage/v1`, `change_impact/v1`, `evidence_gap/v1`, `risk_flag/v1`. Full field schemas: `docs/RECIPES.md` in the repository. Raw Choice/Noul are available for bounded semantic decisions. Score is unsupported.

Model/tool advice uses only supplied eligible options and can abstain. A timing label does not establish a flaky test. No-gap-visible does not certify completion. Negative risk does not grant permission. Proposed context reduction does not mean actual token savings.

Exact recipe reuse is opt-in and applies only after a matching result settled. Same-ID replay protects against duplicate dispatch; distinct concurrent IDs are not coalesced. Never invent a source version merely to obtain a cache hit.

## Close the loop

Record typed outcomes only after observing them: missed important evidence, routing rework, assessment, or measured downstream usage/duration. Use one measurement ID per actual shared run. Missing data stays unknown. Do not ask Jev to grade itself as independent ground truth. Compare complete workflows, including extra calls and rework, before claiming improvement.
