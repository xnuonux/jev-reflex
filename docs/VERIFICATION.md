# Verification: public 0.3.0

Local qualification on 24 September 2026 UTC. Windows, Python 3.13.15, MCP 1.30.0 and Pydantic 2.13.5. The accompanying `verification.json` binds the tested runtime/test/tool sources by SHA-256. Documentation changes do not change those source hashes.

| Check | Observed result |
| --- | --- |
| `python -m unittest discover -s tests -q` | 65 tests passed, zero failures |
| `node --test adapters/pi/bridge.test.mjs` | 4 tests passed, zero failures |
| `python -m build --no-isolation` | Source distribution and universal Python wheel built |
| Non-editable wheel installation | Installed into an isolated virtual environment |
| `python tools/verify_installed.py` | Installed package from outside source cwd, offline demo, six MCP tools, disabled context request preserves mandatory evidence |
| MCP negotiation | Official SDK client/server negotiated `2025-11-25` |
| Original personal plugin | Original four runtime files retain their pre-extraction hashes; not upgraded or reconfigured |

The 65 Python cases include real SQLite contention, two-process duplicate protection, response validation, threshold edges, budget admission, privacy-marker sweeps, source/pointer binding, required pins, reuse invalidation, typed outcomes, CLI setup and actual MCP transport. All provider responses in these tests are injected fixtures. The demo's one provider invocation is synthetic, not a paid call.

## Independent review

A separate GPT-6 Sol reviewer ran its own offline probes against the public source. It found and rechecked fixes for direct-route billing-field acceptance, missing generic threshold binding, source-byte hash semantics, initialization with legacy quota overrides, oversized reported cost settlement, request-model binding, and aggregate unknown-cost visibility. It additionally inspected context fallback, JSON operation restrictions, pi UTF-8/cancellation boundaries and evaluation attribution. Independent means separate from the builder; it is not a third-party human security audit.

The review preserves two limits: distinct-ID in-flight calls are not coalesced, and evaluation verifies only pairing of caller-declared hashes/measurements. Neither is marketed as stronger than delivered behavior.

## Not established by this release

- No fresh paid TypeSafe/OpenRouter inference campaign or live comparative performance benchmark.
- No end-to-end Claude Code, Codex, OpenCode, pi or DeepSeek-backed host session was run as part of public-package qualification. The SDK/bridge paths and documented host setup have different evidence levels.
- No universal MCP revision/client conformance claim. The negotiated revision above is the tested one.
- No measured accuracy gain, token savings, cost reduction or superiority over another wrapper.
- No authenticated tenant isolation, adversarial host protection, ledger rollback protection or provider-enforced billing cap.

The repository CI matrix is configured for Python 3.11 and 3.13 on Windows, Linux and macOS. Publication-time run results are recorded in the release notes; configuration alone is not a passing run. Local evidence remains valid independently of remote CI availability.
