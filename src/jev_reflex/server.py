"""Portable stdio MCP. No admin tools and no network listener."""
from typing import Literal
import asyncio
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field
from .reflex import Service


class ChoiceItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str = Field(description='Opaque item ID; do not put private text in IDs.')
    primitive: Literal['choice']
    text: str = Field(description='Only the selected non-secret text needed for this judgment.')
    question: str = Field(description='One atomic semantic question, not authority or verification.')
    choices: dict[str, str] = Field(description='2–255 opaque option IDs mapped to short descriptions; request size still applies.')


class NoulItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    primitive: Literal['noul']
    text: str
    question: str = Field(description='One semantic yes/no question; not factual certification.')


class SharedChoice(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    primitive: Literal['choice']
    question: str
    choices: dict[str, str]


class SharedNoul(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    primitive: Literal['noul']
    question: str


RecipeVersion = Literal['context_triage/v1', 'routing_advice/v1', 'evidence_gap/v1', 'risk_flag/v1',
                        'tool_advice/v1', 'failure_triage/v1', 'change_impact/v1']


class ContextRecipeItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    privacy_namespace: str
    text: str = Field(description='A small, caller-selected context excerpt; no secrets.')
    goal: str
    mandatory_pinned: bool = Field(description='True for required evidence that must remain visible and intact.')


class EligibleModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    option_id: str
    model_id: str
    description: str = Field(description='Caller-supplied known capability and suitability; no inferred roster.')


class RoutingRecipeItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    privacy_namespace: str
    text: str = Field(description='Small task packet for advisory model routing.')
    current_option_id: str
    eligible_models: list[EligibleModel]


class EvidenceGapRecipeItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    privacy_namespace: str
    text: str = Field(description='Caller-selected evidence packet, not a certification record.')
    claim: str


class RiskFlagRecipeItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    privacy_namespace: str
    text: str
    risk: str = Field(description='Specific risk to look for; a negative flag grants no permission.')


class OutcomeV1(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    outcome_version: Literal['v1']
    missed_important_item: bool | None = None
    routing_rework: bool | None = None
    later_assessment: Literal['agree', 'disagree', 'abstained'] | None = None
    measurement_unit_id: str | None = Field(
        default=None, description='Unique opaque downstream work ID required for any numeric measurement; report each shared run once.')
    end_to_end_duration_ms: float | None = None
    downstream_input_tokens: int | None = None
    downstream_output_tokens: int | None = None
    downstream_cached_input_tokens: int | None = None
    downstream_cache_hit_count: int | None = None


class EligibleTool(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    option_id: str
    description: str


class ToolRecipeItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    privacy_namespace: str
    text: str
    goal: str
    eligible_tools: list[EligibleTool]


class FailureRecipeItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    privacy_namespace: str
    text: str
    expected: str


class ImpactRecipeItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    privacy_namespace: str
    text: str
    goal: str


class SourceChunk(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    text: str
    source_ref: str
    mandatory_pinned: bool


def make_server(service=None):
    service = service or Service()
    server = FastMCP('Jev Reflex', instructions=(
        'Jev is an advisory S1 helper; The host agent keeps reasoning and the user directs priorities. '
        'Batch bounded semantic triage when it saves work. Never use judgments as authority, '
        'test verification, arithmetic, or proof of truth. Send only necessary selected text. '
        'On abstain/unavailable continue reasoning yourself; no polling or retry loop. '
        'Recipes are opt-in and never change a model, delete context, or certify completion.'))

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
    def jev_reflex_workflow(project: str, task: str, request_id: str, privacy_namespace: str,
                           workflow: str, packet: dict) -> dict:
        """Run a versioned workflow on explicit selected evidence. See WORKFLOWS.md.

        progress_watch/v1 {goal,steps:[{action,observation,evidence_ref}]};
        skill_shortlist/v1 {goal,candidates:[{id,description,instructions,revision}]};
        swarm_inbox/v1 {goal,reports:[{id,status,summary,source_ref}]};
        patch_review/v1 {goal,diff,requirements,checks}; handoff_check/v1 {original,handoff};
        memory_conflict/v1 {existing,incoming}; decision_pack/v1 {state,operations:
        [{id,description,candidates:[{id,description}]}]}. No source collection or actions.
        Skill selection uses up to TWO dependent calls, all others zero or one shared call.
        Stable request_id binds the complete input; no retries under new IDs. Unavailable
        or uncertain means use host reasoning. Reports and memory are never discarded.
        """
        from .workflows import run
        return run(service,project,task,request_id,privacy_namespace,workflow,packet)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
    def jev_reflex_host_event(project: str, task: str, request_id: str, privacy_namespace: str,
                             event: str, packet: dict) -> dict:
        """Explicit host event adapter; not an automatic Codex interceptor.

        after_tool=>progress_watch, skill_selection=>skill_shortlist, child_report=>swarm_inbox,
        source_changed=>patch_review, before_handoff=>handoff_check, memory_proposal=>memory_conflict,
        before_tool=>decision_pack. Packets use the corresponding workflow schema. Only
        caller-selected authorized text is sent. A report status is caller supplied.
        """
        from .workflows import host_event
        return host_event(service,project,task,request_id,privacy_namespace,event,packet)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
    def jev_reflex_artifact_put(project: str, privacy_namespace: str, content: str) -> dict:
        """Explicitly save <=1MiB supplied text locally in plaintext by content hash.

        Zero provider calls. Unlike inference receipts this intentionally retains raw text.
        No arbitrary path, file scan, deletion or automatic upload. Avoid credentials.
        Namespace labels are accounting boundaries, not hostile-user authentication.
        """
        from .artifacts import put
        return put(service,project,privacy_namespace,content)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    def jev_reflex_artifact_get(project: str, privacy_namespace: str, artifact_id: str,
                               start: int=0, length: int=6000) -> dict:
        """Retrieve hash-verified local text, at most 16000 Unicode codepoints per call.

        Explicit content returned to the caller, never a provider call. Does not prove
        the original external file is still current. Same project/namespace required.
        """
        from .artifacts import get
        return get(service,project,privacy_namespace,artifact_id,start,length)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
    def jev_reflex_calibration_audit(project: str, privacy_namespace: str, recipe_revision: str,
                                    model: str, split: str, examples: list[dict]) -> dict:
        """Offline caller-labeled evaluation; no inference, training or automatic promotion.

        examples:[{family,text,expected:boolean,probability_true:number}]. Stable family
        hashing selects tune/holdout; repeated cross-revision holdout use is marked.
        Reports abstentions, Brier and accepted accuracy, not general calibration proof.
        Stores hashes and exposure only. Labels/predictions remain caller assertions.
        """
        from .calibration import audit
        return audit(service,project,privacy_namespace,recipe_revision,model,split,examples)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
    def jev_reflex_controller_open(project: str, task: str, privacy_namespace: str,
                                   controller_id: str, snapshot_id: str,
                                   signal: dict,
                                   policy: dict | None = None) -> dict:
        """Create a durable advisory stream; zero inference, permissions or actions.

        Policy defaults: confirmations=2, max_hold_sources=2, override_sources=4.
        signal is {primitive:'choice',question,choices:{id:description}} or
        {primitive:'noul',question}. Exact question and descriptions are bound. Use one
        controller for one stable semantic question. Exact open replay reads current
        state. Bind source changes before inference. See docs/CONTROLLERS.md.
        """
        from .controllers import open_controller
        return open_controller(service, project, task, privacy_namespace, controller_id,
                               snapshot_id, signal, policy)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
    def jev_reflex_controller_event(project: str, task: str, privacy_namespace: str,
                                    controller_id: str, event_id: str,
                                    expected_revision: int, event: dict) -> dict:
        """Advance a controller using recorded evidence or explicit caller controls.

        event exact shapes: {kind:'bind',snapshot_id}; {kind:'observe',receipt:
        {kind:'batch'|'shared',request_id,item_id}}; {kind:'override',selected_id};
        {kind:'release'|'pause'|'resume'|'stop'}. Never accepts probabilities.
        Revisions serialize updates. Pause/stop bypass revision conflict and clear
        hints immediately on commit. Stop is permanent; resume needs fresh revision.
        One vote per source snapshot; stale results and source-name reuse refuse.
        An override is caller input, not authenticated human approval. No inference.
        """
        from .controllers import event as advance
        return advance(service, project, task, privacy_namespace, controller_id,
                       event_id, expected_revision, event)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    def jev_reflex_controller_inspect(project: str, task: str, privacy_namespace: str,
                                      controller_id: str) -> dict:
        """Read current advisory stream; does not inspect files or prove freshness.

        supported_snapshot may be older than snapshot_id. Always recheck relevance.
        Paused/stopped streams have no hint. No model call or execution authority.
        """
        from .controllers import inspect
        return inspect(service, project, task, privacy_namespace, controller_id)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    def jev_reflex_status() -> dict:
        """Read shared UTC daily budget, credential availability and model pin. No inference or secret values."""
        return service.status()

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
    def jev_reflex_context(project: str, task: str, request_id: str, privacy_namespace: str,
                           goal: str, chunks: list[SourceChunk], reuse_success: bool = False) -> dict:
        """Suggest reversible context visibility within the host's native batch capacity.

        Hashes exact supplied text, pointers and goal into a source snapshot. Required
        pins and uncertain/unavailable results stay visible. Never scans, reads or
        deletes files. The caller must preserve source bytes and independently check
        source currency. Source pointers stay local; selected text reaches Jev.
        """
        from .context import plan
        return plan(service, project, task, request_id, privacy_namespace, goal,
                    [c.model_dump() for c in chunks], reuse_success)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
    def jev_reflex_batch(project: str, task: str, request_id: str, snapshot_id: str,
                         items: list[ChoiceItem | NoulItem]) -> dict:
        """Ask independent semantic questions in one native batch, default up to 256.

        Use for relevance, triage, candidate selection or semantic routing; never permissions,
        budgets, exact computations, execution decisions or declaring tests/tasks passed.
        project/task are opaque stable accounting labels, NOT authentication. request_id must
        be stable for one attempt: retrying the same ID never redispatches. snapshot_id binds
        the input version; YOU must recheck current relevance before acting on an advisory.
        Use choice with 2–255 options or noul. Size limits can bind before count limits.
        For larger jobs use bulk; for one context with many questions use shared. No Score.
        No auto-reading of files or chat; only item.text and question/choices reach the provider.
        A valid answer can abstain. On unavailable/paced/busy/budget-exhausted, continue with
        the host agent; do not loop or mint a new ID just to retry. No execution authority is returned.
        """
        return service.judge(project, task, request_id, snapshot_id,
                             [item.model_dump() for item in items])

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
    def jev_reflex_recipe(project: str, task: str, request_id: str, snapshot_id: str,
                          privacy_namespace: str, recipe: RecipeVersion,
                          items: list[ContextRecipeItem | RoutingRecipeItem | EvidenceGapRecipeItem | RiskFlagRecipeItem | ToolRecipeItem | FailureRecipeItem | ImpactRecipeItem],
                          independent_items: bool, reuse_success: bool = False) -> dict:
        """Run independent items of one versioned recipe within host batch capacity.

        All items must repeat the same privacy namespace. A dependent question belongs in
        a later request. Text and descriptions go only to the pinned Jev provider when
        admitted. Exact success reuse is opt-in; it keeps snapshot/version binding and
        emits a new receipt with zero inference. The caller must revalidate the source.
        No action, model switch, context deletion or completion certification occurs.
        """
        return service.recipe(project, task, request_id, snapshot_id,
                              privacy_namespace, recipe,
                              [item.model_dump() for item in items],
                              independent_items, reuse_success)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
    def jev_reflex_shared(project: str, task: str, request_id: str, snapshot_id: str,
                          privacy_namespace: str, state: str | dict | list,
                          questions: list[SharedChoice | SharedNoul], independent_questions: bool) -> dict:
        """Send shared state ONCE with many independent questions in one paid request.

        Every question sees the same state; use a single confidentiality boundary.
        Questions cannot read one another's answers. Actual dependencies need a later
        request with fresh explicit state. Defaults: 256 questions, 60k request bytes,
        30k state plus largest question bytes. Byte guards are not exact token counts.
        No execution authority. Preserve request_id on replay or uncertain outcomes.
        """
        return service.shared(project,task,request_id,snapshot_id,privacy_namespace,state,
                              [q.model_dump() for q in questions],independent_questions)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
    async def jev_reflex_bulk(project: str, task: str, request_id: str, snapshot_id: str,
                        privacy_namespace: str, items: list[dict], independent_items: bool,
                        shared_state: str | dict | list | None = None,
                        recipe: RecipeVersion | None = None, max_batches: int = 32) -> dict:
        """Advance a job of up to 10,000 explicit items with automatic size-based packing.

        Raw items use batch schemas; with shared_state, use shared question schemas;
        with recipe, use that recipe's schema. Whole job validates before any inference.
        Runs in the foreground with a bounded start window and host-owned concurrency.
        Read next_step and progress; continue-same-input means resubmit IDENTICAL input
        and request_id later. Never spin or change IDs to retry a failed paid child.
        Only hashes, IDs, results and progress persist. Results are paginated (inspect_job).
        No file collection or execution. cancel_job stops new admission, not issued calls.
        Cancelling this MCP request alone does not cancel the durable job: its bounded
        worker may still settle or admit work. Use cancel_job and inspect before disconnecting.
        """
        return await asyncio.to_thread(service.bulk,project,task,request_id,snapshot_id,privacy_namespace,items,
                                       independent_items,shared_state,recipe,max_batches)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    def jev_reflex_inspect_job(project: str, task: str, request_id: str,
                               privacy_namespace: str, offset: int = 0, limit: int = 100) -> dict:
        """Read durable bulk progress and up to 256 item results; zero provider calls.

        Pending can mean an active or crashed request. Never redispatch it blindly.
        Follow next_offset to read all results; status ok is not semantic certification.
        """
        return service.inspect_job(project,task,request_id,privacy_namespace,offset,limit)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
    def jev_reflex_cancel_job(project: str, task: str, request_id: str, privacy_namespace: str) -> dict:
        """Persist cancellation of an existing bulk job. No new provider call or refund.

        Requests admitted before cancellation may still finish and be accounted.
        An already admitted provider call cannot be recalled by cancelling this job.
        """
        return service.cancel_job(project,task,request_id,privacy_namespace)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
    def jev_reflex_record_outcome(project: str, task: str, privacy_namespace: str,
                                   receipt_id: str, item_id: str, outcome: OutcomeV1) -> dict:
        """Store one typed caller-reported outcome for an actual successful recipe receipt/item.

        No free text, automatic learning or threshold changes. An exact repeat is
        idempotent; a conflicting report for the same receipt/item is refused.
        """
        return service.record_outcome(project, task, privacy_namespace,
                                      receipt_id, item_id,
                                      outcome.model_dump(exclude_unset=True))

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    def jev_reflex_recipe_metrics(project: str, task: str, privacy_namespace: str,
                                   recipe: RecipeVersion | None = None) -> dict:
        """Summarize local recipe receipts and typed caller reports; unknown stays unknown.

        A descriptive report, not measured quality or cost improvement.
        """
        return service.recipe_metrics(project, task, privacy_namespace, recipe)
    return server


if __name__ == '__main__':
    make_server().run(transport='stdio')
