"""Versioned, bounded advisory recipes over the existing Choice/Noul primitives."""

import math
import re

RECIPE_VERSIONS = ('context_triage/v1', 'routing_advice/v1', 'evidence_gap/v1', 'risk_flag/v1',
                   'tool_advice/v1', 'failure_triage/v1', 'change_impact/v1')
THRESHOLD_VERSION = 'choice-085-075-025_noul-015-085/v1'
STORAGE_VERSION = 1
OUTCOME_VERSION = 'v1'
MODEL_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_./:+-]{0,199}$')

CONTEXT_CHOICES = {
    'read_now': 'Needed now to understand the task or next decision.',
    'retain_pointer': 'Can leave the active view if its source pointer stays recoverable.',
    'low_relevance': 'Low relevance to the current task; keep a recoverable source pointer.',
    'uncertain': 'Insufficient basis to reduce visibility; inspect and preserve it.',
}
GAP_CHOICES = {
    'gap_visible': 'The supplied evidence visibly misses a requirement of the claim.',
    'coverage_unclear': 'The supplied evidence may relate, but its coverage is unclear.',
    'no_gap_visible': 'No specific gap is visible in this limited packet.',
    'uncertain': 'Insufficient basis to assess the evidence gap.',
}
FAILURE_CHOICES = {
    'implementation': 'Investigate production implementation against the stated contract.',
    'test_contract': 'Investigate whether the test represents the intended contract.',
    'fixture': 'Investigate fixture data, setup or teardown.',
    'environment': 'Investigate dependency, filesystem, platform or configuration evidence.',
    'timing': 'Investigate scheduling or timing sensitivity; not a declaration of a flake.',
    'uncertain': 'Insufficient supplied evidence; preserve the failure and investigate further.',
}
IMPACT_CHOICES = {
    'interface': 'Inspect caller/API compatibility and validation.',
    'persistence': 'Inspect durable state, migrations and recovery.',
    'concurrency': 'Inspect ownership, ordering and concurrent access.',
    'presentation': 'Inspect rendering and user interaction.',
    'tests': 'Inspect fixture and test coverage implications.',
    'uncertain': 'No supported priority; broader review is still needed.',
}
ALLOWED_OUTCOME_KEYS = {
    'outcome_version', 'missed_important_item', 'routing_rework', 'later_assessment',
    'measurement_unit_id',
    'end_to_end_duration_ms', 'downstream_input_tokens', 'downstream_output_tokens',
    'downstream_cached_input_tokens', 'downstream_cache_hit_count',
}


def prepare(recipe, privacy_namespace, independent_items, items, max_items=256):
    """Validate a single confidentiality batch and return provider primitives.

    Imported lazily so the generic reflex module can load independently during a
    rolling installation. The caller remains responsible for truthful labels.
    """
    from .reflex import ReflexError, identifier, require, text

    require(recipe in RECIPE_VERSIONS, 'recipe-version')
    identifier(privacy_namespace)
    require(type(independent_items) is bool and independent_items, 'dependent-items-separate-requests')
    require(type(items) is list and 1 <= len(items) <= max_items, 'item-count')
    expanded, seen = [], set()
    for item in items:
        require(type(item) is dict, 'recipe-item')
        common = {'id', 'privacy_namespace', 'text'}
        extras = {
            'context_triage/v1': {'goal', 'mandatory_pinned'},
            'routing_advice/v1': {'current_option_id', 'eligible_models'},
            'evidence_gap/v1': {'claim'},
            'risk_flag/v1': {'risk'},
            'tool_advice/v1': {'goal', 'eligible_tools'},
            'failure_triage/v1': {'expected'},
            'change_impact/v1': {'goal'},
        }[recipe]
        require(set(item) == common | extras, 'recipe-item-fields')
        item_id = identifier(item['id'])
        require(item_id not in seen, 'duplicate-item')
        seen.add(item_id)
        require(item['privacy_namespace'] == privacy_namespace, 'mixed-confidentiality-boundary')
        packet = text(item['text'], 6000)
        if recipe == 'context_triage/v1':
            goal = text(item['goal'], 1000)
            require(type(item['mandatory_pinned']) is bool, 'mandatory-pinned')
            expanded.append(dict(id=item_id, primitive='choice', text=packet,
                                 question='For this goal, classify the selected context only. Goal: ' + goal,
                                 choices=CONTEXT_CHOICES))
        elif recipe == 'routing_advice/v1':
            models = item['eligible_models']
            require(type(models) is list and 2 <= len(models) <= 14, 'routing-no-valid-option')
            current = identifier(item['current_option_id'])
            ids, model_ids, choices = set(), set(), {}
            for model in models:
                require(type(model) is dict and set(model) == {'option_id', 'model_id', 'description'}, 'routing-model-fields')
                option = identifier(model['option_id'])
                require(option not in ('keep_current', 'insufficient_basis') and option not in ids, 'routing-option-id')
                ids.add(option)
                model_id = text(model['model_id'], 200)
                require(bool(MODEL_ID.fullmatch(model_id)) and model_id not in model_ids, 'routing-model-id')
                model_ids.add(model_id)
                description = text(model['description'], 240)
                if option != current:
                    choices[option] = model_id + ': ' + description
                else:
                    current_description = model_id + ': ' + description
            require(current in ids and bool(choices), 'routing-no-valid-option')
            choices['keep_current'] = 'Keep the current already eligible model. ' + current_description
            choices['insufficient_basis'] = 'The packet does not support a model recommendation; abstain.'
            expanded.append(dict(id=item_id, primitive='choice', text=packet,
                                 question=('Among only the caller-supplied eligible models, advise on this task. '
                                           'Use only provided model descriptions; do not infer unprovided capabilities. '
                                           'Keeping the current model or abstaining is valid.'),
                                 choices=choices))
        elif recipe == 'evidence_gap/v1':
            claim = text(item['claim'], 1000)
            expanded.append(dict(id=item_id, primitive='choice', text=packet,
                                 question=('For this claim, classify a gap visible in the supplied evidence only. '
                                           'No label certifies completion or truth. Claim: ' + claim),
                                 choices=GAP_CHOICES))
        elif recipe == 'tool_advice/v1':
            goal = text(item['goal'], 1000)
            tools = item['eligible_tools']
            require(type(tools) is list and 1 <= len(tools) <= 14, 'eligible-tools')
            choices = {}
            for tool in tools:
                require(type(tool) is dict and set(tool) == {'option_id', 'description'}, 'tool-fields')
                name = identifier(tool['option_id'])
                require(name not in choices and name not in ('no_tool','uncertain'), 'tool-id')
                choices[name] = text(tool['description'], 300)
            choices.update(no_tool='No supplied tool is useful here.', uncertain='Insufficient basis; host should reason further.')
            expanded.append(dict(id=item_id, primitive='choice', text=packet, choices=choices,
                                 question='Suggest one already eligible tool to consider, without arguments or execution. Goal: '+goal))
        elif recipe in ('failure_triage/v1', 'change_impact/v1'):
            failure = recipe == 'failure_triage/v1'
            purpose = text(item['expected'] if failure else item['goal'], 1000)
            expanded.append(dict(id=item_id, primitive='choice', text=packet,
                                 choices=FAILURE_CHOICES if failure else IMPACT_CHOICES,
                                 question=('Prioritize one investigation area from this packet. This is not a verified diagnosis '
                                           'or a reason to ignore any failure, skip required tests or remove evidence. Context: '+purpose)))
        else:
            risk = text(item['risk'], 1000)
            expanded.append(dict(id=item_id, primitive='noul', text=packet,
                                 question=('Does this packet show a plausible risk of the specified kind? '
                                           'A negative answer grants no permission and proves no safety. Risk: ' + risk)))
    return expanded


def interpret(recipe, items, answers):
    """Map numeric proposals to reversible advice; never issue an action."""
    for item in items:
        answer = answers[item['id']]
        if recipe == 'context_triage/v1':
            selected = answer.get('selected_id') if answer['status'] == 'proposal' else None
            effective = 'read_now' if item['mandatory_pinned'] else selected or 'uncertain'
            show = effective in ('read_now', 'uncertain')
            answer['advice'] = dict(
                label=effective, model_label=selected,
                mandatory_pin_override=bool(item['mandatory_pinned'] and selected != 'read_now'),
                visibility='show_now' if show else 'collapse_recoverably',
                retention='retain_full' if show else 'retain_source_pointer',
                deletion_recommended=False)
        elif recipe == 'routing_advice/v1':
            selected = answer.get('selected_id') if answer['status'] == 'proposal' else None
            current = next(x['model_id'] for x in item['eligible_models']
                           if x['option_id'] == item['current_option_id'])
            if selected == 'keep_current':
                kind, model = 'keep_current', current
            elif selected and selected != 'insufficient_basis':
                kind = 'consider_model'
                model = next(x['model_id'] for x in item['eligible_models'] if x['option_id'] == selected)
            else:
                kind, model = 'abstain', None
            answer['advice'] = dict(kind=kind, model_id=model, current_model_id=current,
                                    automatic_switch=False, eligible_roster_only=True)
        elif recipe == 'evidence_gap/v1':
            selected = answer.get('selected_id') if answer['status'] == 'proposal' else None
            answer['advice'] = dict(gap=selected or 'uncertain', completion_certified=False)
        elif recipe == 'tool_advice/v1':
            selected = answer.get('selected_id') if answer['status'] == 'proposal' else None
            tool_id = selected if selected not in (None, 'no_tool', 'uncertain') else None
            answer['advice'] = dict(tool_id=tool_id, execute=False, arguments_generated=False,
                                    label=selected or 'uncertain', eligible_roster_only=True)
        elif recipe in ('failure_triage/v1', 'change_impact/v1'):
            selected = answer.get('selected_id') if answer['status'] == 'proposal' else None
            answer['advice'] = dict(investigate=selected or 'uncertain', verified=False,
                                    may_skip_required_checks=False)
        else:
            value = answer.get('value') if answer['status'] == 'proposal' else None
            answer['advice'] = dict(flag='plausible' if value is True else
                                    'not_observed_in_packet' if value is False else 'uncertain',
                                    permission_granted=False, safety_certified=False)
    return answers


def validate_outcome(recipe, outcome):
    """Accept only typed caller reports, without prose or secret-bearing fields."""
    from .reflex import require

    require(type(outcome) is dict and set(outcome) <= ALLOWED_OUTCOME_KEYS and
            outcome.get('outcome_version') == OUTCOME_VERSION, 'outcome-schema')
    require(len(outcome) > 1 and any(v is not None for k, v in outcome.items() if k != 'outcome_version'),
            'outcome-empty')
    if 'missed_important_item' in outcome:
        require(recipe == 'context_triage/v1' and
                (outcome['missed_important_item'] is None or type(outcome['missed_important_item']) is bool),
                'outcome-missed-important')
    if 'routing_rework' in outcome:
        require(recipe == 'routing_advice/v1' and
                (outcome['routing_rework'] is None or type(outcome['routing_rework']) is bool),
                'outcome-routing-rework')
    if 'later_assessment' in outcome:
        require(outcome['later_assessment'] is None or outcome['later_assessment'] in
                ('agree', 'disagree', 'abstained'), 'outcome-later-assessment')
    if 'end_to_end_duration_ms' in outcome and outcome['end_to_end_duration_ms'] is not None:
        v = outcome['end_to_end_duration_ms']
        require(type(v) in (float, int) and 0 <= v <= 604800000 and math.isfinite(v),
                'outcome-duration')
    for key in ('downstream_input_tokens', 'downstream_output_tokens',
                'downstream_cached_input_tokens', 'downstream_cache_hit_count'):
        if key in outcome and outcome[key] is not None:
            require(type(outcome[key]) is int and 0 <= outcome[key] <= 1000000000,
                    'outcome-count')
    if outcome.get('downstream_input_tokens') is not None and outcome.get('downstream_cached_input_tokens') is not None:
        require(outcome['downstream_cached_input_tokens'] <= outcome['downstream_input_tokens'],
                'outcome-cache-count')
    numeric_keys = ('end_to_end_duration_ms', 'downstream_input_tokens',
                    'downstream_output_tokens', 'downstream_cached_input_tokens',
                    'downstream_cache_hit_count')
    any_numeric = any(outcome.get(key) is not None for key in numeric_keys)
    if any_numeric:
        from .reflex import identifier
        identifier(outcome.get('measurement_unit_id'))
    else:
        require(outcome.get('measurement_unit_id') is None, 'outcome-measurement-unit')
    return outcome


def summarize(receipts, feedback):
    """Aggregate local caller reports. Missing values stay unknown."""
    from .reflex import strict_json

    successful = [r for r in receipts if r['status'] == 'ok']
    all_items = [(r['receipt_id'], item_id, item) for r in successful
                 for item_id, item in r['results'].items()]
    known_feedback = {(receipt_id, item_id): strict_json(payload)
                      for receipt_id, item_id, payload in feedback}
    def metric(name, true_value=True):
        vals = [known_feedback.get((rid, iid), {}).get(name) for rid, iid, _ in all_items]
        known = [v for v in vals if v is not None]
        return dict(known_count=len(known), unknown_count=len(vals)-len(known),
                    true_count=sum(v == true_value for v in known),
                    rate=(sum(v == true_value for v in known) / len(known)) if known else None)
    def numeric(name):
        vals = [known_feedback.get((rid, iid), {}).get(name) for rid, iid, _ in all_items]
        known = [v for v in vals if v is not None]
        return dict(known_count=len(known), unknown_count=len(vals)-len(known),
                    sum=sum(known) if known else None,
                    mean=(sum(known) / len(known)) if known else None)
    assessments = [known_feedback.get((rid, iid), {}).get('later_assessment') for rid, iid, _ in all_items]
    return dict(
        schema_version=STORAGE_VERSION, outcome_version=OUTCOME_VERSION,
        receipt_count=len(receipts), successful_receipt_count=len(successful),
        unavailable_receipt_count=len(receipts)-len(successful),
        inference_receipt_count=sum(r.get('model_calls_this_invocation') == 1 for r in receipts),
        unknown_dispatch_receipt_count=sum(r.get('model_calls_this_invocation') is None for r in receipts),
        reuse_receipt_count=sum(r.get('reused_success', False) for r in receipts),
        successful_item_count=len(all_items),
        proposal_count=sum(item['status'] == 'proposal' for _, _, item in all_items),
        initial_abstention_count=sum(item['status'] == 'abstain' for _, _, item in all_items),
        feedback_item_count=len(known_feedback),
        missed_important_item=metric('missed_important_item'),
        routing_rework=metric('routing_rework'),
        later_assessment=dict(agree=assessments.count('agree'), disagree=assessments.count('disagree'),
                              abstained=assessments.count('abstained'), unknown=assessments.count(None)),
        end_to_end_duration_ms=numeric('end_to_end_duration_ms'),
        downstream_input_tokens=numeric('downstream_input_tokens'),
        downstream_output_tokens=numeric('downstream_output_tokens'),
        downstream_cached_input_tokens=numeric('downstream_cached_input_tokens'),
        downstream_cache_hit_count=numeric('downstream_cache_hit_count'),
        outcome_source='caller_reported', quality_or_savings_improvement_established=False)
