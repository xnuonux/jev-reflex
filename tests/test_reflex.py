import copy
import concurrent.futures
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from jev_reflex import reflex


def request(**changes):
    base = dict(project='test-project', task='test-task', request_id='call-1', snapshot_id='snapshot-1',
                items=[dict(id='route', primitive='choice', text='A compiler reports a type error.',
                            question='Which topic fits?', choices={'code': 'Programming', 'food': 'Cooking'})])
    return base | changes


def response(wire, **changes):
    answers = {}
    for key, q in wire['questions'].items():
        if q['type'] == 'noul':
            answers[key] = {'type': 'noul', 'noul': .9}
        else:
            ids = list(q['criteria'])
            answers[key] = dict(type='choice', choice=ids[0], confidence=.9,
                                probabilities={k: (.9 if i == 0 else .1 / (len(ids)-1)) for i, k in enumerate(ids)})
    return dict(model=reflex.SNAPSHOT, provider='TypeSafe', id='gen-test-1', answers=answers,
                usage={'cost': .00001}) | changes


class ReflexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.now = 100000.
        self.calls = 0
        self.transport = self.fake
        self.service = reflex.Service(self.root, transport=lambda w: self.transport(w), clock=lambda: self.now)
        self.policy(enabled=True)

    def tearDown(self):
        self.tmp.cleanup()

    def policy(self, **kw):
        p = dict(reflex.DEFAULT_POLICY) | dict(enabled=True, daily_limit_microusd=1000000) | kw
        (self.root / 'policy.json').write_text(json.dumps(p))

    def fake(self, wire):
        self.calls += 1
        return response(wire)

    def test_proposal_and_no_authority(self):
        r = self.service.judge(**request())
        self.assertEqual(r['results']['route']['selected_id'], 'code')
        self.assertEqual(r['authority'], 'none')
        self.assertFalse(r['may_execute'])
        self.assertEqual(r['snapshot_id'], 'snapshot-1')
        self.assertEqual(self.calls, 1)

    def test_legacy_pacing_profile_cannot_restore_artificial_delay(self):
        profile=self.root/'research-pacing.json'
        profile.write_text(json.dumps(dict(project='test-project',task='test-task',minimum_start_interval_s=.5,authority='Owner requests faster research routing')))
        self.service=reflex.Service(self.root,transport=self.fake,clock=lambda:self.now,pacing_profile=profile)
        self.assertEqual(self.service.judge(**request())['status'],'ok')
        self.now+=.4
        self.assertEqual(self.service.judge(**request(request_id='call-2'))['status'],'ok')
        self.now+=.2
        self.assertEqual(self.service.judge(**request(request_id='call-2'))['status'],'ok')
        self.assertTrue(self.service.judge(**request(request_id='call-2'))['replayed'])
        self.now+=.6
        self.assertEqual(self.service.judge(**request(task='another',request_id='call-3'))['status'],'ok')
        self.now+=.6
        self.assertEqual(self.service.judge(**request(task='another',request_id='call-4'))['status'],'ok')
        self.assertEqual(self.service.start_interval('other-project','test-task'),0)
        self.assertEqual(reflex.Service(self.root,transport=self.fake,clock=lambda:self.now).start_interval('test-project','test-task'),0)
        self.assertEqual(self.calls,4)

    def test_pacing_profile_rejects_negative_interval(self):
        profile=self.root/'pacing.json'
        profile.write_text(json.dumps(dict(project='test-project',task='test-task',minimum_start_interval_s=-1,authority='Invalid')))
        service=reflex.Service(self.root,transport=self.fake,clock=lambda:self.now,pacing_profile=profile)
        with self.assertRaises(reflex.ReflexError):service.judge(**request())
        self.assertEqual(self.calls,0)

    def test_owner_authorized_zero_pacing_retains_replay_and_defaults(self):
        profile=self.root/'unpaced.json'
        profile.write_text(json.dumps(dict(project='test-project',task='test-task',minimum_start_interval_s=0,authority='Owner explicitly requests no pacing')))
        service=reflex.Service(self.root,transport=self.fake,clock=lambda:self.now,pacing_profile=profile)
        self.assertEqual(service.judge(**request())['status'],'ok')
        self.assertEqual(service.judge(**request(request_id='call-2'))['status'],'ok')
        self.assertTrue(service.judge(**request(request_id='call-2'))['replayed'])
        self.assertEqual(service.start_interval('other','task'),0)
        self.assertEqual(self.calls,2)

    def test_replay_has_no_second_call_and_conflict_refuses(self):
        a = self.service.judge(**request())
        b = self.service.judge(**request())
        self.assertEqual(a['request_digest'], b['request_digest'])
        self.assertTrue(b['replayed'])
        self.assertEqual(self.calls, 1)
        c = self.service.judge(**request(snapshot_id='changed'))
        self.assertEqual(c['reason'], 'idempotency-conflict')

    def test_same_identity_is_separate_between_contexts(self):
        self.service.judge(**request())
        self.now += 3
        self.assertEqual(self.service.judge(**request(task='other'))['status'], 'ok')
        self.assertEqual(self.calls, 2)

    def test_thresholds(self):
        for p, conf, expected in [(.85,.75,'proposal'),(.8499,.9,'abstain'),(.9,.7499,'abstain')]:
            with self.subTest(p=p, conf=conf):
                def send(w):
                    raw=response(w)
                    raw['answers']['q0'].update(probabilities={'code':p,'food':1-p},confidence=conf)
                    return raw
                self.transport=send
                self.now+=3
                r=self.service.judge(**request(request_id=str(self.now)))
                self.assertEqual(r['results']['route']['status'],expected)

    def test_noul_boundaries(self):
        for p, expected in [(.85,True),(.15,False),(.8499,None),(.1501,None)]:
            def send(w):
                raw=response(w);raw['answers']['q0']['noul']=p;return raw
            self.transport=send;self.now+=3
            r=self.service.judge(**request(request_id=str(self.now),items=[dict(id='yes',primitive='noul',text='test',question='Relevant?')]))
            self.assertIs(r['results']['yes'].get('value'),expected)

    def test_malformed_response_fails_closed_and_stays_charged(self):
        changes=[{'model':'typesafe/jev-latest'}, {'provider':'other'}, {'id':''}, {'answers':{}},
                 {'answers':{'q0':dict(type='choice',choice='food',confidence=.9,probabilities={'code':.9,'food':.1})}},
                 {'answers':{'q0':dict(type='choice',choice='code',confidence=True,probabilities={'code':.9,'food':.1})}},
                 {'answers':{'q0':dict(type='choice',choice='code',confidence=.9,probabilities={'code':.8,'food':.1})}}]
        for i,change in enumerate(changes):
            self.transport=lambda w: response(w,**change);self.now+=3
            r=self.service.judge(**request(request_id=str(i)))
            self.assertEqual(r['status'],'unavailable')
            self.assertNotIn('results',r)
        self.assertEqual(self.service.status()['accounted_microusd'],len(changes)*reflex.ENVELOPE)

    def test_bad_input_makes_no_call(self):
        bad=[request(items=[]),request(items=[dict(id='x',primitive='score',text='x',question='x')]),
             request(items=[dict(id='x',primitive='noul',text='x',question='x',choices={})]),
             request(items=[dict(id='x',primitive='choice',text='x',question='x',choices={'constructor':'bad','ok':'ok'})]),
             request(items=[dict(id='x',primitive='noul',text='x'*17000,question='x')])]
        for x in bad:
            with self.assertRaises(reflex.ReflexError):self.service.judge(**x)
        self.assertEqual(self.calls,0)

    def test_disabled_budget_and_known_cost(self):
        self.policy(enabled=False)
        self.assertEqual(self.service.judge(**request())['reason'],'disabled')
        self.policy(daily_limit_microusd=reflex.ENVELOPE-1)
        self.assertEqual(self.service.judge(**request())['reason'],'daily-budget')
        self.assertEqual(self.calls,0)
        self.policy()
        self.service.judge(**request())
        self.assertEqual(self.service.status()['accounted_microusd'],10)

    def test_missing_cost_keeps_envelope(self):
        self.transport=lambda w: response(w,usage={})
        self.service.judge(**request())
        self.assertEqual(self.service.status()['accounted_microusd'],reflex.ENVELOPE)

    def test_excess_cost_trips_stop(self):
        self.transport=lambda w:response(w,usage={'cost':1})
        self.assertEqual(self.service.judge(**request())['reason'],'cost-exceeded-envelope')
        self.now+=3
        self.assertEqual(self.service.judge(**request(request_id='next'))['reason'],'accounting-stop')

    def test_exception_no_retry_or_provider_prose(self):
        def send(w):self.calls+=1;raise TimeoutError('ZZQX PRIVATE exception')
        self.transport=send
        a=self.service.judge(**request());b=self.service.judge(**request())
        self.assertEqual(self.calls,1)
        self.assertEqual(a['status'],'unavailable')
        self.assertNotIn('ZZQX',json.dumps(a)+json.dumps(b))
        self.assertEqual(self.service.status()['accounted_microusd'],reflex.ENVELOPE)

    def test_cross_instance_concurrency_no_duplicate(self):
        entered=threading.Event();release=threading.Event()
        def send(w):entered.set();release.wait(5);return response(w)
        self.transport=send
        other=reflex.Service(self.root,transport=self.fake,clock=lambda:self.now)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            first=pool.submit(self.service.judge,**request())
            self.assertTrue(entered.wait(2))
            duplicate=other.judge(**request())
            different=other.judge(**request(request_id='another'))
            self.assertEqual(duplicate['reason'],'pending-or-uncertain')
            self.assertEqual(different['status'],'ok')
            release.set();self.assertEqual(first.result()['status'],'ok')

    def test_parallel_reservations_still_enforce_aggregate_budget(self):
        self.policy(daily_limit_microusd=reflex.ENVELOPE)
        entered=threading.Event();release=threading.Event()
        def send(w):
            entered.set();release.wait(5);return response(w)
        self.transport=send
        other=reflex.Service(self.root,transport=lambda w:self.fail('over-budget dispatch'),clock=lambda:self.now)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            first=pool.submit(self.service.judge,**request())
            try:
                self.assertTrue(entered.wait(2))
                self.assertEqual(other.judge(**request(request_id='different'))['reason'],'daily-budget')
            finally:
                release.set()
            self.assertEqual(first.result()['status'],'ok')

    def test_no_spacing_and_clock_rewind(self):
        self.service.judge(**request())
        self.assertEqual(self.service.judge(**request(request_id='two'))['status'],'ok')
        self.now-=1
        self.assertEqual(self.service.judge(**request(request_id='three'))['reason'],'clock-rewind')

    def test_legacy_next_start_does_not_delay_new_clients(self):
        with reflex.connection(self.service.path) as db:
            db.execute("UPDATE meta SET value=? WHERE name='next_start'",(self.now+2,))
        self.assertEqual(self.service.judge(**request())['status'],'ok')
        self.assertEqual(self.service.status()['minimum_start_interval_s'],0)

    def test_http_diagnostic_is_bounded_and_keeps_uncertain_accounting(self):
        import subprocess
        for code in (402,429,503):
            run=subprocess.CompletedProcess([],2,json.dumps({'http_status':code}).encode())
            with patch.object(reflex,'credential',return_value='secret-not-logged'), patch.object(reflex.subprocess,'run',return_value=run):
                self.transport=reflex.provider_transport
                r=self.service.judge(**request(request_id=f'http-{code}'))
            self.assertEqual(r['reason'],f'provider-http-{code}')
            self.assertEqual(r['accounted_microusd'],reflex.ENVELOPE)
            self.assertNotIn('secret',json.dumps(r))
        bad=subprocess.CompletedProcess([],2,b'{"http_status":"secret-provider-body"}')
        with patch.object(reflex,'credential',return_value='secret-not-logged'), patch.object(reflex.subprocess,'run',return_value=bad):
            with self.assertRaisesRegex(reflex.ReflexError,'^transport$'):
                reflex.provider_transport({})

    def test_private_text_not_persisted(self):
        x=request();x['items'][0]['text']='ZZQX Private source text'
        self.assertEqual(self.service.judge(**x)['status'],'ok')
        self.assertEqual(self.calls,1)
        for f in self.root.glob('*'):
            if f.is_file():self.assertNotIn(b'ZZQX',f.read_bytes())

    def test_malformed_answer_cannot_hide_over_envelope_cost(self):
        self.transport=lambda w:response(w,answers={},usage={'cost':1})
        r=self.service.judge(**request())
        self.assertEqual(r['reason'],'cost-exceeded-envelope')
        self.assertTrue(self.service.status()['accounting_stop'])
        self.assertEqual(self.service.status()['accounted_microusd'],1000000)

    def test_uncertain_settlement_blocks_after_lease_expiry(self):
        lock=sqlite3.connect(self.service.path,isolation_level=None)
        def send(w):
            lock.execute('BEGIN IMMEDIATE')
            return response(w,usage={'cost':1})
        self.transport=send
        try:
            self.assertEqual(self.service.judge(**request())['reason'],'settlement-uncertain')
        finally:
            lock.rollback();lock.close()
        self.transport=lambda w:self.fail('must not dispatch past unresolved accounting')
        self.now+=31
        self.assertEqual(self.service.judge(**request(request_id='next'))['reason'],'accounting-unresolved')

    def test_generation_echo_not_retained(self):
        self.transport=lambda w:response(w,id='ZZQX_PRIVATE_SOURCE_TEXT')
        r=self.service.judge(**request())
        self.assertEqual(r['status'],'ok')
        self.assertNotIn('ZZQX',json.dumps(r))
        self.assertIn('generation_id_sha256',r)
        for f in self.root.glob('*'):
            if f.is_file():self.assertNotIn(b'ZZQX',f.read_bytes())

    def test_cold_start_contention_waits_without_inference(self):
        # Lock the fresh database before constructing the service. Release independently.
        cold=self.root/'cold';cold.mkdir()
        lock=sqlite3.connect(cold/'ledger.sqlite',isolation_level=None,check_same_thread=False)
        lock.execute('BEGIN EXCLUSIVE')
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future=pool.submit(reflex.Service,cold)
            threading.Event().wait(1)
            lock.rollback();lock.close()
            service=future.result(timeout=3)
            self.assertEqual(service.status()['calls_today'],0)

    def test_transport_wall_deadline_kills_real_child(self):
        import subprocess
        worker=self.root/'transport.py'
        worker.write_text('import time\ntime.sleep(60)\n')
        original=subprocess.run
        seen=[]
        def short_deadline(*args,**kwargs):
            seen.append(kwargs['timeout'])
            kwargs['timeout']=.15
            return original(*args,**kwargs)
        with patch.object(reflex,'__file__',str(self.root/'reflex.py')), patch.object(reflex,'credential',return_value='test-only-not-a-key'), patch.object(reflex.subprocess,'run',side_effect=short_deadline):
            with self.assertRaises(subprocess.TimeoutExpired):
                reflex.provider_transport({'model':'test'})
        self.assertEqual(seen,[20])

    def test_no_credential_makes_no_reservation(self):
        service=reflex.Service(self.root,clock=lambda:self.now)
        with patch.object(reflex,'credential',return_value=None):
            self.assertEqual(service.judge(**request())['reason'],'credential-unavailable')
        self.assertEqual(service.status()['calls_today'],0)

    def test_limits_are_atomic_and_daily(self):
        self.policy(max_daily_calls=1)
        self.service.judge(**request());self.now+=3
        self.assertEqual(self.service.judge(**request(request_id='two'))['reason'],'daily-call-limit')
        self.now+=86400
        self.assertEqual(self.service.judge(**request(request_id='three'))['status'],'ok')

    def test_owner_can_disable_all_daily_quotas_without_disabling_accounting(self):
        self.policy(daily_limit_microusd=None,max_daily_calls=None,max_context_daily_calls=None)
        # Seed settled accounting beyond every formerly accepted numeric limit.
        with reflex.connection(self.service.path) as db:
            context=reflex.build(**request())[2]
            db.executemany('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?)',
                [(f'seed-{i}','seed',context,int(self.now//86400),self.now-100,'settled',100000000,100000000,'{}') for i in range(10001)])
        result=self.service.judge(**request())
        self.assertEqual(result['status'],'ok')
        status=self.service.status()
        self.assertIsNone(status['daily_limit_microusd'])
        self.assertIsNone(status['max_daily_calls'])
        self.assertIsNone(status['max_context_daily_calls'])
        self.assertEqual(status['calls_today'],10002)
        self.assertEqual(status['accounted_microusd'],1000100000010)
        self.assertEqual(self.calls,1)

    def test_optional_quota_values_remain_strict_and_independently_enforced(self):
        for invalid in [True,-1,'unlimited',1.5]:
            self.policy(daily_limit_microusd=invalid)
            with self.assertRaises(reflex.ReflexError):self.service.policy()
        self.policy(daily_limit_microusd=None,max_daily_calls=0,max_context_daily_calls=None)
        self.assertEqual(self.service.judge(**request())['reason'],'daily-call-limit')
        self.policy(daily_limit_microusd=None,max_daily_calls=None,max_context_daily_calls=0)
        self.assertEqual(self.service.judge(**request())['reason'],'context-call-limit')
        self.policy(daily_limit_microusd=0,max_daily_calls=None,max_context_daily_calls=None)
        self.assertEqual(self.service.judge(**request())['reason'],'daily-budget')
        self.assertEqual(self.calls,0)

    def test_unlimited_quota_zero_spacing_keeps_idempotency(self):
        self.policy(daily_limit_microusd=None,max_daily_calls=None,max_context_daily_calls=None)
        self.assertEqual(self.service.judge(**request())['status'],'ok')
        self.assertEqual(self.service.judge(**request(request_id='second'))['status'],'ok')
        self.assertTrue(self.service.judge(**request())['replayed'])
        self.assertEqual(self.calls,2)

    def test_rolling_owner_override_disables_quotas_but_not_enabled_flag(self):
        self.policy(daily_limit_microusd=0,max_daily_calls=0,max_context_daily_calls=0)
        overrides=dict(daily_limit_microusd=None,max_daily_calls=None,max_context_daily_calls=None)
        (self.root/'quota-overrides.json').write_text(json.dumps(overrides))
        self.assertEqual(self.service.judge(**request())['status'],'ok')
        self.policy(enabled=False)
        self.assertEqual(self.service.judge(**request(request_id='new'))['reason'],'disabled')
        (self.root/'quota-overrides.json').write_text(json.dumps(overrides|{'enabled':True}))
        with self.assertRaises(reflex.ReflexError):self.service.policy()


if __name__=='__main__':unittest.main()
