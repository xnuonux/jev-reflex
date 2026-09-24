"""Offline fixtures for advisory recipes, exact reuse, and typed caller reports."""
import concurrent.futures
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from jev_reflex import reflex
from jev_reflex import recipes


def context_item(namespace='private-a', **changes):
    return dict(id='a', privacy_namespace=namespace, text='ZZQX_PRIVATE selected context',
                goal='Investigate the failing build', mandatory_pinned=False) | changes


def route_item(namespace='private-a', **changes):
    return dict(id='route', privacy_namespace=namespace, text='Small task packet with stated requirements',
                current_option_id='sol', eligible_models=[
                    dict(option_id='sol', model_id='gpt-6-sol', description='Current approved model'),
                    dict(option_id='luna', model_id='gpt-6-luna', description='Approved lightweight model')]) | changes


def recipe_call(recipe='context_triage/v1', items=None, **changes):
    if items is None:
        items = [context_item()]
    return dict(project='project-a', task='triage', request_id='r1', snapshot_id='sha256-a',
                privacy_namespace='private-a', recipe=recipe, items=items,
                independent_items=True, reuse_success=False) | changes


class RecipeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'policy.json').write_text(json.dumps(reflex.DEFAULT_POLICY | {
            'enabled': True, 'daily_limit_microusd': 1000000}))
        self.now = 100000.0
        self.calls = 0
        self.selected = None
        self.choice_probability = .9
        self.noul_probability = .9
        self.service = reflex.Service(self.root, transport=self.fake, clock=lambda: self.now)

    def tearDown(self):
        self.tmp.cleanup()

    def fake(self, wire):
        self.calls += 1
        answers = {}
        for key, q in wire['questions'].items():
            if q['type'] == 'noul':
                answers[key] = dict(type='noul', noul=self.noul_probability)
            else:
                ids = list(q['criteria'])
                chosen = self.selected or ids[0]
                ps = {item_id: ((self.choice_probability if item_id == chosen else
                                 (1-self.choice_probability)/(len(ids)-1))) for item_id in ids}
                answers[key] = dict(type='choice', choice=chosen, confidence=.9,
                                    probabilities=ps)
        return dict(model=reflex.SNAPSHOT, provider='TypeSafe', id='fake-generation',
                    answers=answers, usage={'cost': .00001})

    def test_context_pin_overrides_low_relevance_and_preserves_source(self):
        self.selected = 'low_relevance'
        args = recipe_call(items=[context_item(id='unpinned'),
                                  context_item(id='pinned', mandatory_pinned=True)])
        out = self.service.recipe(**args)
        self.assertEqual(out['status'], 'ok')
        self.assertEqual(out['authority'], 'none')
        self.assertFalse(out['may_execute'])
        low = out['results']['unpinned']['advice']
        self.assertEqual((low['visibility'], low['retention']),
                         ('collapse_recoverably', 'retain_source_pointer'))
        self.assertFalse(low['deletion_recommended'])
        pinned = out['results']['pinned']['advice']
        self.assertEqual((pinned['visibility'], pinned['retention']),
                         ('show_now', 'retain_full'))
        self.assertTrue(pinned['mandatory_pin_override'])
        self.assertEqual(pinned['model_label'], 'low_relevance')
        for file in self.root.iterdir():
            if file.is_file():
                self.assertNotIn(b'ZZQX_PRIVATE', file.read_bytes())

    def test_ambiguous_context_stays_visible_and_empty_packet_refuses(self):
        self.selected = 'low_relevance'
        self.choice_probability = .6
        result = self.service.recipe(**recipe_call())
        self.assertEqual(result['results']['a']['status'], 'abstain')
        self.assertEqual(result['results']['a']['advice']['visibility'], 'show_now')
        self.assertEqual(result['results']['a']['advice']['retention'], 'retain_full')
        with self.assertRaises(reflex.ReflexError):
            self.service.recipe(**recipe_call(request_id='empty', items=[context_item(text='')]))
        self.assertEqual(self.calls, 1)

    def test_routing_uses_only_explicit_roster_and_can_abstain_or_keep_current(self):
        self.selected = 'luna'
        first = self.service.recipe(**recipe_call('routing_advice/v1', [route_item()]))
        advice = first['results']['route']['advice']
        self.assertEqual(advice['kind'], 'consider_model')
        self.assertEqual(advice['model_id'], 'gpt-6-luna')
        self.assertFalse(advice['automatic_switch'])
        self.selected = 'keep_current'
        second = self.service.recipe(**recipe_call('routing_advice/v1', [route_item()], request_id='r2'))
        self.assertEqual(second['results']['route']['advice']['kind'], 'keep_current')
        self.selected = 'insufficient_basis'
        third = self.service.recipe(**recipe_call('routing_advice/v1', [route_item()], request_id='r3'))
        self.assertEqual(third['results']['route']['advice']['kind'], 'abstain')
        self.choice_probability = .6
        fourth = self.service.recipe(**recipe_call('routing_advice/v1', [route_item()], request_id='r4'))
        self.assertEqual(fourth['results']['route']['status'], 'abstain')
        self.assertEqual(fourth['results']['route']['advice']['kind'], 'abstain')
        self.assertEqual(self.calls, 4)

    def test_evidence_gap_and_risk_flag_never_certify_or_grant(self):
        self.selected = 'no_gap_visible'
        gap = self.service.recipe(**recipe_call('evidence_gap/v1', [dict(
            id='gap', privacy_namespace='private-a', text='One small test result',
            claim='The feature is complete')]))
        self.assertEqual(gap['results']['gap']['advice']['gap'], 'no_gap_visible')
        self.assertFalse(gap['results']['gap']['advice']['completion_certified'])
        self.noul_probability = .1
        risk = self.service.recipe(**recipe_call('risk_flag/v1', [dict(
            id='risk', privacy_namespace='private-a', text='Selected change description',
            risk='Unapproved external action')], request_id='r2'))
        self.assertEqual(risk['results']['risk']['advice']['flag'], 'not_observed_in_packet')
        self.assertFalse(risk['results']['risk']['advice']['permission_granted'])
        self.assertFalse(risk['results']['risk']['advice']['safety_certified'])

    def test_schema_confidentiality_dependency_and_roster_validation_before_dispatch(self):
        bad = [
            recipe_call(recipe='context_triage/v2'),
            recipe_call(items=[context_item(), context_item(namespace='private-b', id='b')]),
            recipe_call(independent_items=False),
            recipe_call(items=[context_item(depends_on=['other'])]),
            recipe_call(items=[context_item(mandatory_pinned='yes')]),
            recipe_call('routing_advice/v1', [route_item(eligible_models=[])]),
            recipe_call('routing_advice/v1', [route_item(current_option_id='missing')]),
            recipe_call('routing_advice/v1', [route_item(eligible_models=[
                dict(option_id='sol', model_id='gpt-6-sol', description='Only one')])]),
        ]
        for args in bad:
            with self.subTest(args=args), self.assertRaises(reflex.ReflexError):
                self.service.recipe(**args)
        self.assertEqual(self.calls, 0)

    def test_exact_opt_in_reuse_has_new_receipt_and_invalidation(self):
        args = recipe_call(reuse_success=True)
        first = self.service.recipe(**args)
        self.assertEqual(self.calls, 1)
        self.assertFalse(first['reused_success'])
        second = self.service.recipe(**(args | {'request_id': 'r2'}))
        self.assertEqual(self.calls, 1)
        self.assertTrue(second['reused_success'])
        self.assertEqual(second['historical_source_receipt_id'], first['receipt_id'])
        self.assertNotEqual(second['receipt_id'], first['receipt_id'])
        self.assertNotEqual(second['request_digest'], first['request_digest'])
        self.assertEqual((second['model_calls_this_invocation'], second['accounted_microusd']), (0, 0))
        self.assertEqual(self.service.recipe(**(args | {'request_id': 'r2'}))['receipt_id'],
                         second['receipt_id'])
        replay = self.service.recipe(**args)
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['receipt_id'], first['receipt_id'])
        self.assertFalse(replay['reused_success'])
        conflict = self.service.recipe(**(args | {'items': [context_item(goal='Changed under old ID')]}))
        self.assertEqual(conflict['reason'], 'idempotency-conflict')
        variants = [
            {'request_id': 'r3', 'snapshot_id': 'sha256-b'},
            {'request_id': 'r4', 'items': [context_item(goal='A different goal')]},
            {'request_id': 'r5', 'items': [context_item(mandatory_pinned=True)]},
            {'request_id': 'r6', 'privacy_namespace': 'private-b',
             'items': [context_item(namespace='private-b')]},
        ]
        for change in variants:
            out = self.service.recipe(**(args | change))
            self.assertFalse(out['reused_success'])
        self.assertEqual(self.calls, 5)
        with patch.object(recipes, 'THRESHOLD_VERSION', 'changed-threshold-version'):
            self.assertFalse(self.service.recipe(**(args | {'request_id': 'r7'}))['reused_success'])
        from dataclasses import replace
        with patch.object(self.service, 'profile', replace(self.service.profile, request_model='typesafe/changed-model-pin')):
            self.assertFalse(self.service.recipe(**(args | {'request_id': 'r8'}))['reused_success'])
        self.assertEqual(self.calls, 7)
        status = self.service.status()
        self.assertEqual(status['calls_today'], 7)
        self.assertEqual(status['reused_recipe_receipts_today'], 1)
        with reflex.connection(self.service.path) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM calls').fetchone()[0], 7)

    def test_changed_routing_options_invalidate_reuse(self):
        self.selected = 'luna'
        args = recipe_call('routing_advice/v1', [route_item()], reuse_success=True)
        self.service.recipe(**args)
        changed = route_item()
        changed['eligible_models'][1]['description'] = 'Changed approved capability'
        result = self.service.recipe(**(args | {'request_id': 'r2', 'items': [changed]}))
        self.assertFalse(result['reused_success'])
        self.assertEqual(self.calls, 2)

    def test_reuse_cannot_bypass_disabled_or_unresolved_accounting(self):
        args = recipe_call(reuse_success=True)
        self.service.recipe(**args)
        (self.root / 'policy.json').write_text(json.dumps(reflex.DEFAULT_POLICY | {
            'enabled': False, 'daily_limit_microusd': 1000000}))
        self.assertEqual(self.service.recipe(**(args | {'request_id': 'r2'}))['reason'], 'disabled')
        (self.root / 'policy.json').write_text(json.dumps(reflex.DEFAULT_POLICY | {
            'enabled': True, 'daily_limit_microusd': 1000000}))
        with reflex.connection(self.service.path) as db:
            db.execute('INSERT INTO calls VALUES (?,?,?,?,?,?,?,NULL,NULL)',
                       ('stale', 'stale', 'stale', 1, self.now-31, 'pending', reflex.ENVELOPE))
        self.assertEqual(self.service.recipe(**(args | {'request_id': 'r3'}))['reason'],
                         'accounting-unresolved')
        self.assertEqual(self.calls, 1)

    def test_fault_is_not_cached_and_provider_pin_remains_strict(self):
        original = self.service.transport
        self.service.transport = lambda wire: original(wire) | {'provider': 'Different'}
        args = recipe_call(reuse_success=True)
        failed = self.service.recipe(**args)
        self.assertEqual((failed['status'], failed['reason']), ('unavailable', 'provider'))
        self.service.transport = original
        later = self.service.recipe(**(args | {'request_id': 'r2'}))
        self.assertFalse(later['reused_success'])
        self.assertEqual(self.calls, 2)
        self.assertEqual(self.service.status()['accounted_microusd'], reflex.ENVELOPE+10)

    def test_concurrent_pending_result_is_not_reused(self):
        entered, both_entered, release = threading.Event(), threading.Event(), threading.Event()
        entry_lock = threading.Lock()
        entries = 0
        original = self.service.transport
        def blocked(wire):
            nonlocal entries
            with entry_lock:
                entries += 1
                entered.set()
                if entries == 2:
                    both_entered.set()
            release.wait(4)
            return original(wire)
        self.service.transport = blocked
        args = recipe_call(reuse_success=True)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            first = pool.submit(self.service.recipe, **args)
            self.assertTrue(entered.wait(2))
            self.assertEqual(self.service.recipe(**args)['reason'], 'pending-or-uncertain')
            # A distinct operation cannot borrow an unfinished result.
            second = pool.submit(self.service.recipe, **(args | {'request_id': 'r2'}))
            self.assertTrue(both_entered.wait(2))
            release.set()
            self.assertEqual(first.result()['status'], 'ok')
            self.assertEqual(second.result()['status'], 'ok')
        self.assertEqual(self.calls, 2)

    def test_feedback_binds_actual_receipt_and_is_private_idempotent(self):
        result = self.service.recipe(**recipe_call(items=[context_item(id='a'), context_item(id='b')]))
        receipt = result['receipt_id']
        outcome = dict(outcome_version='v1', missed_important_item=True,
                       later_assessment='agree', measurement_unit_id='run-1',
                       end_to_end_duration_ms=125, downstream_input_tokens=100,
                       downstream_cached_input_tokens=20, downstream_output_tokens=10,
                       downstream_cache_hit_count=1)
        first = self.service.record_outcome('project-a', 'triage', 'private-a', receipt, 'a', outcome)
        self.assertFalse(first['replayed'])
        self.assertTrue(self.service.record_outcome('project-a', 'triage', 'private-a',
                                                   receipt, 'a', outcome)['replayed'])
        with self.assertRaisesRegex(reflex.ReflexError, 'feedback-conflict'):
            self.service.record_outcome('project-a', 'triage', 'private-a', receipt, 'a',
                                        outcome | {'missed_important_item': False})
        for project, namespace, receipt_id, item in [
            ('wrong', 'private-a', receipt, 'a'), ('project-a', 'private-b', receipt, 'a'),
            ('project-a', 'private-a', '0'*64, 'a'), ('project-a', 'private-a', receipt, 'unknown')]:
            with self.assertRaises(reflex.ReflexError):
                self.service.record_outcome(project, 'triage', namespace, receipt_id, item, outcome)
        with self.assertRaises(reflex.ReflexError):
            self.service.record_outcome('project-a', 'triage', 'private-a', receipt, 'b',
                                        outcome | {'measurement_unit_id': 'run-1'})
        with self.assertRaises(reflex.ReflexError):
            self.service.record_outcome('project-a', 'triage', 'private-a', receipt, 'b',
                                        {'outcome_version': 'v1', 'note': 'ZZQX_SECRET'})
        with self.assertRaises(reflex.ReflexError):
            self.service.record_outcome('project-a', 'triage', 'private-a', receipt, 'b',
                                        {'outcome_version': 'v2', 'missed_important_item': True})
        summary = self.service.recipe_metrics('project-a', 'triage', 'private-a')['metrics']
        self.assertEqual(summary['missed_important_item']['known_count'], 1)
        self.assertEqual(summary['missed_important_item']['unknown_count'], 1)
        self.assertEqual(summary['downstream_input_tokens']['sum'], 100)
        self.assertEqual(summary['downstream_input_tokens']['unknown_count'], 1)
        self.assertEqual(summary['later_assessment']['unknown'], 1)
        self.assertFalse(summary['quality_or_savings_improvement_established'])
        for file in self.root.iterdir():
            if file.is_file():
                self.assertNotIn(b'ZZQX_SECRET', file.read_bytes())

    def test_feedback_refuses_unavailable_and_invalid_numeric_reports(self):
        self.service.transport = lambda wire: {'provider': 'Wrong'}
        failed = self.service.recipe(**recipe_call())
        self.assertEqual(failed['status'], 'unavailable')
        with self.assertRaisesRegex(reflex.ReflexError, 'feedback-not-successful'):
            self.service.record_outcome('project-a', 'triage', 'private-a',
                                        failed['receipt_id'], 'a',
                                        {'outcome_version': 'v1', 'missed_important_item': True})
        self.service.transport = self.fake
        good = self.service.recipe(**recipe_call(request_id='r2'))
        for invalid in [
            {'outcome_version': 'v1', 'routing_rework': True},
            {'outcome_version': 'v1', 'end_to_end_duration_ms': 12},
            {'outcome_version': 'v1', 'downstream_input_tokens': -1, 'measurement_unit_id': 'run'},
            {'outcome_version': 'v1', 'downstream_input_tokens': 10,
             'downstream_cached_input_tokens': 11, 'measurement_unit_id': 'run'},
            {'outcome_version': 'v1', 'missed_important_item': None},
        ]:
            with self.subTest(invalid=invalid), self.assertRaises(reflex.ReflexError):
                self.service.record_outcome('project-a', 'triage', 'private-a',
                                            good['receipt_id'], 'a', invalid)


if __name__ == '__main__':
    unittest.main()
