# Jev Reflex: portable decision support for agents

The public product is an independently usable Python distribution exposing one shared service through stdio MCP, JSON CLI, and Python imports. Host agents keep reasoning, permissions, tools and effects. Jev supplies small typed advisory judgments. This project is independent of TypeSafe.

## Release boundary

Retain the existing tested accounting core, package it without private history, credentials, machine paths or host policy, and add useful coding workflows. Reuse and idempotency include source snapshot, recipe, complete input, provider/model and thresholds. A request never silently retries. All inputs in a batch share one disclosure boundary. Unknown billing stays conservatively accounted. Every returned decision explicitly has no execution authority.

Initial workflows: reversible context triage, eligible-model routing advice, evidence gap triage, risk flags, eligible-tool advice, failure investigation triage, and change-impact triage. No automatic execution, model switching, completion certification, score-based ranking, context deletion or ambient repository upload. A failed or abstaining reflex returns control to the host.

## Interfaces and state

- `jev-reflex serve`: stdio MCP, using the official Python MCP SDK.
- `jev-reflex call METHOD`: bounded JSON from stdin to the same service.
- `jev-reflex demo`: synthetic provider, temporary ledger, no key or network.
- `jev-reflex init --daily-usd N --enable`: explicit host configuration; never overwrites existing policy or resets accounting. Not exposed over MCP.
- `jev-reflex config CLIENT`: prints configuration; does not modify client settings or embed credentials.
- `jev-reflex doctor`: secret-free readiness report.
- Python `Service` and a strict operation dispatcher enable host-specific function calling.

Public state has a distinct default directory, selectable with `JEV_REFLEX_HOME`; no reuse of the private installed plugin's ledger. Provider keys come from process environment only. Source collectors, if added, must be explicit local operations and must never transmit automatically.

## Acceptance

Legacy offline behavior remains green after packaging. Add meaningful CLI/install/MCP round trips, all-recipe abstention and eligibility controls, fake-provider demo, secret/output-leak checks, and source/hash-bound evaluation validation. Build/install an actual wheel in an isolated environment and invoke from outside the checkout. Independent review must inspect runtime and publication surface. A small public synthetic live smoke may qualify the provider wire only under an existing spending authorization; never claim benchmark superiority from it.

## Claims

Universal means interoperable surfaces, not automatic support for every agent. DeepSeek is a model that can be hosted by a tool-capable harness. Document executed, contract-tested, and documentation-only adapters separately. Probabilities are not calibrated correctness guarantees. A local ledger is not provider-enforced billing, tenant isolation or rollback protection. Publish honest product strengths and measured limits, not a claim to be the best without a matched evaluation.
