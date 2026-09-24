# Research and related work

Public-source reconnaissance, 23 September 2026. This release reviewed upstream docs and selected repository surfaces; it did not run competitors or measure their claims. No competitor implementation was copied.

## Provider facts that shape the design

[TypeSafe's API](https://docs.typesafe.ai/api) supports typed Choice, Score and Noul questions over shared state. The [model documentation](https://docs.typesafe.ai/models) lists `jev-1.13.0`; the [confidence guide](https://docs.typesafe.ai/confidence) explains the returned statistics. Direct usage reports input/output tokens rather than billed USD. Reflex exposes Choice/Noul and pins the returned model; Score needs its own useful, qualified contract before inclusion.

[Jev's documented limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13) include literal interpretation, arithmetic/counting weaknesses, irrelevant-context sensitivity and adversarial state text. These informed small packets, explicit uncertainty, retained evidence and separation from host authority. [TypeSafe's coding-agent guidance](https://docs.typesafe.ai/introduction/coding-agents) places Jev alongside the coding model, not in its place.

The [official Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python) and [JavaScript SDK](https://github.com/typesafe-ai/typesafe-sdk-js) already cover normal typed API calls. Reflex adds decision lifecycle and agent workflow contracts. Its bounded no-retry transport is deliberate; it does not need another general-purpose SDK.

## Existing integrations worth knowing

| Project | Existing focus observed | Lesson adopted in our design |
| --- | --- | --- |
| [itsmostafa/typesafe-mcp](https://github.com/itsmostafa/typesafe-mcp) | Go CLI/MCP and multiple routes | Portable transport alone is not differentiation; distinguish a native multi-question request from per-item fan-out. |
| [jkudish/jev-mcp](https://github.com/jkudish/jev-mcp) | Named workflows, thresholds, usage and typed outputs | Useful recipes should preserve uncertainty and avoid calling judgment verification. |
| [rashedInt32/jev-mcp](https://github.com/rashedInt32/jev-mcp) | Node MCP/Claude integration and optional file input | Source collection and disclosure deserve explicit boundaries. Reflex reads no workspace files automatically. |
| [Brainwires/jevwire](https://github.com/Brainwires/jevwire) | MCP, embedded decision library and Claude hooks | Hooks are host-specific. A common core should not claim universal automatic interception. |
| [jal-co/jev-agent-browser](https://github.com/jal-co/jev-agent-browser) | Typed browser action selection with parent verification | Domain execution adapters need their own contracts; they are not part of this coding-decision release. |

Reflex's focus is shared durable accounting, stable operation identity, exact settled-result reuse, reversible source-bound context selection, and typed downstream feedback. These features are testable engineering differences, not evidence that it outperforms those projects.

The motivating [Mika article, "Jev: The 9-Step Blueprint for Building a Faster Decision Brain for AI Agents"](https://x.com/mika_systems/status/2101686148338798610) was inaccessible during v0.3 authoring and subsequently read in full through the owner's open browser for v0.4. Its useful lessons: narrow answer contracts, independent questions over shared state, confidence distinct from correctness, deterministic composition, explicit eligible actions, re-observation after effects, whole-workflow costs, and task-specific shadow evaluation. Its demos span feed filtering, UI selection, voice actions and lead triage; those are possibilities, not integrations delivered here.

v0.4 applies those lessons through shared requests, resumable bulk packing, host-owned admission and offline confusion matrices. The article's cited 13-question performance comparison and third-party demo numbers were not reproduced here; no speedup or cost reduction is attributed to Reflex from them. Score and autonomous action loops remain outside this release's qualified contract.

Current [TypeSafe limits](https://docs.typesafe.ai/models) list 64k tokens per request, 32k state-plus-longest-question, 1,200 requests/minute and 250,000 tokens/second, with an explicit warning that rates change. Native count and concurrency are different quantities. Our UTF-8 byte ceilings are a conservative packing heuristic, not those token counts. [Speculative fan-out](https://docs.typesafe.ai/patterns/fan-out) explains when independent conditional questions can share a request; genuine answer dependencies still require later calls.

## Next useful work

Prioritize matched real-task evaluations and actual host round trips. Consider explicit source collectors, optional host hooks, configurable calibrated thresholds, and tariff-estimated direct-provider accounting only with their own contracts and evidence. More automatic calls are not inherently more useful. Preserve a cheap no-call path.
