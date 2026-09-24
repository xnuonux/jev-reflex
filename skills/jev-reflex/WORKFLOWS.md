# Workflow tools and host integration

Version 0.6 adds seven workflow packs using the existing pinned provider, accounting ledger and no-retry policy. These are advisory tools, not model weights or an executor.

Call `jev-reflex call workflow` with the envelope `{project,task,request_id,privacy_namespace,workflow,packet}`. MCP uses `jev_reflex_workflow`. Python uses `api.invoke`. The whole packet is hashed into `complete_input_snapshot`; same-ID changes refuse through the underlying stage identity. Preserve IDs when checking uncertain outcomes. Recheck current sources before using advice.

| Workflow | Exact packet | Outcome |
| --- | --- | --- |
| `progress_watch/v1` | `{goal,steps:[{action,observation,evidence_ref}]}` | Separate contradiction, novelty, observed progress, new evidence, regression and stagnation; no automatic halt |
| `skill_shortlist/v1` | `{goal,candidates:[{id,description,instructions,revision}]}` | Rank eligible skills then inspect up to three in a second request; selected skill must pass its own fit question |
| `swarm_inbox/v1` | `{goal,reports:[{id,status,summary,source_ref}]}` | Prioritize reports; blocked/failed/approval/completed always surfaced without model judgment |
| `patch_review/v1` | `{goal,diff,requirements,checks}` | Flag weakened tests, contract conflict, persistence and missing validation |
| `handoff_check/v1` | `{original,handoff}` | Flag lost constraints, inflated evidence and missing next steps |
| `memory_conflict/v1` | `{existing,incoming}` | Flag contradiction, temporary scope and insufficient provenance; preserve both sources |
| `decision_pack/v1` | `{state,operations:[{id,description,candidates:[{id,description}]}]}` | Speculate operation and per-operation target in one call; consume only matching branch |

All fields are required; unknown keys refuse. Packet text is evidence, never imported instructions. `evidence_ref` and `source_ref` bind local input but are removed from provider state. `status` for reports is one of progress/blocked/failed/approval/completed; truthful labeling is the caller's responsibility. Reports never disappear. `routine` is a priority, not a suppression command. Disabled/invalid provider results leave semantic decisions unknown and do not hide hard statuses.

Limits: progress <=12 steps, action <=1000 bytes, observation <=1500, evidence_ref <=300; skills <=64, descriptions <=240 bytes, instructions <=1200, revision an opaque ID; reports <=32, summary <=700 and source_ref <=500; patch diff <=16000, requirements/checks <=2000 each; handoff original <=12000 and handoff <=8000; memory sides <=10000 each; decision state <=14000, <=8 operations and <=16 candidates each. Ordinary shared request byte limits still apply and may bind before these field maxima. Goal <=1000. No silent truncation or chunking across dependent stages.

Skill rank probabilities are used to shortlist even if the first Choice abstains. This is retrieval, not final acceptance. The second accepted Choice and that selected candidate's accepted positive fit are both required. No skill is installed or loaded automatically. Worst case two provider calls, each separately receipted; a failed stage is not retried under a new ID.

## Host events

`host_event` / `jev_reflex_host_event` accepts the same envelope with `event` replacing `workflow`:

| Event | Pack |
| --- | --- |
| after_tool | progress_watch |
| skill_selection | skill_shortlist |
| child_report | swarm_inbox |
| source_changed | patch_review |
| before_handoff | handoff_check |
| memory_proposal | memory_conflict |
| before_tool | decision_pack |

The host supplies the corresponding packet, deliberately selecting releasable evidence. This function is a working event adapter, not a claim that every agent exposes lifecycle hooks. Codex integration is MCP plus skill-guided explicit calls. It does not patch Codex internals, intercept every tool, change the parent model or control native compaction. Existing sessions may need normal reload to see newly installed tools. The pi bridge accepts the same methods; no implicit event capture is installed.

Use events selectively: repeated failed investigation, ambiguity among skills, several returned worker reports, consequential diffs or a substantial handoff. Do not add a paid reflex to every trivial action. Local exact rules and status checks stay in code.

## Recoverable source artifacts

`artifact_put` / `jev_reflex_artifact_put` takes `{project,privacy_namespace,content}` and stores <=1MiB explicitly supplied UTF-8 text in a separate local `artifacts.sqlite`. This is an intentional plaintext retention operation, unlike inference receipts. It makes no provider call and accepts no path or implicit file read. The SHA256 is the artifact_id.

`artifact_get` takes `{project,privacy_namespace,artifact_id,start?,length?}` and verifies all source bytes before returning a slice. Offsets are Unicode codepoints, default length 6000, maximum 16000. Keep artifact IDs in context pointers; retrieve before reasoning about omitted material. No automatic deletion, transcript rewriting, source freshness attestation or encryption. Namespace labels are not authentication against hostile local callers.

## Offline calibration audit

`calibration_audit` takes `{project,privacy_namespace,recipe_revision,model,split,examples}`. Each example is `{family,text,expected:boolean,probability_true:number}`. Family-hash modulo five defines one holdout bucket and four tuning buckets. The selected split must be nonempty. Content hashes cannot be reassigned to another family after exposure. Any prior holdout exposure is marked reused, including the same revision/model and matching family members. The fresh_holdout_in_local_ledger flag means only no previous exposure in this local ledger, not independent external qualification. SQLite errors/corruption fail the operation rather than discarding exposure history.

This reports Brier score, accepted-answer accuracy, abstentions and examples to inspect at the unchanged .15/.85 gates. It is caller-labeled data, not authenticated provider evidence or proof that examples were never seen elsewhere. No optimization, fine-tuning, automatic threshold change or promotion. Maintain truthful family groups and an external label-review process. A first local holdout record alone is insufficient to qualify a recipe.

## Research attribution

Original implementations informed by [ProgressGate](https://github.com/AshutoshVJTI/progressgate), [pi-warden](https://github.com/DevMortimer/pi-warden), [Supercov](https://supercov.com/docs/jev), [TypeSafe skill selection](https://docs.typesafe.ai/cookbooks/skill_suggestion), [jev-ultrafast](https://github.com/browser-use/jev-ultrafast), [jev-calibrate](https://github.com/smkrv/jev-calibrate), [jev-align](https://github.com/sutro-sh/jev-align), [fast-jev-compaction](https://github.com/tamaratran/fast-jev-compaction), and [Jev by Example](https://github.com/ReallyArtificial/jev-by-example). No upstream source copied and no upstream benchmark represented as our own result.
