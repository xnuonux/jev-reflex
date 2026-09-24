import copy
from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from jev_reflex.reflex import Service, DEFAULT_POLICY, ENVELOPE, ReflexError, build, validate_response
from jev_reflex.providers import OPENROUTER, TYPESAFE

ITEMS = [dict(id='x',primitive='noul',text='A compiler error.',question='Is this a code error?')]


class ProviderTests(unittest.TestCase):
    def test_request_model_change_also_rebinds_generic_wire(self):
        original=build('p','t','r','s',ITEMS,OPENROUTER)
        moved=build('p','t','r','s',ITEMS,replace(OPENROUTER,request_model='typesafe/jev-new-request-pin'))
        self.assertNotEqual(original[0]['model'],moved[0]['model'])
        self.assertNotEqual(original[1],moved[1])
        self.assertEqual(original[3],moved[3])  # Same operation identity now conflicts.

    def test_extreme_billing_stops_durably_without_overflow_or_zero_charge(self):
        for cost in (1e20, 10**400, -1, True, float('inf')):
            with self.subTest(cost=str(cost)[:20]), tempfile.TemporaryDirectory() as d:
                root=Path(d)
                (root/'policy.json').write_text(json.dumps(DEFAULT_POLICY|{'enabled':True,'daily_limit_microusd':100000}))
                s=Service(root,transport=lambda w: {'usage':{'cost':cost}})
                r=s.judge('p','t','r','s',ITEMS)
                self.assertEqual(r['reason'],'cost-out-of-range')
                self.assertEqual(r['accounted_microusd'],ENVELOPE)
                self.assertIsNone(r['reported_microusd'])
                self.assertTrue(s.status()['accounting_stop'])
                self.assertTrue(s.judge('p','t','r','s',ITEMS)['replayed'])

    def test_threshold_change_rebinds_generic_idempotency(self):
        def response(w):
            return dict(model=OPENROUTER.returned_model,provider='TypeSafe',id='fixture',
                        answers={'q0':{'type':'noul','noul':.9}},usage={'cost':.00001})
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'policy.json').write_text(json.dumps(DEFAULT_POLICY|{'enabled':True,'daily_limit_microusd':100000}))
            s=Service(root,transport=response)
            self.assertEqual(s.judge('p','t','r','s',ITEMS)['results']['x']['status'],'proposal')
            with patch('jev_reflex.reflex.NOUL_HIGH',.95):
                self.assertEqual(s.judge('p','t','r','s',ITEMS)['reason'],'idempotency-conflict')
                self.assertEqual(s.judge('p','t','new','s',ITEMS)['results']['x']['status'],'abstain')

    def test_direct_typesafe_uses_native_envelope_without_invented_cost_or_generation(self):
        wires=[]
        def direct(wire):
            wires.append(wire)
            return dict(model='jev-1.13.0', answers={'q0':{'type':'noul','noul':.95}},
                        usage={'input_tokens':120,'output_tokens':5})
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'policy.json').write_text(json.dumps(DEFAULT_POLICY|{'enabled':True,'daily_limit_microusd':100000}))
            s=Service(root,transport=direct,profile=TYPESAFE)
            r=s.judge('p','t','r','s',ITEMS)
            self.assertEqual(r['status'],'ok')
            self.assertEqual(wires[0]['model'],'jev-1.13.0')
            self.assertIsNone(r['generation_id_sha256'])
            self.assertIsNone(r['reported_microusd'])
            self.assertEqual(r['accounted_microusd'], ENVELOPE)
            self.assertEqual(r['usage_tokens'],{'input_tokens':120,'output_tokens':5})
            self.assertEqual(r['cost_basis'],'conservative-reservation')
            self.assertEqual(s.status()['unreported_cost_calls_today'],1)
            self.assertEqual(s.status()['reported_cost_calls_today'],0)
            self.assertEqual(s.status()['reported_cost_basis'],'sum-of-known-reports-only')
            self.assertTrue(s.judge('p','t','r','s',ITEMS)['replayed'])
            self.assertEqual(len(wires),1)
            other=Service(root,transport=direct,profile=OPENROUTER)
            self.assertEqual(other.judge('p','t','r','s',ITEMS)['reason'],'idempotency-conflict')

    def test_direct_rejects_alias_model_extra_billing_and_malformed_usage(self):
        wire=build('p','t','r','s',ITEMS,TYPESAFE)[0]
        valid=dict(model='jev-1.13.0',answers={'q0':{'type':'noul','noul':.9}},usage={'input_tokens':10,'output_tokens':2})
        for field,value in [('model','jev-latest'),('usage',{'input_tokens':True,'output_tokens':2}),
                            ('usage',{'input_tokens':10,'output_tokens':2,'cost':0})]:
            with self.assertRaises(ReflexError):
                validate_response(valid|{field:value},wire,ITEMS,TYPESAFE)

    def test_unrecognized_provider_refuses_before_state_creation(self):
        with tempfile.TemporaryDirectory() as d, patch.dict('os.environ',{'JEV_REFLEX_PROVIDER':'evil'}):
            path=Path(d)/'absent'
            with self.assertRaises(ReflexError): Service(path)
            self.assertFalse(path.exists())


if __name__ == '__main__': unittest.main()
