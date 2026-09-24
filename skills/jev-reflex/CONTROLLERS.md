# Stateful reflex controllers (v1)

An agent can keep an investigation direction across a changing evidence stream.
Controllers consume **settled raw batch/shared results in the local ledger**;
they do not accept caller-supplied probabilities, launch inference, or run tools.
Use a separate controller for each question/signal. Choice routes and Noul
signals share the same mechanism (`true` and `false` are the Noul option IDs).

## Contract and design

- `controller_open` binds project, task, privacy namespace, controller ID,
  initial snapshot, exact semantic question/candidate descriptions and immutable policy. An exact repeat
  reads the current state; changing the contract under that ID is refused.
- `controller_event` accepts a unique event ID and an exact expected revision.
  `bind` announces a **new, never previously bound snapshot** before inference.
  `observe` references one existing raw `batch` or `shared` request and item.
  Shared receipts must belong to the same privacy namespace. Raw batch receipts
  are project/task scoped; their namespace is caller-owned, not authenticated.
- Only a proposal already accepted by the existing Jev validator can vote.
  One source snapshot supplies at most one vote, irrespective of request IDs.
  First accepted evidence selects a hint. A different hint needs consecutive
  accepted votes from distinct snapshots (default 2). Abstention breaks the
  challenger streak. It never becomes a low-confidence vote.
- A held hint names its supporting snapshot, distinct from the current snapshot.
  `supporting_evidence` identifies its supporting receipt; `last_evidence` may
  describe a newer abstention. `confirmation_evidence` retains the bounded
  sequence (at most 8) that selected/switched it; challengers retain their votes.
  After more than `max_hold_sources` source advances without supporting evidence
  it disappears. This is a **source-step bound, not a wall-clock freshness claim**.
  The host must still establish that its current snapshot describes reality.
- `override` is an explicit caller correction, never a provider result. It lasts
  through at most `override_sources` subsequent source advances, or until
  `release`, pause or stop. `release` clears it and the previous interpretation.
- `pause` and permanent `stop` bypass revision comparison so an in-flight
  observation cannot prevent them. Both immediately clear hints and challengers.
  `resume` needs the current revision and starts empty; stop cannot resume.
  Pause invalidates the current source even if no result has landed yet.
  Resume/release never reopen an already used source vote: `awaiting-new-snapshot`
  means bind a genuinely new source, not call Jev again on the same one.
  These control only this advisory stream, not a provider request or host process.
- Events are transactional. Exact event replay returns **current** state with
  `replayed: true`, never a historical hint. Conflicting reuse is refused.
  Revision conflicts, foreign receipts, stale snapshots and malformed fields
  mutate nothing. Stop/pause still require a valid, unique event envelope.

Default policy: `confirmations: 2`, `max_hold_sources: 2`, `override_sources: 4`.
Bounds: confirmations 1–8; hold sources 0–32; override sources 0–32. These
controls add temporal filtering; they never lower provider acceptance thresholds.
No Score support. No automatic model switching, safety approval or task completion.

Question and candidate descriptions are hashed into each new result. Receipts from
a different question or older versions lacking those hashes refuse. Raw question
text is not stored by the controller. Snapshot IDs still describe caller-asserted
source identity; the controller does not read the source to authenticate it.

## JSON API (also `jev-reflex call METHOD`)

Open with:

```json
{"project":"demo","task":"investigate","privacy_namespace":"public","controller_id":"direction","snapshot_id":"source-1","signal":{"primitive":"choice","question":"Where should we investigate?","choices":{"code":"Code","fixture":"Test fixture","environment":"Environment"}},"policy":{"confirmations":2,"max_hold_sources":2,"override_sources":4}}
```

All subsequent calls repeat project/task/privacy_namespace/controller_id.
`controller_inspect` needs only those four keys. Events additionally supply
`event_id`, `expected_revision` (an integer, including for pause/stop), and `event`:

| event | Exact additional fields inside `event` |
| --- | --- |
| `{"kind":"bind", ...}` | `snapshot_id` |
| `{"kind":"observe", ...}` | `receipt: {kind: "batch" or "shared", request_id, item_id}` |
| `{"kind":"override", ...}` | `selected_id` |
| `{"kind":"release"}` | none |
| `{"kind":"pause"}` | none |
| `{"kind":"resume"}` | none |
| `{"kind":"stop"}` | none |

Example after opening and running a raw batch on source-1:

```json
{"project":"demo","task":"investigate","privacy_namespace":"public","controller_id":"direction","event_id":"e1","expected_revision":0,"event":{"kind":"observe","receipt":{"kind":"batch","request_id":"classify-1","item_id":"route"}}}
```

Use `bind` before the next source's inference. A late result from the previous
source refuses, even if it is very confident. `inspect` is a read of historical
advice; it neither rereads source files nor verifies the source against the world.
For unrelated goals/vocabularies use another controller ID, not a continuation.

The local ledger, host and source labels are trusted. This is not authenticated
multi-tenant storage or independent testimony. IDs must be opaque. Stored state
  contains IDs, hashes, decisions and receipt provenance, not source text. Event
and snapshot hashes are retained for replay/ABA protection; storage grows with
accepted events. Only one current vote and challenger are kept, not input bodies.

## Completion and evaluation

Run `jev-reflex controller-demo` for a fully offline, real-ledger walkthrough.
On its designed seven-observation trace, stateless selection changes five times;
the two-confirmation controller changes once and accepts a sustained change one
observation later. It also applies a manual correction and clears it on stop.
Both paths see identical synthetic proposals. This is a mechanism demonstration.

Ship Python/JSON CLI, stdio MCP and pi bridge integration plus an offline demo.
Test restart, competing writers, late evidence, replay, source-name reuse,
abstention, manual corrections, pause/resume/stop and privacy. Compare identical
synthetic streams with stateless selection and report both reduced switching
and the deliberate delay on a genuine change. Synthetic traces prove mechanics,
not real-agent productivity. No additional paid experiment is part of this release.

Inspiration: source review of [Shapeshift](https://github.com/anishfn/shapeshift/tree/5e24166dcbde6e794f0bd5b1b4bd395aaee5fc19),
especially its stateful UI selection and independent signals. This implementation
uses local recorded evidence and stricter source/revision binding; its thresholds
and no-execution contract are Jev Reflex's own. No Shapeshift source is vendored.
