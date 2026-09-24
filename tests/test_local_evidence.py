import tempfile
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from jev_reflex.reflex import Service, ReflexError, connection, digest
from jev_reflex.api import invoke


class LocalEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.s=Service(Path(self.tmp.name),transport=lambda _:self.fail('No network'))
    def tearDown(self): self.tmp.cleanup()
    def test_artifact_exact_roundtrip_and_scope(self):
        k=dict(project='p',privacy_namespace='private')
        a=invoke(self.s,'artifact_put',k|dict(content='A😀B\n'))
        b=invoke(self.s,'artifact_get',k|dict(artifact_id=a['artifact_id'],start=1,length=1))
        self.assertEqual(b['content'],'😀'); self.assertEqual(b['offset_unit'],'unicode-codepoints')
        self.assertEqual(invoke(self.s,'artifact_put',k|dict(content='A😀B\n'))['artifact_id'],a['artifact_id'])
        with self.assertRaises(ReflexError): invoke(self.s,'artifact_get',k|dict(privacy_namespace='else',artifact_id=a['artifact_id']))
    def test_artifact_corruption_is_not_returned(self):
        k=dict(project='p',privacy_namespace='n'); a=invoke(self.s,'artifact_put',k|dict(content='saved'))
        with connection(self.s.root/'artifacts.sqlite') as db:
            db.execute('UPDATE artifacts SET content=?',(b'corrupt',)); db.commit()
        with self.assertRaises(ReflexError): invoke(self.s,'artifact_get',k|dict(artifact_id=a['artifact_id']))
    def test_no_path_input_or_negative_range(self):
        with self.assertRaises(ReflexError): invoke(self.s,'artifact_put',dict(project='p',privacy_namespace='n',path='C:/secret'))
        with self.assertRaises(ReflexError): invoke(self.s,'artifact_get',dict(project='p',privacy_namespace='n',artifact_id='a'*64,start=-1))
    def test_missing_artifact_get_creates_no_store(self):
        path=self.s.root/'artifacts.sqlite'
        self.assertFalse(path.exists())
        with self.assertRaises(ReflexError): invoke(self.s,'artifact_get',dict(project='p',privacy_namespace='n',artifact_id='a'*64))
        self.assertFalse(path.exists())
    def examples(self):
        family=next('f'+str(i) for i in range(100) if int(digest('f'+str(i))[:8],16)%5==0)
        return [dict(family=family,text='one',expected=True,probability_true=.99),
                dict(family=family,text='two',expected=False,probability_true=.5)]
    def audit(self,revision='r1',examples=None):
        return invoke(self.s,'calibration_audit',dict(project='p',privacy_namespace='n',recipe_revision=revision,
                      model='jev-fixture',split='holdout',examples=examples or self.examples()))
    def test_holdout_abstention_and_contamination(self):
        a=self.audit(); self.assertEqual(a['abstentions'],1); self.assertEqual(a['accepted_accuracy'],1)
        self.assertTrue(a['fresh_holdout_in_local_ledger']); self.assertFalse(self.audit()['fresh_holdout_in_local_ledger'])
        self.assertEqual(self.audit('r2')['contaminated_examples'],2)
        self.assertFalse(self.audit('r2')['automatic_promotion'])
    def test_changed_predictions_under_same_revision_are_not_fresh(self):
        e=self.examples(); e[0]['probability_true']=.01
        self.assertTrue(self.audit(examples=e)['fresh_holdout_in_local_ledger'])
        e[0]['probability_true']=.99
        self.assertFalse(self.audit(examples=e)['fresh_holdout_in_local_ledger'])
    def test_family_reassignment_refuses_and_duplicate_content_refuses(self):
        self.audit(); e=self.examples(); e[0]['family']='changed'
        with self.assertRaises(ReflexError): self.audit(examples=e)
        e=self.examples(); e[1]['text']=e[0]['text']
        with self.assertRaises(ReflexError): self.audit(examples=e)

if __name__=='__main__': unittest.main()
