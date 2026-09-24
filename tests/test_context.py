import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from jev_reflex import Service
from jev_reflex.context import plan
from jev_reflex.reflex import DEFAULT_POLICY, SNAPSHOT


class ContextPlan(unittest.TestCase):
    def test_snapshot_binds_bytes_and_pointers_and_pins_override(self):
        wires=[]
        def fake(wire):
            wires.append(wire)
            return dict(model=SNAPSHOT,provider='TypeSafe',id='fixture',usage={'cost':0},answers={
                k:dict(type='choice',choice='low_relevance',confidence=.99,
                       probabilities={option:(.97 if option=='low_relevance' else .01) for option in q['criteria']})
                for k,q in wire['questions'].items()})
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'policy.json').write_text(json.dumps(DEFAULT_POLICY|{'enabled':True,'daily_limit_microusd':100000}))
            s=Service(root,transport=fake)
            chunks=[dict(id='x',text='A required failure',source_ref='LOCAL_PRIVATE_POINTER',mandatory_pinned=True),
                    dict(id='y',text='An optional aside',source_ref='aside',mandatory_pinned=False)]
            a=plan(s,'p','t','one','n','Find failure',chunks,True)
            self.assertEqual(a['context_plan'][0]['visibility'],'show_now')
            self.assertEqual(a['context_plan'][1]['visibility'],'collapse_recoverably')
            self.assertNotIn('LOCAL_PRIVATE_POINTER',json.dumps(wires))
            self.assertFalse(a['automatic_context_change'])
            b=plan(s,'p','t','two','n','Find failure',[chunks[0]|{'source_ref':'different'},chunks[1]],True)
            self.assertNotEqual(a['complete_input_snapshot'],b['complete_input_snapshot'])
            self.assertFalse(b['reused_success'])
            for f in root.glob('ledger.sqlite*'):
                self.assertNotIn(b'LOCAL_PRIVATE_POINTER',f.read_bytes())

    def test_disabled_keeps_everything_visible_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            s=Service(Path(d),transport=lambda _:self.fail('No call expected'))
            r=plan(s,'p','t','r','n','goal',[dict(id='x',text='text',source_ref='ref',mandatory_pinned=False)])
            self.assertEqual(r['context_plan'][0]['visibility'],'show_now')
            self.assertTrue(r['caller_must_retain_originals'])


if __name__ == '__main__': unittest.main()
