import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from jev_reflex.evaluation import compare
from jev_reflex import ReflexError


def fixture():
    row=dict(case_id='a',input_sha256='a'*64,correct=True,important_missed=False,
             abstained=False,duration_ms=100,cost_microusd=None,input_tokens=100,output_tokens=5)
    return dict(schema='jev-reflex-paired/v1',synthetic=True,baseline=[row],candidate=[row|{'duration_ms':60,'correct':False}])


class EvaluationTests(unittest.TestCase):
    def test_tradeoff_and_unknown_cost_remain_visible(self):
        r=compare(fixture())
        self.assertEqual(r['metrics']['duration_ms']['candidate_minus_baseline_mean'],-40)
        self.assertEqual(r['metrics']['correct']['candidate_minus_baseline_mean'],-1)
        self.assertIsNone(r['metrics']['cost_microusd']['candidate_mean'])
        self.assertEqual(r['metrics']['cost_microusd']['paired_unknown'],1)
        self.assertFalse(r['causal_claim'])

    def test_substituted_populations_duplicates_and_nonfinite_refuse(self):
        for field,value in [('case_id','b'),('input_sha256','b'*64),('duration_ms',float('nan')),
                            ('cost_microusd',True),('correct',1)]:
            d=fixture();d['candidate'][0][field]=value
            with self.assertRaises(ReflexError):compare(d)
        d=fixture();d['candidate'].append(d['candidate'][0])
        with self.assertRaises(ReflexError):compare(d)


if __name__ == '__main__':unittest.main()
