# Does Reflex actually improve your agent?

Measure the complete task, not only a cheap classifier call. Jev latency, extra tool round trips, context construction, errors and downstream rework can outweigh an otherwise correct triage decision. Use direct host reasoning as a baseline.

## A useful first experiment

1. Freeze a small representative set of task inputs. Include ambiguous and irrelevant packets, required evidence that looks unimportant, and source text containing adversarial instructions. Keep a held-out set.
2. Run the same host workflow with and without Reflex. Counterbalance order, retain identical task contracts, and record source hashes and actual input bytes privately. Do not give one condition answers learned from the other.
3. Independently score completion and missed-important-evidence. Record abstention/review burden, total latency, total provider cost, downstream tokens and rework. Use provider-reported cached-input counters; missing counters stay unknown.
4. Compare quality and expense together. A faster failure is not an improvement. Tune on training cases, then freeze thresholds and evaluate held-out cases. Preserve negatives.

Optional additional baselines: direct TypeSafe calls and a mature existing Jev wrapper. The related-project research is not a comparative benchmark.

## Local paired-report checker

```sh
jev-reflex evaluate < examples/paired-evaluation.json
```

PowerShell: `Get-Content -Raw examples/paired-evaluation.json | jev-reflex evaluate`.

This makes no inference. Input has schema `jev-reflex-paired/v1`, a caller-supplied `synthetic` boolean, and equal `baseline`/`candidate` populations. Each row must contain exactly:

`case_id`, `input_sha256`, `correct`, `important_missed`, `abstained`, `duration_ms`, `cost_microusd`, `input_tokens`, `output_tokens`.

The three judgments are booleans or null. Measurements are non-negative bounded numbers or null; costs and token counts must be integers. Duplicates, substituted case IDs, mismatched declared input hashes and non-finite values refuse. Unknown pairs remain explicitly unknown.

The report checks **structural pairing of caller reports**. It does not receive source bytes or independently authenticate a declared hash, verify an outcome, or establish whether a run was synthetic. Output states `source_bytes_verified:false`, `independent_verification:false`, `synthetic_label_source:"caller"`, and `causal_claim:false`. Retain raw run records and source manifests separately if you need auditable evidence.

The supplied example is deliberately synthetic: a candidate can become faster while becoming less correct. No measured performance uplift or benchmark victory is claimed for this release.

## Labelled shadow decisions

```sh
jev-reflex shadow-report < examples/shadow.json
```

This offline report accepts `{schema:"shadow/v1", labels:[...], cases:[...]}`.
Each case has exactly `id`, `route`, `truth`, `prediction`, `confidence`.
Truth and prediction are declared label IDs or null. Null prediction means
abstention, null truth means unknown ground truth, and null confidence means
unreported confidence. Confidence is a finite number in [0,1], not a correctness
certificate. When prediction is null, its confidence is excluded from bins.

Results are separated by caller-labelled route: confusion matrix (truth rows,
prediction columns), support, precision, recall, abstentions, coverage, selective
accuracy and confidence-bin accuracy. Recall counts abstentions as missed true
cases; selective accuracy measures only predictions with known truth. Unknown
truth and unknown confidence counts stay visible. The supplied fixture includes
a confident wrong answer, an abstention and unknown truth so that a tiny valid
report cannot be mistaken for proof of reliability. No threshold changes occur.

Labels are caller reports, not authenticated independent ground truth. Use
representative held-out specimens, independent labels and adversarial state
injection examples before selecting operational thresholds. Avoid broad accuracy
claims from aggregate routes or training cases reused as evaluation cases.

## Recipe feedback versus experiments

The live ledger's typed outcomes help identify where advice failed. They are observational, caller-reported records, not randomized evidence. Receipt metrics do not imply savings, and unknown outcomes are not successes. `evaluate` is a separate offline report comparison; it does not modify the ledger or turn self-reports into certification.
