"""Portable stdio MCP. No admin tools and no network listener."""
from typing import Literal
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
    choices: dict[str, str] = Field(description='2–16 opaque option IDs mapped to short descriptions.')


class NoulItem(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    primitive: Literal['noul']
    text: str
    question: str = Field(description='One semantic yes/no question; not factual certification.')


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

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False))
    def jev_reflex_status() -> dict:
        """Read shared UTC daily budget, credential availability and model pin. No inference or secret values."""
        return service.status()

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
    def jev_reflex_context(project: str, task: str, request_id: str, privacy_namespace: str,
                           goal: str, chunks: list[SourceChunk], reuse_success: bool = False) -> dict:
        """Suggest reversible context visibility for 1–8 supplied source chunks.

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
        """Ask Jev 1–8 atomic semantic questions in one paid batch (16 KiB wire maximum).

        Use for relevance, triage, candidate selection or semantic routing; never permissions,
        budgets, exact computations, execution decisions or declaring tests/tasks passed.
        project/task are opaque stable accounting labels, NOT authentication. request_id must
        be stable for one attempt: retrying the same ID never redispatches. snapshot_id binds
        the input version; YOU must recheck current relevance before acting on an advisory.
        Use choice with 2–16 named options or noul for a semantic yes/no judgment. No Score.
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
        """Run 1–8 independent items of one versioned advisory recipe.

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
