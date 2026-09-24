# Versioned recipes

`jev-reflex catalog` lists the supported versions. All recipes use this common envelope through CLI `call recipe`, Python `Service.recipe`, or MCP `jev_reflex_recipe`:

```json
{
  "project":"widget", "task":"fix-build", "request_id":"investigate-001",
  "snapshot_id":"build-21", "privacy_namespace":"selected-public-source",
  "recipe":"failure_triage/v1", "independent_items":true, "reuse_success":false,
  "items":[{
    "id":"failure", "privacy_namespace":"selected-public-source",
    "text":"Expected 42, received 41 after applying the patch.",
    "expected":"The update changes the stored value to 42."
  }]
}
```

Every item has exactly `id`, `privacy_namespace`, `text`, plus the fields in the table. No extra fields. All items repeat the envelope namespace. Batch only independent questions within one disclosure boundary.

| Recipe | Additional fields | Interpretation |
| --- | --- | --- |
| `context_triage/v1` | `goal` string; `mandatory_pinned` boolean | `read_now`, `retain_pointer`, `low_relevance`, `uncertain`. Required pins override hiding. Prefer the higher-level `context` method when supplying source pointers. |
| `routing_advice/v1` | `current_option_id`; `eligible_models` array | Each model has `option_id`, `model_id`, `description`. 2–14 eligible models, current ID included. Advice can keep current, suggest another eligible model, or abstain. No switch occurs. |
| `evidence_gap/v1` | `claim` string | `gap_visible`, `coverage_unclear`, `no_gap_visible`, `uncertain`. No completion certificate. |
| `risk_flag/v1` | `risk` string | Noul flag: plausible, not observed in this packet, or uncertain. No permission granted. |
| `tool_advice/v1` | `goal`; `eligible_tools` array | 1–14 `{option_id,description}` objects. Advice can select one, `no_tool`, or `uncertain`. No arguments or call generated. |
| `failure_triage/v1` | `expected` string | Prioritize implementation, test contract, fixture, environment, timing, or uncertain. No verified diagnosis or permission to discard a failing test. |
| `change_impact/v1` | `goal` string | Prioritize interface, persistence, concurrency, presentation, tests, or uncertain. One area is not an exhaustive impact analysis. |

Goal/claim/risk/expected strings are <=1,000 UTF-8 bytes. Model descriptions <=240 and tool descriptions <=300 bytes. IDs use letters, digits, `_`, `.`, `:`, `-`, start alphanumerically, and are <=128 characters; prototype-related reserved names refuse. Eligibility comes from the host. Jev does not discover installed models, tools or prices.

## Raw primitive batch

```json
{
  "project":"widget", "task":"triage", "request_id":"batch-001", "snapshot_id":"source-21",
  "items":[
    {"id":"topic", "primitive":"choice", "text":"Compiler reports a type mismatch.",
     "question":"Which investigation area is suggested?",
     "choices":{"types":"Type compatibility", "network":"Network connection", "uncertain":"Insufficient evidence"}},
    {"id":"relevant", "primitive":"noul", "text":"Compiler reports a type mismatch.",
     "question":"Does this passage discuss a software compilation issue?"}
  ]
}
```

Submit with `jev-reflex call batch`. The two questions share one native request, not two network calls. A returned probability does not establish accuracy or authorize an action.

## Feedback

Use `record_outcome` with `project`, `task`, `privacy_namespace`, `receipt_id`, `item_id` and `outcome`. Start `outcome` with `outcome_version:"v1"` and one or more meaningful observations:

- `missed_important_item`: boolean/null for context only.
- `routing_rework`: boolean/null for routing only.
- `later_assessment`: `agree`, `disagree`, `abstained`, or null. Agreement/disagreement requires an actual proposal.
- `end_to_end_duration_ms`, `downstream_input_tokens`, `downstream_output_tokens`, `downstream_cached_input_tokens`, `downstream_cache_hit_count`: measured numeric values or null. Any numeric report requires an opaque unique `measurement_unit_id`.

Do not report the same shared downstream run on every item. `metrics` accepts `project`, `task`, `privacy_namespace` and optional `recipe`; it reports known and unknown counts. No prose, private excerpts, secrets or invented savings belong in feedback.
