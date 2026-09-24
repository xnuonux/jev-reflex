import concurrent.futures
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from jev_reflex.reflex import Service, DEFAULT_POLICY, ReflexError, build, packed, ENVELOPE, connection
from jev_reflex.bulk import prepare
from jev_reflex.api import invoke
from test_reflex import response


def items(n, shared=False):
    return [dict(id=f'i{x}',primitive='noul',question='Relevant to software?',
                 **({} if shared else {'text':f'Compiler report {x}'})) for x in range(n)]


class BulkTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.clock=100000.
        self.wires=[]
        self.service=Service(self.root,transport=self.send,clock=lambda:self.clock)
        (self.root/'policy.json').write_text(json.dumps(DEFAULT_POLICY | dict(enabled=True,daily_limit_microusd=2000000)))
        self.args=dict(project='p',task='t',request_id='j',snapshot_id='v1',privacy_namespace='public',
                       items=items(1000),independent_items=True)
        self.key={k:self.args[k] for k in ('project','task','request_id','privacy_namespace')}

    def tearDown(self):
        self.tmp.cleanup()

    def send(self,wire):
        self.wires.append(wire)
        return response(wire)

    def capacity(self,**values):
        (self.root/'capacity.json').write_text(json.dumps(values))

    def drain(self,args):
        for _ in range(100):
            r=self.service.bulk(**args)
            if r['next_step'] != 'continue-same-input':
                return r
            self.clock += 2
        self.fail('job did not complete')

    def test_native_thirteen_and_shared_state_once(self):
        r=self.service.judge('p','t','native','v1',items(13))
        self.assertEqual(len(r['results']),13)
        r=self.service.shared('p','t','shared','v1','public',
                              'UNIQUE_SHARED_CONTEXT',items(50,True),True)
        self.assertEqual(len(r['results']),50)
        self.assertEqual(packed(self.wires[-1]).count('UNIQUE_SHARED_CONTEXT'),1)
        self.assertEqual(len(self.wires),2)
        self.assertFalse(r['may_execute'])

    def test_thousand_item_job_pack_resume_pagination_and_no_raw_spool(self):
        self.args['items'][0]['text']='ZZQX_PRIVATE_PACKET'
        r=self.drain(self.args)
        self.assertEqual(r['status'],'ok')
        self.assertEqual(r['total_items'],1000)
        self.assertGreater(r['total_batches'],1)
        self.assertLess(r['total_batches'],125)
        self.assertEqual(sum(len(w['questions']) for w in self.wires),1000)
        for wire in self.wires:
            self.assertLessEqual(len(packed(wire).encode()),60000)
        seen=[]
        offset=0
        while offset is not None:
            page=self.service.inspect_job(**self.key,offset=offset,limit=137)
            seen.extend(x['id'] for x in page['items'])
            offset=page['next_offset']
        self.assertEqual(seen,[f'i{x}' for x in range(1000)])
        before=len(self.wires)
        self.service=Service(self.root,transport=self.send,clock=lambda:self.clock)
        self.assertEqual(self.service.bulk(**self.args)['status'],'ok')
        self.assertEqual(len(self.wires),before)
        for f in self.root.glob('*'):
            self.assertNotIn(b'ZZQX_PRIVATE_PACKET',f.read_bytes())

    def test_shared_bulk_and_recipe_bulk(self):
        self.capacity(max_questions=20)
        r=self.drain(self.args | dict(items=items(53,True),shared_state={'packet':'ONCE_PER_BATCH'}))
        self.assertEqual(r['status'],'ok')
        self.assertEqual(len(self.wires),3)
        self.assertTrue(all(packed(w).count('ONCE_PER_BATCH')==1 for w in self.wires))
        recipe_items=[dict(id=f'r{x}',privacy_namespace='public',text='a compiler log',risk='network failure') for x in range(53)]
        r=self.drain(self.args | dict(request_id='recipe',items=recipe_items,recipe='risk_flag/v1'))
        self.assertEqual(r['status'],'ok')
        self.assertIn('advice',r['items'][0]['answer'])

    def test_invalid_last_item_and_duplicate_are_preflight_no_calls(self):
        for last in (dict(id='bad',primitive='score',text='x',question='x'),items(1)[0]):
            bad=items(999)+[last]
            with self.assertRaises(ReflexError):
                self.service.bulk(**(self.args | dict(items=bad)))
        with self.assertRaisesRegex(ReflexError,'dependent'):
            self.service.bulk(**(self.args | dict(independent_items=False)))
        self.assertEqual(self.wires,[])
        self.assertEqual(self.service.inspect_job(**self.key)['status'],'not-found')

    def test_job_binds_contents_order_snapshot_and_plan(self):
        self.capacity(max_questions=5)
        args=self.args | dict(items=items(20),max_batches=1)
        r=self.service.bulk(**args)
        self.assertEqual(r['batch_counts']['ok'],1)
        for changes in (dict(snapshot_id='v2'),dict(items=list(reversed(args['items']))),dict(shared_state='new')):
            if 'shared_state' in changes:
                with self.assertRaises(ReflexError):self.service.bulk(**(args | changes))
            else:
                self.assertEqual(self.service.bulk(**(args | changes))['reason'],'idempotency-conflict')
        self.capacity(max_questions=6)
        self.assertEqual(self.service.bulk(**args)['reason'],'idempotency-conflict')
        self.assertEqual(len(self.wires),1)

    def test_cancellation_during_admitted_call_settles_without_new_calls(self):
        self.capacity(max_questions=5,max_concurrency=1)
        entered,release=threading.Event(),threading.Event()
        def gate(wire):
            entered.set();self.assertTrue(release.wait(5));return self.send(wire)
        self.service.transport=gate
        with concurrent.futures.ThreadPoolExecutor() as pool:
            run=pool.submit(self.service.bulk,**(self.args | dict(items=items(20))))
            self.assertTrue(entered.wait(3))
            cancelled=self.service.cancel_job(**self.key)
            self.assertEqual(cancelled['status'],'cancelling')
            release.set()
            r=run.result(5)
        self.assertEqual(r['status'],'cancelled')
        self.assertEqual(len(self.wires),1)
        self.assertEqual(r['batch_counts'],dict(waiting=3,pending=0,ok=1,failed=0))
        self.service.bulk(**(self.args | dict(items=items(20))))
        self.assertEqual(len(self.wires),1)

    def test_duplicate_concurrent_job_no_duplicate_dispatch(self):
        self.capacity(max_questions=5,max_concurrency=2)
        entered,release=threading.Event(),threading.Event()
        def gate(w):
            entered.set();self.assertTrue(release.wait(5));return self.send(w)
        self.service.transport=gate
        other=Service(self.root,transport=self.send,clock=lambda:self.clock)
        args=self.args | dict(items=items(10))
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future=pool.submit(self.service.bulk,**args)
            self.assertTrue(entered.wait(3))
            second=other.bulk(**args)
            self.assertIn(second['status'],('pending','ok'))
            release.set();future.result(5)
        self.assertEqual(sum(len(w['questions']) for w in self.wires),10)

    def test_budget_holds_each_child_and_refusal_spends_nothing(self):
        self.capacity(max_questions=5,max_concurrency=1)
        (self.root/'policy.json').write_text(json.dumps(DEFAULT_POLICY | dict(enabled=True,daily_limit_microusd=ENVELOPE)))
        self.service.transport=lambda w: (self.wires.append(w) or response(w,usage={}))
        r=self.service.bulk(**(self.args | dict(items=items(10))))
        self.assertEqual(len(self.wires),1)
        self.assertEqual(r['run_refusals'],[{'reason':'daily-budget'}])
        self.assertEqual(r['accounted_microusd'],ENVELOPE)
        self.assertEqual(r['batch_counts']['waiting'],1)

    def test_rate_admission_shared_across_instances_and_resumes(self):
        self.capacity(max_questions=5,max_concurrency=1,requests_per_minute=1)
        args=self.args | dict(items=items(10))
        r=self.service.bulk(**args)
        self.assertEqual(r['run_refusals'][0]['reason'],'rate-limit')
        other=Service(self.root,transport=self.send,clock=lambda:self.clock)
        self.assertEqual(other.judge('other','task','r','v1',items(1))['reason'],'rate-limit')
        self.clock+=60
        self.assertEqual(self.service.bulk(**args)['status'],'ok')
        self.assertEqual(len(self.wires),2)

    def test_uncertain_paid_child_never_redispatched(self):
        self.capacity(max_questions=5,max_concurrency=1)
        def timeout(w):
            self.wires.append(w);raise TimeoutError('PRIVATE_PROVIDER_PROSE')
        self.service.transport=timeout
        args=self.args | dict(items=items(10))
        r=self.service.bulk(**args)
        self.assertEqual(r['status'],'partial-failure')
        self.service=Service(self.root,transport=self.send,clock=lambda:self.clock)
        r=self.service.bulk(**args)
        self.assertEqual(len(self.wires),1)
        self.assertNotIn('PRIVATE_PROVIDER_PROSE',packed(r))

    def test_crashed_pending_call_stays_pending_after_reopen(self):
        self.capacity(max_questions=5)
        args=self.args | dict(items=items(10),max_batches=1)
        self.service.bulk(**args)
        with connection(self.service.path) as db:
            db.execute("UPDATE calls SET state='pending',result=NULL")
        self.clock+=40
        self.service=Service(self.root,transport=self.send,clock=lambda:self.clock)
        r=self.service.bulk(**args)
        self.assertEqual(r['status'],'pending')
        self.assertEqual(len(self.wires),1)

    def test_settled_replay_survives_disable_and_missing_key(self):
        args=dict(project='p',task='t',request_id='r',snapshot_id='v1',items=items(13))
        self.service.judge(**args)
        (self.root/'policy.json').write_text(json.dumps(DEFAULT_POLICY))
        self.service=Service(self.root,clock=lambda:self.clock)
        self.assertTrue(self.service.judge(**args)['replayed'])
        self.assertEqual(len(self.wires),1)

    def test_capacity_and_private_argument_validation(self):
        for settings in (dict(max_questions=True),dict(max_concurrency=33),dict(max_request_bytes=60001),dict(foo=1)):
            self.capacity(**settings)
            with self.assertRaises(ReflexError):self.service.capacity()
        self.capacity()
        with self.assertRaisesRegex(ReflexError,'arguments-fields'):
            invoke(self.service,'bulk',self.args | {'_job':['fake',0]})
        self.assertEqual(self.wires,[])

    def test_recipe_plan_digest_matches_actual_reservation(self):
        args=self.args | dict(items=[dict(id='r',privacy_namespace='public',text='log',risk='failure')],recipe='risk_flag/v1')
        self.assertEqual(self.service.bulk(**args)['status'],'ok')
        with connection(self.service.path) as db:
            plan=json.loads(db.execute('SELECT plan FROM bulk_jobs').fetchone()[0])
            for child in plan:
                actual=db.execute('SELECT digest FROM calls WHERE identity=?',(child['call_identity'],)).fetchone()[0]
                self.assertEqual(actual,child['request_digest'])

    def test_lower_capacity_keeps_native_and_shared_replay_but_blocks_new_dispatch(self):
        kwargs=dict(project='p',task='t',request_id='raw',snapshot_id='v1',items=items(13))
        self.assertEqual(self.service.judge(**kwargs)['status'],'ok')
        shared=dict(project='p',task='t',request_id='shared',snapshot_id='v1',privacy_namespace='public',
                    state='one packet',questions=items(13,True),independent_questions=True)
        self.assertEqual(self.service.shared(**shared)['status'],'ok')
        self.capacity(max_questions=8,max_request_bytes=1024,max_state_question_bytes=512)
        self.assertTrue(self.service.judge(**kwargs)['replayed'])
        self.assertTrue(self.service.shared(**shared)['replayed'])
        with self.assertRaisesRegex(ReflexError,'item-count'):
            self.service.judge(**(kwargs | dict(request_id='new')))
        self.assertEqual(len(self.wires),2)

    def test_clock_rewind_allows_read_only_replay_but_never_new_admission(self):
        args=dict(project='p',task='t',request_id='r',snapshot_id='v1',items=items(13))
        self.service.judge(**args)
        self.clock-=1
        self.assertTrue(self.service.judge(**args)['replayed'])
        self.assertEqual(self.service.judge(**(args | dict(request_id='new')))['reason'],'clock-rewind')
        self.assertEqual(len(self.wires),1)

    def test_cancel_during_preflight_wins_before_registration(self):
        from jev_reflex import bulk
        entered,release=threading.Event(),threading.Event()
        original=bulk.prepare
        def blocked(*args,**kwargs):
            entered.set();self.assertTrue(release.wait(5));return original(*args,**kwargs)
        with patch.object(bulk,'prepare',side_effect=blocked), concurrent.futures.ThreadPoolExecutor() as pool:
            future=pool.submit(self.service.bulk,**(self.args | dict(items=items(13))))
            self.assertTrue(entered.wait(3))
            cancel=self.service.cancel_job(**self.key)
            self.assertEqual(cancel['status'],'cancelled')
            release.set()
            self.assertEqual(future.result(5)['status'],'cancelled')
        self.assertEqual(len(self.wires),0)

    def test_route_capacity_is_distinct_and_strict(self):
        from jev_reflex.providers import TYPESAFE
        self.capacity(max_questions=256,routes={'typesafe':{'max_questions':100,'requests_per_minute':900}})
        other=Service(self.root,transport=self.send,clock=lambda:self.clock,profile=TYPESAFE)
        self.assertEqual(self.service.capacity()['max_questions'],256)
        self.assertEqual(other.capacity()['max_questions'],100)
        self.assertEqual(other.capacity()['requests_per_minute'],900)
        self.capacity(routes={'arbitrary-endpoint':{}})
        with self.assertRaisesRegex(ReflexError,'capacity-routes'):self.service.capacity()

    def test_byte_rate_never_overcommits_and_counts_actual_utf8(self):
        self.capacity(max_questions=1,max_concurrency=1,max_request_bytes=1024,
                      max_state_question_bytes=1024,request_bytes_per_second=1024)
        args=self.args | dict(items=[dict(id=f'i{i}',primitive='noul',text='🧠'*75,question='Relevant?') for i in range(3)])
        r=self.service.bulk(**args)
        self.assertEqual(len(self.wires),1)
        self.assertEqual(r['run_refusals'][0]['reason'],'byte-rate-limit')
        self.clock+=1
        r=self.service.bulk(**args)
        self.assertEqual(len(self.wires),2)

    def test_active_slot_status_does_not_disable_remaining_capacity(self):
        entered,release=threading.Event(),threading.Event()
        def gate(w):entered.set();release.wait(5);return self.send(w)
        self.service.transport=gate
        with patch('jev_reflex.reflex.credential',return_value='not-a-real-key'), concurrent.futures.ThreadPoolExecutor() as pool:
            future=pool.submit(self.service.judge,'p','t','held','v1',items(1))
            self.assertTrue(entered.wait(3))
            r=self.service.status()
            self.assertEqual(r['status'],'ready')
            self.assertEqual(r['active_calls'],1)
            self.assertEqual(r['uncertain_calls'],0)
            release.set();future.result(5)

    def test_real_processes_share_bulk_child_ownership(self):
        self.capacity(max_questions=5,max_concurrency=4)
        script=self.root/'worker.py'
        script.write_text(
            f'import sys,json,time\nfrom pathlib import Path\nsys.path.insert(0,{str(Path(__file__).resolve().parents[1]/"src")!r})\n'
            'from jev_reflex.reflex import Service,SNAPSHOT\nroot=Path(__file__).parent\n'
            'def fake(w):\n'
            ' with (root/"dispatches").open("a") as f:f.write(next(iter(w["state"].values()))+"\\n")\n'
            ' time.sleep(.1)\n'
            ' return dict(model=SNAPSHOT,provider="TypeSafe",id="g",answers={k:{"type":"noul","noul":.9} for k in w["questions"]},usage={"cost":.00001})\n'
            's=Service(root,transport=fake,clock=lambda:100000.)\n'
            'r=s.bulk(project="p",task="t",request_id="j",snapshot_id="v1",privacy_namespace="public",independent_items=True,items=[dict(id=f"i{x}",primitive="noul",text=f"Compiler report {x}",question="Relevant to software?") for x in range(20)])\n'
            'print(json.dumps(r))\n')
        flags=subprocess.CREATE_NO_WINDOW if sys.platform=='win32' else 0
        children=[subprocess.Popen([sys.executable,str(script)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                   creationflags=flags) for _ in range(2)]
        for child in children:
            out,err=child.communicate(timeout=10)
            self.assertEqual(child.returncode,0,err.decode())
        r=self.service.bulk(**(self.args | dict(items=items(20))))
        self.assertEqual(r['status'],'ok')
        lines=(self.root/'dispatches').read_text().splitlines()
        self.assertEqual(sorted(lines),sorted(f'Compiler report {i}' for i in (0,5,10,15)))
        self.assertEqual(len(self.wires),0)


if __name__=='__main__':unittest.main()
