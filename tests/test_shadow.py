from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from jev_reflex.shadow import report
from jev_reflex.reflex import ReflexError


class ShadowTests(unittest.TestCase):
    def test_wrong_confident_label_abstention_and_unknown_are_distinct(self):
        data=dict(schema='shadow/v1',labels=['yes','no'],cases=[
            dict(id='a',route='triage',truth='yes',prediction='no',confidence=.99),
            dict(id='b',route='triage',truth='yes',prediction='yes',confidence=.99),
            dict(id='c',route='triage',truth='no',prediction=None,confidence=None),
            dict(id='d',route='triage',truth=None,prediction='yes',confidence=.99)])
        r=report(data)['routes']['triage']
        self.assertEqual(r['selective_accuracy'],.5)
        self.assertEqual(r['coverage'],2/3)
        self.assertEqual(r['unknown_truth'],1)
        self.assertEqual(r['per_class']['yes']['recall'],.5)
        self.assertEqual(r['per_class']['no']['recall'],0)
        self.assertEqual(r['confidence_bins'][-1]['accuracy'],.5)
        self.assertEqual(r['confusion']['yes']['no'],1)

    def test_unknown_and_invalid_labels_are_not_accuracy(self):
        row=dict(id='a',route='triage',truth=None,prediction=None,confidence=None)
        data=dict(schema='shadow/v1',labels=['yes','no'],cases=[row])
        self.assertIsNone(report(data)['routes']['triage']['selective_accuracy'])
        for changes in (dict(truth='other'),dict(confidence=True),dict(prediction='made-up')):
            with self.assertRaises(ReflexError):report(data | dict(cases=[row | changes]))
        with self.assertRaises(ReflexError):report(data | dict(cases=[row,row]))


if __name__=='__main__':unittest.main()
