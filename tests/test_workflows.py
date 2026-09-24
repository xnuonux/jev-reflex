import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from jev_reflex.reflex import Service, DEFAULT_POLICY, SNAPSHOT, ReflexError, connection
from jev_reflex.workflows import run
from jev_reflex.api import invoke


class Workflows(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        (self.root/'policy.json').write_text(json.dumps(DEFAULT_POLICY|{'enabled':True,'daily_limit_microusd':1000000}))
        self.wires=[]; self.values={}; self.choice=None; self.fail=False
        self.s=Service(self.root,transport=self.fake)
    def tearDown(self): self.tmp.cleanup()
    def fake(self,w):
        self.wires.append(w)
        if self.fail: raise RuntimeError('private error')
        answers={}
        for i,(k,q) in enumerate(w['questions'].items()):
            if q['type']=='noul': answers[k]=dict(type='noul',noul=self.values.get(i,.99))
            else:
                opts=list(q['criteria']); chosen=self.choice or next(x for x in opts if x!='none')
                answers[k]=dict(type='choice',choice=chosen,confidence=.99,
                    probabilities={x:.99 if x==chosen else .01/(len(opts)-1) for x in opts})
        return dict(model=SNAPSHOT,provider='TypeSafe',id='fixture',usage={'cost':0},answers=answers)
    def runpack(self,w,p,r='a'):
        return invoke(self.s,'workflow',dict(project='public',task='test',request_id=r,privacy_namespace='public',workflow=w,packet=p))
    def progress(self): return dict(goal='Fix compilation',steps=[dict(action='Run compiler',observation='Type mismatch',evidence_ref='PRIVATE_POINTER')]*2)
    def skills(self): return dict(goal='Write docs',candidates=[dict(id='docs',description='Write technical docs',instructions='Use evidence.',revision='abc')])
    def test_progress_uses_observations_and_does_not_halt(self):
        self.values={0:.01,1:.01,2:.01,3:.01,4:.01,5:.99}
        a=self.runpack('progress_watch/v1',self.progress())
        self.assertEqual(a['advice']['kind'],'consider_replan'); self.assertFalse(a['advice']['automatic_halt'])
        self.assertEqual(a['advice']['exact_adjacent_repeats'],1)
        self.assertNotIn('PRIVATE_POINTER',json.dumps(self.wires))
    def test_useful_negative_evidence_vetoes_stagnation(self):
        self.values={0:.01,1:.01,2:.01,3:.99,4:.01,5:.99}
        self.assertEqual(self.runpack('progress_watch/v1',self.progress())['advice']['kind'],'continue_with_evidence')
    def test_provider_error_stays_unknown_and_replays_without_retry(self):
        self.fail=True
        a=self.runpack('progress_watch/v1',self.progress()); self.assertEqual(a['status'],'unavailable')
        self.assertEqual(a['advice']['kind'],'uncertain'); self.runpack('progress_watch/v1',self.progress())
        self.assertEqual(len(self.wires),1); self.assertNotIn('private error',json.dumps(a))
    def test_skill_two_stages_replay_and_revision_binding(self):
        p=self.skills(); a=self.runpack('skill_shortlist/v1',p)
        self.assertEqual(a['advice']['skill_id'],'docs'); self.assertEqual(len(self.wires),2)
        self.runpack('skill_shortlist/v1',p); self.assertEqual(len(self.wires),2)
        p['candidates'][0]['revision']='changed'
        b=self.runpack('skill_shortlist/v1',p); self.assertEqual(b['status'],'unavailable'); self.assertEqual(len(self.wires),2)
    def test_selected_skill_needs_its_own_fit(self):
        self.values={1:.01,2:.99}
        p=self.skills(); p['candidates'].append(dict(id='other',description='Other',instructions='Something else',revision='v1'))
        self.assertIsNone(self.runpack('skill_shortlist/v1',p)['advice']['skill_id'])
    def test_critical_reports_bypass_inference_and_remain_visible(self):
        p=dict(goal='Integrate',reports=[dict(id='x',status='blocked',summary='Need input',source_ref='private-ref')])
        a=self.runpack('swarm_inbox/v1',p)
        self.assertEqual(len(self.wires),0); self.assertEqual(a['advice']['reports'][0]['priority'],'surface_now')
    def test_unknown_inbox_is_not_hidden(self):
        self.fail=True
        p=dict(goal='Integrate',reports=[dict(id='x',status='progress',summary='Some work',source_ref='private-ref')])
        a=self.runpack('swarm_inbox/v1',p)
        self.assertEqual(a['advice']['reports'][0]['priority'],'review_unknown')
        self.assertNotIn('private-ref',json.dumps(self.wires)); self.assertFalse(a['advice']['suppress_reports'])
    def test_patch_and_handoff_flags_never_certify(self):
        for w,p in [('patch_review/v1',dict(goal='Fix',diff='-assert x',requirements='Keep test',checks='No checks')),
                    ('handoff_check/v1',dict(original='Do not deploy',handoff='Deploy now')),
                    ('memory_conflict/v1',dict(existing='Use TS',incoming='Use Python today'))]:
            a=self.runpack(w,p,w.replace('/','-')); self.assertTrue(a['advice']['flagged']); self.assertFalse(a['advice']['verified'])
    def test_packet_rejects_extra_fields_before_calls(self):
        with self.assertRaises(ReflexError): self.runpack('progress_watch/v1',self.progress()|{'secret':'no'})
        self.assertEqual(len(self.wires),0)
    def test_decision_pack_only_consumes_matching_target(self):
        p=dict(state='Need tests',operations=[dict(id='test',description='Test',candidates=[dict(id='unit',description='Unit test')])])
        a=self.runpack('decision_pack/v1',p)
        self.assertEqual(a['advice']['target'],'unit'); self.assertFalse(a['advice']['execute'])
    def test_raw_packet_not_persisted(self):
        p=dict(original='ZZQX_PRIVATE',handoff='ZZQX_PRIVATE preserved')
        self.runpack('handoff_check/v1',p)
        for f in self.root.glob('ledger.sqlite*'): self.assertNotIn(b'ZZQX_PRIVATE',f.read_bytes())
    def test_zero_call_workflow_still_binds_request_id(self):
        p=dict(goal='Integrate',reports=[dict(id='x',status='blocked',summary='Need input',source_ref='ref')])
        self.runpack('swarm_inbox/v1',p)
        p['reports'][0]['status']='failed'
        self.assertEqual(self.runpack('swarm_inbox/v1',p)['reason'],'idempotency-conflict')
        self.assertEqual(len(self.wires),0)
    def test_contended_binding_refuses_without_inference(self):
        with connection(self.s.path) as db:
            db.execute('BEGIN IMMEDIATE')
            a=self.runpack('progress_watch/v1',self.progress())
            self.assertEqual(a['reason'],'ledger-busy'); self.assertEqual(len(self.wires),0)

if __name__=='__main__': unittest.main()
