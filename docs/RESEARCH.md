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

The motivating [Mika X post](https://x.com/mika_systems/status/2101686148338798610) was not accessible during this research. No content, linked implementation or performance figure is attributed to it. Third-party profile snippets were not used as implementation evidence.

## Next useful work

Prioritize matched real-task evaluations and actual host round trips. Consider explicit source collectors, optional host hooks, configurable calibrated thresholds, and tariff-estimated direct-provider accounting only with their own contracts and evidence. More automatic calls are not inherently more useful. Preserve a cheap no-call path.
