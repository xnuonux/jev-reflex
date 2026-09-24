# Version 0.6.0 verification

Windows qualification on 2026-09-24. This extends the historical v0.5 evidence;
it does not relabel earlier checks as tests of this release.

## Local and independent checks

- Python regression suite: 133 passed. This includes 20 new workflow/local-evidence
  cases; those counts overlap and must not be summed.
- Node pi bridge suite: 5 passed.
- Non-editable wheel, outside-source working directory: 18 MCP tools, protocol
  2025-11-25, actual calls through the installed server, zero live inference.
- Separate GPT-6 Sol max source review and disposable injected-transport probes.
  Review found and rechecked zero-inference workflow identity, repeated holdout
  exposure, writer contention and read-only artifact retrieval. Final disposition:
  accepted within that source/API scope. This reviewer did not qualify deployment
  or model accuracy.

The source manifest is `verification-v0.6.0.json`. Runtime installation and release
assets are checked against the qualified sources; original evidence is retained.

## Live direct-TypeSafe diagnostic

Seven selected non-secret work packets made eight calls to pinned `jev-1.13.0`
(skill selection uses two stages). Seven identical workflow replays made zero
additional calls. No pending requests remained. Every response passed the provider
contract; semantic acceptance is a separate matter:

| Packet | Observation |
| --- | --- |
| Progress trace | Uncertain; progress/useful-evidence probabilities did not meet acceptance gates |
| Skill shortlist | Preferred the verification skill, but candidate-fit abstained; no final skill accepted |
| Worker inbox | Surfaced a review finding and completion; repeated branch-status report was routine |
| Patch review | No accepted flag; some questions remained unknown, not a clean-review certificate |
| Handoff | No accepted flag; constraint/next-step questions remained unknown |
| Memory comparison | Identified a scoped exception; other dimensions remained unknown |
| Conditional decision | Test operation selected, target abstained; no final dispatch recommendation |

Thresholds were not weakened to make these examples pass. This is an authored
smoke diagnostic, not a blind accuracy benchmark, demonstrated productivity gain,
or grounds for automatically accepting model review. A matched held-out workflow
comparison remains necessary for those claims.

The existing personal installation initially used OpenRouter and returned HTTP 402
for seven distinct workflow packets. Those failures remain recorded, with no
retry on replay. The operator then explicitly selected the existing direct
TypeSafe route for a separately identified diagnostic. There was no automatic
fallback or account top-up.

All fifteen attempted calls retained their conservative $0.02 reservations:
$0.30 total is local accounting, **not reported provider billing**. TypeSafe
reported token usage but no USD charge. Prior ledger rows, quota policy and host
configuration were preserved. No inference campaign was restarted or reset.

## Integration boundaries

The personal Codex plugin now launches the installed public package using the
explicit direct route. A fresh MCP process exposes all 18 tools. Already-running
sessions may retain their old tool inventory until normal reload; no automatic
tool interception or Codex-internal model replacement is claimed.

Artifacts intentionally retain supplied plaintext locally. Calibration consumes
caller-supplied predictions and labels; freshness means only unexposed in this
local ledger. Neither feature authenticates a caller or proves external source
freshness. No live Resident, autonomous action, permission or consciousness claim
follows from this release.

Claude Code, full pi UI, other model hosts, Linux/macOS and other Python versions
were not exercised by this Windows release check. Hosted CI status is reported
separately from these local results.
