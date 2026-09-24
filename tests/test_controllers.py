import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from jev_reflex.reflex import DEFAULT_POLICY, Service, ReflexError, SNAPSHOT, connection
from jev_reflex.providers import OPENROUTER
from jev_reflex.api import invoke


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.calls = 0
        self.choice = 'code'
        self.uncertain = False
        self.service = Service(self.root, transport=self.fake, profile=OPENROUTER, clock=lambda: 100000.)
        (self.root/'policy.json').write_text(json.dumps(DEFAULT_POLICY | {
            'enabled': True, 'daily_limit_microusd': 1000000}))
        self.key = dict(project='p', task='t', privacy_namespace='public', controller_id='route')
        self.seq = 0
        self.signal = dict(primitive='choice', question='Investigation direction?', choices={'code':'Code','fixture':'Fixture'})
        self.open_args = self.key | dict(snapshot_id='s0', signal=self.signal)
        self.call('controller_open', **self.open_args)

    def tearDown(self):
        self.temp.cleanup()

    def fake(self, wire):
        self.calls += 1
        answers = {}
        for key, q in wire['questions'].items():
            if q['type'] == 'noul':
                answers[key] = dict(type='noul', noul=.1 if self.choice == 'fixture' else .9)
            else:
                answers[key] = dict(type='choice', choice=self.choice, confidence=.9,
                                    probabilities={k: .5 if self.uncertain else
                                        (.9 if k == self.choice else .1) for k in q['criteria']})
        return dict(model=SNAPSHOT, provider='TypeSafe', id='synthetic',
                    answers=answers, usage={'cost': .00001})

    def call(self, method, **args):
        return invoke(self.service, method, args)

    def state(self):
        return self.call('controller_inspect', **self.key)['controller']

    def send(self, kind, **fields):
        self.seq += 1
        return self.call('controller_event', **self.key, event_id=f'e{self.seq}',
                         expected_revision=self.state()['revision'], event=dict(kind=kind, **fields))['controller']

    def receipt(self, request='r0', snapshot=None, shared=False, primitive='choice'):
        item = dict(id='signal', primitive=primitive, question='Investigation direction?')
        if primitive == 'choice':
            item['choices'] = {'code': 'Code', 'fixture': 'Fixture'}
        args = dict(project='p', task='t', request_id=request,
                    snapshot_id=snapshot or self.state()['snapshot_id'])
        if shared:
            self.service.shared(**args, privacy_namespace='public', state='ZZQX-private-source',
                                questions=[item], independent_questions=True)
        else:
            self.service.judge(**args, items=[item | {'text': 'ZZQX-private-source'}])
        return dict(kind='shared' if shared else 'batch', request_id=request, item_id='signal')

    def vote(self, choice, source, uncertain=False):
        if source != self.state()['snapshot_id']:
            self.send('bind', snapshot_id=source)
        self.choice, self.uncertain = choice, uncertain
        return self.send('observe', receipt=self.receipt(request='r-'+source))

    def test_switching_reduced_and_real_change_delayed_one_observation(self):
        labels = ['code','fixture','code','fixture','code','fixture','fixture']
        actual = [self.vote(x, 's'+str(i))['selected_id'] for i,x in enumerate(labels)]
        self.assertEqual(actual, ['code']*6+['fixture'])
        self.assertEqual(sum(a != b for a,b in zip(labels, labels[1:])), 5)
        self.assertEqual(sum(a != b for a,b in zip(actual, actual[1:])), 1)
        self.assertEqual(self.state()['supported_snapshot'], 's6')
        self.assertEqual([r['snapshot_id'] for r in self.state()['confirmation_evidence']], ['s5','s6'])

    def test_abstention_and_skipped_sources_break_streak(self):
        self.vote('code', 's0')
        self.vote('fixture', 's1')
        s = self.vote('fixture', 's2', uncertain=True)
        self.assertIsNone(s['challenger'])

        # Refresh code, then a skipped source must not count as consecutive support.
        self.vote('code', 's3')
        self.vote('fixture', 's4')
        self.send('bind', snapshot_id='s5')
        # Bounded retention expiry clears selection too at s6.
        s = self.vote('fixture', 's6')
        self.assertEqual(s['reason'], 'supported')
        self.assertIsNone(s['challenger'])

    def test_skipped_source_clears_displayed_challenger_immediately(self):
        self.key['controller_id'] = 'long-retention'
        self.call('controller_open', **self.key, snapshot_id='s0', signal=self.signal,
                  policy={'confirmations':2,'max_hold_sources':10,'override_sources':4})
        self.vote('code','s0')
        self.vote('fixture','s1')
        self.assertIsNotNone(self.send('bind',snapshot_id='s2')['challenger'])
        self.assertIsNone(self.send('bind',snapshot_id='s3')['challenger'])
        self.assertEqual(self.vote('fixture','s4')['reason'], 'challenger-pending')

    def test_one_vote_per_source_even_distinct_requests(self):
        ref = self.receipt()
        self.send('observe', receipt=ref)
        another = self.receipt('r1')
        before = self.state()
        with self.assertRaisesRegex(ReflexError, 'source-already-observed'):
            self.send('observe', receipt=another)
        self.assertEqual(self.state(), before)

    def test_support_provenance_survives_abstention(self):
        first = self.vote('code', 's0')['supporting_evidence']
        s = self.vote('fixture', 's1', uncertain=True)
        self.assertEqual(s['supporting_evidence'], first)
        self.assertEqual(s['last_evidence']['snapshot_id'], 's1')
        self.assertNotEqual(s['last_evidence']['request_digest'], first['request_digest'])
        self.assertIsNone(self.send('override', selected_id='fixture')['supporting_evidence'])

    def test_question_and_candidate_descriptions_bound(self):
        for i, signal in enumerate((self.signal | {'question':'What is for lunch?'},
                                   self.signal | {'choices':{'code':'Dessert','fixture':'Main'}})):
            self.service.judge(project='p', task='t', request_id=f'unrelated{i}', snapshot_id='s0',
                               items=[signal | {'id':'signal','text':'ZZQX-private-source'}])
            with self.assertRaisesRegex(ReflexError, 'signal-mismatch'):
                self.send('observe', receipt=dict(kind='batch', request_id=f'unrelated{i}', item_id='signal'))
        self.assertEqual(self.state()['revision'], 0)

    def test_late_receipt_source_reuse_and_foreign_scope(self):
        ref = self.receipt()
        self.send('bind', snapshot_id='s1')
        before = self.state()
        with self.assertRaisesRegex(ReflexError, 'stale-snapshot'):
            self.send('observe', receipt=ref)
        with self.assertRaisesRegex(ReflexError, 'snapshot-reused'):
            self.send('bind', snapshot_id='s0')
        self.assertEqual(self.state(), before)
        self.call('controller_open', **(self.open_args | {'task': 'foreign'}))
        with self.assertRaisesRegex(ReflexError, 'receipt-unsettled'):
            self.call('controller_event', **(self.key | {'task': 'foreign'}),
                      event_id='foreign', expected_revision=0, event=dict(kind='observe', receipt=ref))

    def test_override_survives_evidence_and_expires_at_source_bound(self):
        self.send('override', selected_id='fixture')
        self.assertEqual(self.vote('code', 's0')['selected_id'], 'fixture')
        for n in range(1, 5):
            self.assertEqual(self.send('bind', snapshot_id=f's{n}')['selected_id'], 'fixture')
        self.assertIsNone(self.send('bind', snapshot_id='s5')['selected_id'])
        self.send('override', selected_id='fixture')
        self.assertIsNone(self.send('release')['selected_id'])

    def test_stop_bypasses_stale_revision_and_never_resurrects(self):
        self.vote('code', 's0')
        out = self.call('controller_event', **self.key, event_id='stop', expected_revision=0,
                        event={'kind':'stop'})
        self.assertEqual(out['controller']['phase'], 'stopped')
        self.assertIsNone(out['controller']['selected_id'])
        self.assertFalse(out['may_execute'])
        for kind in ('pause','resume','release','bind'):
            with self.assertRaisesRegex(ReflexError, 'controller-stopped'):
                self.send(kind, **({'snapshot_id':'s1'} if kind == 'bind' else {}))

    def test_pause_resume_clears_hint_and_prevents_reusing_old_vote(self):
        self.vote('code', 's0')
        self.call('controller_event', **self.key, event_id='pause', expected_revision=0,
                  event={'kind':'pause'})
        with self.assertRaisesRegex(ReflexError, 'not-active'):
            self.send('override', selected_id='fixture')
        self.assertIsNone(self.send('resume')['selected_id'])
        with self.assertRaisesRegex(ReflexError, 'source-already-observed'):
            self.send('observe', receipt=dict(kind='batch', request_id='r-s0', item_id='signal'))

    def test_pause_invalidates_source_even_before_first_observation(self):
        ref = self.receipt()
        self.send('pause')
        self.assertEqual(self.send('resume')['reason'], 'awaiting-new-snapshot')
        with self.assertRaisesRegex(ReflexError, 'source-already-observed'):
            self.send('observe', receipt=ref)
        self.assertEqual(self.vote('code', 's1')['selected_id'], 'code')

    def test_demo_compares_identical_streams(self):
        from jev_reflex.controller_demo import run
        report = run()
        self.assertEqual((report['stateless_switches'], report['controller_switches']), (5, 1))
        self.assertEqual(report['paid_calls'], 0)
        self.assertIsNone(report['stopped_hint'])
        self.assertEqual(report['trace'][-1]['held_hint'], 'fixture')
        self.assertTrue(all(row['evidence_origin'] == 'injected-transport' for row in report['trace']))

    def test_replay_returns_current_not_old_state_and_conflict_refuses(self):
        args = self.key | dict(event_id='manual', expected_revision=0,
                              event=dict(kind='override', selected_id='code'))
        self.call('controller_event', **args)
        self.send('stop')
        replay = self.call('controller_event', **args)
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['controller']['phase'], 'stopped')
        self.assertIsNone(replay['controller']['selected_id'])
        with self.assertRaisesRegex(ReflexError, 'event-conflict'):
            self.call('controller_event', **(args | {'expected_revision': 1}))

    def test_reopen_contract_and_process_cli_inspect(self):
        self.vote('code','s0')
        old = self.state()
        self.service = Service(self.root, transport=lambda _: self.fail('network'))
        self.assertEqual(self.call('controller_open', **self.open_args)['controller'], old)
        with self.assertRaisesRegex(ReflexError, 'contract-conflict'):
            self.call('controller_open', **(self.open_args | {'snapshot_id':'new'}))
        run = subprocess.run([sys.executable, '-m', 'jev_reflex', 'call', 'controller_inspect'],
            input=json.dumps(self.key), text=True, capture_output=True, timeout=15,
            env=dict(os.environ, JEV_REFLEX_HOME=str(self.root),
                     PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src')))
        self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
        self.assertEqual(json.loads(run.stdout)['controller'], old)

    def test_concurrent_revision_single_winner(self):
        def change(n):
            try:
                return self.call('controller_event', **self.key, event_id=f'race{n}',
                    expected_revision=0, event=dict(kind='override', selected_id='code'))['status']
            except ReflexError as e:
                return str(e)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(change, range(4)))
        self.assertEqual(results.count('ok'), 1)
        self.assertEqual(results.count('controller-revision-conflict'), 3)

    def test_noul_false_is_valid_hint_and_provenance_is_synthetic(self):
        self.key['controller_id'] = 'noul'
        self.call('controller_open', **self.key, snapshot_id='s0', signal=dict(primitive='noul', question='Investigation direction?'))
        self.choice = 'fixture'
        s = self.send('observe', receipt=self.receipt('noul', shared=True, primitive='noul'))
        self.assertEqual(s['selected_id'], 'false')
        self.assertEqual(s['last_evidence']['evidence_origin'], 'injected-transport')

    def test_shared_namespace_binding_and_option_vocabulary(self):
        ref = self.receipt(shared=True)
        self.call('controller_open', **(self.open_args | {'privacy_namespace':'other'}))
        with self.assertRaisesRegex(ReflexError, 'receipt-unsettled'):
            self.call('controller_event', **(self.key | {'privacy_namespace':'other'}), event_id='bad',
                      expected_revision=0, event=dict(kind='observe', receipt=ref))
        self.call('controller_open', **(self.open_args | {'controller_id':'different', 'signal':self.signal | {'choices':{'x':'X','y':'Y'}}}))
        with self.assertRaisesRegex(ReflexError, 'signal-mismatch'):
            self.call('controller_event', **(self.key | {'controller_id':'different'}), event_id='bad',
                      expected_revision=0, event=dict(kind='observe', receipt=ref))

    def test_malformed_events_and_policy_mutate_nothing(self):
        before = self.state()
        for evt in ({'kind':'observe','receipt':{'probabilities':{}}},
                    {'kind':'override','selected_id':'absent'}, {'kind':'pause','junk':1},
                    {'kind':'execute'}, {'kind':'bind','snapshot_id':'../x'}):
            with self.assertRaises(ReflexError):
                self.call('controller_event', **self.key, event_id='bad', expected_revision=0, event=evt)
        for revision in (True, -1, 1.2, None):
            with self.assertRaises(ReflexError):
                self.call('controller_event', **self.key, event_id='bad', expected_revision=revision,
                          event={'kind':'pause'})
        for policy in ({}, {'confirmations':True,'max_hold_sources':2,'override_sources':4},
                       {'confirmations':9,'max_hold_sources':2,'override_sources':4}):
            with self.assertRaises(ReflexError):
                self.call('controller_open', **(self.open_args | {'policy':policy}))
        self.assertEqual(self.state(), before)

    def test_failed_provider_cannot_vote(self):
        self.service.transport = lambda _: {}
        ref = self.receipt()
        with self.assertRaisesRegex(ReflexError, 'raw-success-required'):
            self.send('observe', receipt=ref)
        self.assertEqual(self.state()['revision'], 0)

    def test_no_source_plaintext_or_inference_in_controller(self):
        self.vote('code','s0')
        count = self.calls
        self.send('override', selected_id='fixture')
        self.send('pause')
        self.state()
        self.assertEqual(self.calls, count)
        with connection(self.service.path) as db:
            self.assertGreater(db.execute('SELECT count(*) FROM controller_events').fetchone()[0], 0)
            for table in ('controllers','controller_events','controller_snapshots'):
                self.assertNotIn('ZZQX-private-source', str([tuple(r) for r in db.execute('SELECT * FROM '+table)]))


if __name__ == '__main__':
    unittest.main()
