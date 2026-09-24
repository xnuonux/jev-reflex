# Live TypeSafe corpus stress test — 24 September 2026 UTC

Jev Reflex **v0.4.0** (`25e9c1305c5f229d2fab13c4d5e68a3ca245673b`)
was exercised against direct TypeSafe `jev-1.13.0` using existing public
upstream skill bodies. This adds real provider evidence to the release's
separate offline checks. It is not a provider saturation test or a comparison
against another agent workflow.

## Workload and results

A frozen Godskills collections manifest contained 4,139 grouped source bodies.
The run selected 180 complete bodies of 250–4,500 bytes, stratified by previous
candidate class, excluding language-variant groups and hashes appearing in
prior wave receipts. Bodies were read from pinned Git objects and SHA-256
verified, including explicitly recorded LF/CRLF checkout transformations.
This short-body sample is not representative of the whole corpus.

| Measure | Observed |
| --- | ---: |
| Real paid requests | 25 |
| Typed questions submitted | 452 |
| Structurally accepted answers | 444 |
| Questions quarantined with an invalid batch | 8 |
| Largest native request | 64 questions |
| Peak concurrent requests | 4 |
| Request latency, median | 0.683 seconds |
| Request latency, nearest-rank p95 | 0.810 seconds |
| Slowest request | 1.562 seconds |
| Provider input/output tokens | 225,236 / 14,107 |
| Tariff-estimated input cost | $0.009459912 |
| Conservative local reservations retained | $0.50 |
| Provider-reported dollar charge | Unavailable |
| Automatic paid retries / uncertain calls | 0 / 0 |

Latency includes the production transport subprocess and request/response work;
it excludes source preparation, independent review, pauses between foreground
invocations and authoring the handoff. Do not present it as end-to-end engineering
time. The local byte-rate limiter deferred dispatches without charging them.

The estimate uses the provider's [published input price of $0.042/M tokens](https://docs.typesafe.ai/models);
output tokens are free at that tariff. Token usage from **all 25 responses**,
including the rejected response, is included. The API supplies tokens, not USD
charges. Reservations are not an invoice, and were not reset to spend more.

## What the answers were useful for

The 180-body routing job yielded 90 proposals: 54 adapters, 32 reusable-method
candidates, 3 references and 1 stub. It abstained on 82 bodies; 8 remained
unavailable because their request was rejected. The 32 method candidates then
received eight independent structural questions each: triggers, procedure,
outputs, verification, recovery, exclusions, vendor dependence and uncertainty.
Of those 256 answers, 131 were proposals and 125 abstentions. An abstention is
not evidence that a skill lacks the queried property.

A GPT-6 Sol max reviewer classified 24 complete bodies before seeing Jev's
answers or the historical candidate classes. Jev proposed on 11, abstained on
11, and had no accepted result on 2. **10 of the 11 proposed labels agreed**
with the reviewer. The disagreement classified a workflow launcher as a reusable
method. An illustrative Wilson 95% interval for the 10/11 proportion is
0.623–0.984; the denominator is small and these are model judgments, not human
ground truth, representative accuracy or calibrated probabilities.

Source comparison produced two first-party candidate amendments for existing
Godskills owners: changelog evidence/recovery for Herald, and hierarchy-fidelity
checks for Logos. A generic feature-development amendment was rejected because
Forge/Phoenix already covered the mechanisms. No skill was installed or given
a terminal corpus disposition by this experiment.

## Failure found and preserved

One Choice response was:

```json
{"choice":"adapter","confidence":0.92,"probabilities":{"adapter":0.93,"reference":0.0,"method":0.02,"stub":0.04,"unclear":0.0}}
```

Its probabilities sum to **0.99**. The [provider contract says they sum to 1](https://docs.typesafe.ai/primitives/choice).
The strict validator refused the whole eight-question response with
`distribution-sum`. No normalization or weakened threshold was applied, and
the bulk job stopped. Seven siblings therefore lost their otherwise usable
responses too; they were not silently salvaged.

After inspecting the failed response, only the **39 items never reserved or
sent** were submitted under a separately recorded remainder job. No paid item
was retried. The original job remains a partial failure, not a retroactive pass.
Replaying both that failed job and the completed remainder made zero new calls.
A transport-spy negative control confirmed the exhausted budget refuses before
dispatch; it was not an extra provider request. The experiment policy was then
disabled.

Two offline regression tests preserve the observed malformed distribution,
batch quarantine, retained reservation, no-retry replay and bulk stop, alongside
a valid-distribution positive control. The focused provider/bulk/regression
group passes **29 tests**. This is separate from the live 25-request evidence.

## Refinements motivated by the run

1. **Per-question failure isolation needs an explicit contract.** A single bad
   answer currently invalidates all siblings and halts the job. A future version
   could retain independently validated siblings while making invalid items
   explicitly unavailable, with no automatic paid retry. That behavior is not
   implemented or claimed by this report.
2. **Failed semantic receipts should retain independently validated token
   usage.** Today the failed receipt lacks `usage_tokens`; this experiment
   recovered it from a separate response capture. Dollar cost remains unknown.
3. **Provider-specific tariff accounting would improve budget utilization.**
   The fixed $0.02 reservation is substantially above this run's token estimate.
   Changing that requires a versioned estimate contract, not silently treating
   a tariff estimate as a provider bill or refunding uncertain requests.
4. **Use atomic feature questions and a review queue.** The broad route label
   was often ambiguous. Preserve low-confidence cases and source evidence;
   strong agreement on a small accepted subset cannot justify automatic corpus
   completion, activation, licensing judgments or research conclusions.

Aggregate machine-readable evidence is in
[live-godskills-20260924.json](evidence/live-godskills-20260924.json).
Raw public-source bodies and private workstation paths are not republished here.
This test did not change the installed personal plugin, Resident runtime or
paused Godskills workers, and makes no claim about hosted CI or other operating
systems.
