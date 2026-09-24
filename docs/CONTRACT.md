# Decision and accounting contract

## What the result means

Every operational result declares `authority:"none"` and `may_execute:false`. A valid provider envelope produces `status:"ok"`; each item can still be `proposal` or `abstain`. `ok` means structurally accepted response, not correct judgment. Failures produce bounded `unavailable` reasons; malformed caller arguments raise `ReflexError` in Python, become an MCP tool error, or exit 2 with a JSON error in the CLI. The host handles both refusal shapes.

Choice requires exactly the declared option keys, finite probabilities in [0,1], a sum within 1e-5 of one, and the returned choice within 1e-7 of the maximum. A proposal requires probability >= .85, confidence >= .75, and margin >= .25. With probability >= .85 and a normalized distribution, the margin is already >= .70: the current margin test is redundant, **not an independent safeguard**. Thresholds are heuristics, not demonstrated calibration. Noul proposes true at >= .85, false at <= .15, and abstains between. Score is unavailable.

There are 1–8 items per native provider request and a 16 KiB total serialized request limit. Individual recipe text is capped at 6,000 UTF-8 bytes; raw batch text at 12,000. The total limit still applies. Shared state is visible to all questions; per-item prompt separation is not confidentiality isolation. Dependent questions require separate steps.

## Source and identity

`project`, `task`, IDs and privacy namespaces are opaque caller labels, not authentication. A raw batch binds its complete input, caller snapshot, route/model, endpoint and thresholds. A recipe additionally binds its version, namespace, eligibility roster and policy-relevant parameters. Do not put private content into IDs.

`context` computes a snapshot over the supplied text, pointers, goal and pin flags. Each `source_sha256` is SHA-256 of that chunk's UTF-8 text bytes. It does not open the pointer or attest a file's authenticity. The host retains originals and checks current relevance before acting. Required pins and uncertain/unavailable decisions stay visible. No actual token reduction is claimed from a proposed visibility plan.

## Idempotency and reuse are different

A raw dispatched operation is identified by project/task/request ID. Recipe identities additionally include the privacy namespace and a recipe-operation tag. Replay never redispatches it. Changed binding with the same identity refuses. Before dispatch, a disabled/budget-refused request has no paid reservation; it can be reconsidered after a legitimate host change. An uncertain paid attempt must not be given a new ID to bypass the record.

Recipe `reuse_success:true` allows a **settled successful** exact match under a new request ID. Each reuse has a receipt pointing to the original and zero new inference charge. Input/snapshot/recipe/model/threshold changes invalidate it. Reuse is not fuzzy caching. Concurrent distinct-ID requests do not coalesce: if neither has settled, both can dispatch if limits allow. Success includes a valid abstention, not proof of a useful decision. The host still revalidates context.

## Local budget lifecycle

Before any provider request, one SQLite `BEGIN IMMEDIATE` transaction checks policy and atomically reserves **20,000 micro-USD ($0.02)**. Concurrent processes sharing the directory see these reservations. This is a conservative local envelope, not a provider quote.

OpenRouter's reported cost, when present and valid, is rounded **up** to integer micro-USD. Structurally accepted responses can settle downward. Missing or unusable billing leaves conservative accounting. An over-envelope reported cost is retained and stops subsequent dispatch. An implausible/non-numeric/negative/non-finite bill stops dispatch while retaining the reservation, with unknown reported cost; it is never bound as an unbounded SQLite integer. This stop is durable.

Direct TypeSafe's documented response contains token counts, not USD cost. Its calls retain the full reservation and report `reported_microusd:null`. This intentionally exhausts a $2 local cap after 100 such dispatches if no other tighter limit binds. It does not imply TypeSafe billed $2. A tariff-based accounting option would require a separately versioned estimate contract; it is not silently substituted here.

No inference retry occurs on timeout or HTTP error. A process death before settlement can leave a pending reservation; after the uncertainty window it blocks new dispatch instead of silently releasing money. `doctor` exposes pending calls and the accounting stop. Preserve the ledger and reconcile against provider evidence with the host owner. There is no automated refund/reset tool in this release.

## Host configuration

Status's `reported_microusd` sums only known reported bills. It is accompanied by `reported_cost_calls_today`, `unreported_cost_calls_today` and `reported_cost_basis`. A zero known sum with unreported calls is not a verified zero bill.

`init` creates, but never overwrites, `policy.json`. Defaults: disabled, $0/day, 1,000 calls/day and 200 calls per project/task/day. Days are UTC. `--daily-usd` accepts 0–100 with at most six fractional digits. Hosts can edit the policy while preserving the ledger. Legacy owner-only quota overrides and explicit null limits are supported for migration; null means unlimited. New initialization refuses a preexisting override. `doctor` reports effective limits. Model tools cannot change them.

There is no imposed pacing or global in-flight cap beyond quota admission. Provider rate limits still apply. Backpressure and host scheduling remain the caller's job. The fixed transport disables redirects and inherited proxies, caps response bytes and runs under a wall deadline. No arbitrary endpoint argument or silent provider fallback is exposed.

The ledger is neither a provider billing cap nor a security boundary against its owner. Other machines, other state directories, restoring old state, or external provider use are outside this cap. There is no authenticated multi-tenant isolation, remote witness, encryption, or rollback protection.

## Feedback and measurement

Only a successful recipe receipt and an actual item can receive feedback. Typed outcomes are immutable and idempotent; conflicting rewrites refuse. Numeric measurements require a unique `measurement_unit_id` so one shared downstream run cannot be counted repeatedly in the same context. Metrics distinguish missing/unknown values from zero. Feedback is caller-reported, not independently verified. See [evaluation](EVALUATION.md).
