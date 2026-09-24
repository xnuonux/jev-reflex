# Shared context, native batches and bulk jobs

These APIs provide advisory judgments. They do not execute tools, certify
completion, or change the host's model. v0.4 replaces the inherited eight-question
cap across the Python, CLI, MCP and pi boundaries.

## Choose the request shape

- `batch`: independent items with `id`, `primitive`, `text`, `question`, and
  `choices` for Choice. Each question targets its item's text.
- `shared`: `state` (string, object or array) and `questions` with `id`,
  `primitive`, `question` and optional Choice `choices`. State appears once.
- `recipe`: independent items conforming to one versioned recipe.
- `bulk`: a larger job of any one of those three shapes, partitioned automatically.

All questions see the provider's shared state. `privacy_namespace` is a caller
assertion and local accounting label, not authentication or data isolation.
Shared questions have no separate namespace: the caller must ensure that all
questions and state belong together. Recipes also check each item's namespace.
Neither check can authenticate where source text came from.

`shared` requires `independent_questions:true`. `bulk` requires
`independent_items:true`. A question depending on another answer belongs in a
later request. There is no implied DAG executor or hidden follow-up inference.

For speculative questions, consider the helpdesk example: category, reproduction
steps, and refund intent can all inspect the original ticket independently.
Host code can ignore the refund result when it is irrelevant. A later question
that actually uses a returned category needs a new explicit state and operation
ID. On an abstention, take the host reasoning path. After an external action,
re-observe the world and bind a new snapshot; don't reuse a pre-action judgment as
proof of success. See [shared.json](../examples/shared.json).

## Bulk example (Python)

```python
from jev_reflex import Service

service = Service()
job = dict(
    project="widget", task="triage", request_id="job-001",
    snapshot_id="source-revision-1", privacy_namespace="widget-public",
    independent_items=True,
    items=[dict(id=f"log-{i}", primitive="noul", text=excerpt,
                question="Does this excerpt discuss a compiler failure?")
           for i, excerpt in enumerate(selected_excerpts)],
)
progress = service.bulk(**job)
# Schedule a continuation only when next_step is continue-same-input and
# run_refusals/budget/rate evidence allow it. Do not busy-loop.
page = service.inspect_job("widget", "triage", "job-001", "widget-public")
```

The CLI accepts the same JSON with `jev-reflex call bulk`. For shared-state bulk,
set `shared_state` and supply question-only `items`. For recipe bulk, set `recipe`
and use that recipe's item schema; it does not enable distinct-ID success reuse.
`shared_state` and `recipe` are mutually exclusive. The complete job is at most
10,000 items and 16 MiB JSON (CLI envelope included). A single item that cannot fit
is rejected rather than split semantically or truncated. Every child is validated
before the first provider call.

## Lifecycle and results

Job identity binds project/task/namespace/request ID. The durable job digest binds
the complete input, ordered packing plan, snapshot, provider and thresholds.
Changed source, order, packing settings or model under that ID refuses. Execution
pace (`max_batches` or concurrency/rate configuration) may change without changing
the job identity. Native settled calls remain replayable under tighter capacity;
bulk plans remain fixed because repartitioning could otherwise duplicate work.

Each foreground call can attempt at most `max_batches` (default 32, maximum 256).
It starts work for at most two seconds, with at most the host's configured number
of workers. Already admitted provider calls retain their 20-second transport
deadline and settle before the call returns. This is not a background service or
a hard end-to-end latency guarantee: preflight and local storage work take time.

| `next_step` | Host response |
| --- | --- |
| `continue-same-input` | More work is undispatched. Review `run_refusals`; resume later with identical complete input and ID. |
| `inspect` | At least one child is pending. It may be active or crashed; read progress without inference and preserve accounting. |
| `review-failures` | A paid child failed or is uncertain. No automatic retry or further job dispatch; investigate or use the main agent. |
| `done` | All child responses structurally validated. Individual judgments may still abstain or be wrong. |
| `stop` | Job cancelled. Already admitted calls may have completed. |

`inspect_job` returns 100 item rows by default (maximum 256 per page). Follow
`next_offset` to read the rest. `batch_counts` and `total_items` cover the whole
job, while `items` covers only this page. Results retain full bounded distributions.
`accounted_microusd` is cumulative, not the incremental cost of inspecting.

Cancellation is durable by stable job identity, including during preflight or
before registration. It creates a tombstone, preventing a later registration of
that ID from dispatching. It never refunds or recalls an admitted provider call.
A cancelled job cannot be revived by resubmitting the same ID.

MCP request cancellation/disconnection is different from job cancellation. The
MCP bulk handler runs a bounded worker thread so another `cancel_job` request can
be served while inference waits. Cancelling that handler alone does not terminate
the worker or create a cancellation record; it may still admit work during its
start window. Call `cancel_job` and inspect its result before disconnecting when
you need durable cancellation. No cancelled transport response proves that a
provider request did not happen.

Only hashes, opaque IDs, accepted outputs and progress are persisted. The caller
must keep the original input for continuation. Reopening alone does not resume
work. A process death can leave a child pending indefinitely; inspect is not
evidence that the provider was cancelled, and there is no automatic redispatch.

## Host capacity

An optional owner-edited `capacity.json` in `JEV_REFLEX_HOME` accepts partial
overrides and fixed-route overrides:

```json
{
  "max_questions": 256,
  "max_request_bytes": 60000,
  "max_state_question_bytes": 30000,
  "max_concurrency": 4,
  "requests_per_minute": 1200,
  "request_bytes_per_second": 200000,
  "routes": {"openrouter": {"requests_per_minute": 60}}
}
```

The example's OpenRouter rate is an illustrative host choice, not a published
provider entitlement. Native count is configurable from 1 to 4,096; concurrency
from 1 to 32. Byte caps can only be lowered. Provider routes have separate rate
windows but share the daily spending ledger. Host byte-rate admission is a
conservative local rule, not the provider's token meter. The provider can reject a
packet or rate even when the local check passes. Check actual account limits.

Admission, cancellation checks, child ownership and spend reservation share one
SQLite transaction. Rate or budget refusals consume nothing. A transport error
retains its reservation and is never automatically retried. Older pre-v0.4
workers do not obey the new admission table; stop them before relying on these
limits. Different state directories, machines or external provider calls are
outside this local control.

## What the article contributed

The design adopts independent shared-context questions, deterministic composition,
explicit candidates, a no-call path, and measured quality separate from confidence.
See [research](RESEARCH.md) for attribution and limitations, and
[evaluation](EVALUATION.md) for the offline shadow report.
