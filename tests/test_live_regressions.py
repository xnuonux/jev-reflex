"""Offline negative controls derived from the 2026-09-24 direct TypeSafe run."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from jev_reflex.providers import TYPESAFE
from jev_reflex.reflex import DEFAULT_POLICY, ENVELOPE, Service


def items(n=8):
    return [dict(id=f's{i}', primitive='choice', text='A vendor-specific API procedure.',
                 question='Which review lane fits this source?',
                 choices={k:k for k in ('adapter','reference','method','stub','unclear')})
            for i in range(n)]


def envelope(wire, malformed=False):
    answer=dict(type='choice', choice='adapter', confidence=.92,
                probabilities=dict(adapter=.93,reference=0.,method=.02,stub=.05,unclear=0.))
    answers={k:copy.deepcopy(answer) for k in wire['questions']}
    if malformed:
        # The live provider returned exactly this 0.99 distribution.
        answers['q0']['probabilities']['stub']=.04
    return dict(model='jev-1.13.0',answers=answers,
                usage=dict(input_tokens=500,output_tokens=100))


class LiveRegressionTests(unittest.TestCase):
    def fixture(self, root, transport):
        (root/'policy.json').write_text(json.dumps(DEFAULT_POLICY | {
            'enabled':True, 'daily_limit_microusd':10*ENVELOPE}))
        return Service(root,transport=transport,profile=TYPESAFE)

    def test_live_099_distribution_refuses_whole_batch_and_replay_never_pays_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); wires=[]
            def send(wire):
                wires.append(wire)
                return envelope(wire,malformed=True)
            s=self.fixture(root,send)
            first=s.judge('p','t','malformed','v1',items())
            self.assertEqual(first['reason'],'distribution-sum')
            self.assertNotIn('results',first)  # No implicit salvage of seven siblings.
            self.assertEqual(first['accounted_microusd'],ENVELOPE)
            self.assertIsNone(first['reported_microusd'])
            again=s.judge('p','t','malformed','v1',items())
            self.assertTrue(again['replayed'])
            self.assertEqual(again['model_calls_this_invocation'],0)
            self.assertEqual(len(wires),1)
            self.assertEqual(s.status()['accounted_microusd'],ENVELOPE)
            # Positive control: the same distribution with sum 1 is accepted.
            s.transport=lambda wire:envelope(wire)
            control=s.judge('p','t','control','v1',items())
            self.assertEqual(control['status'],'ok')
            self.assertEqual(len(control['results']),8)

    def test_malformed_child_halts_unissued_children_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);wires=[]
            def send(wire):
                wires.append(wire)
                return envelope(wire,malformed=True)
            s=self.fixture(root,send)
            (root/'capacity.json').write_text(json.dumps({'max_questions':2,'max_concurrency':1}))
            args=dict(project='p',task='t',request_id='bulk',snapshot_id='v1',
                      privacy_namespace='public',items=items(),independent_items=True)
            first=s.bulk(**args)
            self.assertEqual(first['next_step'],'review-failures')
            self.assertEqual(first['batch_counts'],dict(waiting=3,pending=0,ok=0,failed=1))
            again=s.bulk(**args)
            self.assertEqual(again['batch_counts'],first['batch_counts'])
            self.assertEqual(again['model_calls_this_invocation'],0)
            self.assertEqual(len(wires),1)
            self.assertEqual(s.status()['accounted_microusd'],ENVELOPE)


if __name__=='__main__':unittest.main()
