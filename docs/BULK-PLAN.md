# v0.4 refinement contract

Replace the inherited eight-question ceiling, without changing who owns actions.

1. Native item batches and a new shared-state API use owner-configured question
   counts plus serialized UTF-8 size limits. Default 256 questions, 60,000 request
   bytes, 30,000 state-plus-largest-question bytes. These are conservative packing
   heuristics, not an exact provider tokenizer. Keep per-item text limits.
2. Bulk jobs accept up to 10,000 explicit items (16 MiB JSON). Validate the entire
   job before any inference, then partition deterministically without truncation.
   Support raw items, shared-state questions and one versioned recipe per job.
3. Bind job identity to complete inputs, snapshot, provider and packing plan.
   Persist hashes, opaque IDs and progress, never source packets. Resume requires
   the identical input. Replay settled children and never redispatch uncertain
   children. Caller-changed plans conflict instead of spending twice.
4. Workers have bounded concurrency, shared-ledger rate admission and atomic
   spend reservations. A bounded run returns progress on backpressure rather than
   sleeping indefinitely or retrying paid requests. Cancellation atomically
   prevents new admission; already admitted requests may settle.
5. Expose shared/bulk/inspect/cancel through Python, CLI, stdio MCP and pi. Keep
   client payload, response and timeout limits consistent. No new admin MCP tool.
6. Add an offline shadow-evaluation report for caller-labelled decisions:
   confusion matrix, per-class precision/recall, abstention and confidence bins.
   Do not auto-calibrate thresholds or claim measured live improvements.
7. Document speculative independent questions versus true dependent stages,
   deterministic composition, re-observation and explicit eligible candidates.

Acceptance: >8 native questions, 1,000-item job, one-copy shared state, all-input
validation, deterministic packing, concurrent duplicate jobs, restart replay,
cancel/admission interleaving, aggregate budget/rate limits, uncertainty and no
raw persistence. Exercise actual MCP and installed-package boundaries with fake
providers. Preserve the absence of paid/provider quality evidence.
