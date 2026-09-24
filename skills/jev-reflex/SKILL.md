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
2. Choose the appropriate shape. `shared` sends one context packet once with many independent questions. `batch`/`recipe` sends independent item packets. `bulk` accepts up to 10,000 items and packs them automatically. Native defaults: 256 questions, 60,000 UTF-8 request bytes, 30,000 state-plus-longest-question bytes. Actual dependencies wait for earlier results; speculative independent questions may share a call and irrelevant answers can be ignored.
3. Use stable project/task/request IDs. Pin current inputs with a source snapshot. For context, use `jev_reflex_context` / CLI `context` so the supplied content and pointers are hashed automatically.
4. Pin required constraints, failing evidence, user instructions and critical counterexamples. Preserve original text and recoverable pointers even for lower-priority chunks.
5. Read the whole result: outer `ok` does not mean an item proposed anything or got it right. On abstain or unavailable, reason normally. Do not poll or generate new IDs to retry an uncertain paid call.
6. Recheck source relevance before using advice. The host chooses tools, arguments, model changes and actions under its existing policy.

## Workflows

`context_triage/v1`, `routing_advice/v1`, `tool_advice/v1`, `failure_triage/v1`, `change_impact/v1`, `evidence_gap/v1`, `risk_flag/v1`. Full field schemas: `docs/RECIPES.md` in the repository. Raw Choice/Noul are available for bounded semantic decisions. Score is unsupported.

Model/tool advice uses only supplied eligible options and can abstain. A timing label does not establish a flaky test. No-gap-visible does not certify completion. Negative risk does not grant permission. Proposed context reduction does not mean actual token savings.

Exact recipe reuse is opt-in and applies only after a matching result settled. Same-ID replay protects against duplicate dispatch; distinct concurrent IDs are not coalesced. Never invent a source version merely to obtain a cache hit.

Bulk jobs use the same operation ID and identical complete input across continuations.
Read `next_step` and `run_refusals`. `continue-same-input` means more undispatched
work remains: continue at an appropriate scheduling point, honoring rate/budget
backpressure instead of spinning. `pending` may mean a still-running or crashed
child; inspect it and preserve its accounting, never invent a new job to retry it.
`review-failures` needs host judgment. Use `inspect_job` and `next_offset` to read
all results. `cancel_job` prevents new admission; already issued calls can settle.
Cancellation is durable and cannot be undone by resubmitting. Selected source must
remain available to the caller: the job stores no raw-input spool. See `docs/BULK.md`.

## Close the loop

Record typed outcomes only after observing them: missed important evidence, routing rework, assessment, or measured downstream usage/duration. Use one measurement ID per actual shared run. Missing data stays unknown. Do not ask Jev to grade itself as independent ground truth. Compare complete workflows, including extra calls and rework, before claiming improvement.

For labelled decisions, `jev-reflex shadow-report` reports per-route confusion
matrices, precision/recall, abstention coverage and confidence-bin accuracy.
A confident label can be wrong; measure this on representative held-out data.
The report does not tune thresholds or certify safety automatically.
