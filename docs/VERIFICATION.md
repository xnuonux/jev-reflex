# Verification

## Public 0.5.0

Stateful controller qualification: Windows, Python 3.13.15, Node 24.18.0,
MCP 1.30.0. Exact final source hashes and counts are in
`verification-v0.5.0.json`. The earlier 0.4 manifest remains historical.

Final local results: **113 Python tests**, including **20 controller tests**,
**5 Node bridge tests**, **6/6 targeted mutations detected**, and an installed
**13-tool MCP** round trip. Counts overlap; do not sum controller and Python totals.

An independent reviewer found semantic-question substitution, lost support/vote
provenance and stale next-step/challenger reporting in development. Those were
fixed and the reviewer reran the controller suite, with no remaining blocking
defect found in the inspected cut. This is independent agent review, not a human
audit or live-provider qualification.

The new boundary is exercised through actual JSON CLI processes, official-SDK
stdio MCP and the pi subprocess bridge. A non-editable installed wheel is tested
outside the source checkout with credentials removed. New controller calls make
zero inference requests. All inference in these release checks is injected fake
transport, labelled as such in the receipts.

Six targeted source mutations in isolated copies must fail the controller tests:
removing signal binding, source binding, one-vote enforcement, revision checking,
confirmation counting, and invalidation of a pre-pause source. See
`evidence/controller-mutations-v0.5.0.json`. This checks actual failures, not just
the presence of guard clauses. It is not an exhaustive mutation campaign.

The deterministic demo reduces five switches to one on a deliberately alternating
trace, with one extra observation before accepting a sustained change. No live
agent productivity or general accuracy improvement is claimed. Temporal stability
can preserve a wrong interpretation; source limits, abstention, visible evidence
and explicit corrections make that inspectable, not impossible.

## Historical public 0.4.0

Local qualification on 24 September 2026 UTC: Windows, Python 3.13.15,
Node 24.18.0, MCP 1.30.0 and Pydantic 2.13.5. `verification.json` binds
runtime/test/tool sources by SHA-256. Older release evidence remains in Git history.

| Check | Observed result |
| --- | --- |
| Python unittest discovery | **91 passed**, zero failures |
| Node pi bridge suite | **5 passed**, zero failures |
| Source distribution and wheel | Built without dependency changes |
| Non-editable wheel, outside source cwd | **10 MCP tools**, disabled shared and 1,000-item bulk call, inspect and cancel; zero paid calls |
| MCP negotiation | Official SDK negotiated `2025-11-25` |
| Original private plugin | Not changed by this public refinement |

The suite includes a completed **1,000-item fake-provider job**, complete paginated
coverage, a **10,000-item CLI submission** with inference disabled, and a 10,000-item
pi bridge carrier. Those are different checks, not three live throughput tests.
Shared requests verify more than eight questions and one occurrence of shared
state. Native transport boundaries accept more than the former 16 KiB and reject
oversize input before a network call.

Real process tests cover two controllers sharing child ownership and a second
MCP request cancelling a job while its fake provider waits. Only the admitted
child settles; remaining children stay undispatched. Tests also cover complete
preflight validation, budget and rate admission, restart replay, failed/pending
children, pre-registration cancellation, identity conflicts and raw source marker
exclusion from durable state.

## Independent review

A separate GPT-6 Sol reviewer inspected source and ran independent synthetic
probes in temporary directories. Review found and verified fixes for recipe plan
request digests differing from reserved calls, tightened capacity preventing
settled replay, cancellation missing preflight, and clock rewind blocking read-only
replay. New admission still refuses a rewind. Review also prompted route-specific
configuration, active/uncertain status separation, clearer caller-asserted privacy
scope and explicit counts for predictions with unknown truth. The final bounded
review found no remaining release-blocking defect in inspected paths. This is
independent of the builder, not a third-party human audit.

## Limits retained

- The original release checks above used no paid provider calls. A subsequent
  [direct TypeSafe real-corpus stress test](LIVE-GODSKILLS-20260924.md) submitted
  452 questions in 25 requests, including a rejected response. It is separate
  evidence, not a comparative agent-workflow benchmark. Byte limits remain
  heuristics, not an exact provider tokenizer.
- Cancelling an MCP request/disconnection is not durable job cancellation. The
  bounded worker can continue; use `cancel_job` and inspect. Issued calls cannot
  be recalled and are not refunded. A crashed child can remain pending.
- Same-ID replay is protected; distinct job IDs are not coalesced. Progress is
  not authenticated tenant isolation, rollback protection or a provider billing cap.
- No fresh end-to-end Claude Code, Codex, OpenCode, pi-host or DeepSeek model
  session. Actual SDK/CLI/bridge checks are distinguished from those host claims.
- Shadow labels remain caller-reported. No automatic threshold tuning or
  calibration follows from a valid report.

CI is configured for Windows/Linux/macOS and Python 3.11/3.13. The prior publication's
hosted jobs were blocked before execution by account runner provisioning; the
historical result remains in the machine-readable record. Local Windows results
do not establish Linux/macOS or Python 3.11 qualification. Check the current
Actions run separately; no passing cross-platform badge is claimed.
