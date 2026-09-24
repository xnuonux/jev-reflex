import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SRC = Path(__file__).resolve().parents[1] / 'src'


class PublicCLI(unittest.TestCase):
    def run_cli(self, home, *args, data=None):
        env = dict(os.environ, PYTHONPATH=str(SRC), JEV_REFLEX_HOME=str(home))
        env.pop('OPENROUTER_API_KEY', None)
        env.pop('TYPESAFE_API_KEY', None)
        env['JEV_REFLEX_PROVIDER']='openrouter'
        return subprocess.run([sys.executable, '-m', 'jev_reflex', *args],
                              input=data, capture_output=True, text=True, env=env, timeout=15)

    def test_demo_has_real_replay_and_reuse_without_provider_or_host_files(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / 'untouched'
            run = self.run_cli(home, 'demo')
            self.assertEqual(run.returncode, 0, run.stderr)
            r = json.loads(run.stdout)
            self.assertTrue(r['synthetic'])
            self.assertEqual(r['provider_calls'], 1)
            self.assertEqual(r['replay_calls'], 0)
            self.assertEqual(r['reuse_calls'], 0)
            self.assertEqual(r['pinned_context_visibility'], 'show_now')
            self.assertFalse(home.exists())

    def test_init_is_explicit_bounded_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'home'
            invalid = self.run_cli(root, 'init', '--daily-usd', 'NaN', '--enable')
            self.assertNotEqual(invalid.returncode, 0)
            self.assertFalse(root.exists())
            ok = self.run_cli(root, 'init', '--daily-usd', '2', '--enable')
            self.assertEqual(ok.returncode, 0, ok.stderr)
            policy = (root/'policy.json').read_bytes()
            self.assertEqual(json.loads(policy)['daily_limit_microusd'], 2000000)
            again = self.run_cli(root, 'init', '--daily-usd', '100', '--enable')
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual((root/'policy.json').read_bytes(), policy)

    def test_init_refuses_existing_override_instead_of_misreporting_budget(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'quota-overrides.json').write_text('{}')
            r=self.run_cli(root,'init','--daily-usd','1','--enable')
            self.assertEqual(r.returncode,2)
            self.assertEqual(json.loads(r.stdout)['reason'],'existing-quota-override-review-required')
            self.assertFalse((root/'policy.json').exists())

    def test_json_call_error_is_typed_without_echoing_input(self):
        with tempfile.TemporaryDirectory() as d:
            run = self.run_cli(d, 'call', 'batch', data='{"project":"PRIVATE_INPUT", "project":1}')
            self.assertEqual(run.returncode, 2)
            self.assertNotIn('PRIVATE_INPUT', run.stdout+run.stderr)
            self.assertEqual(json.loads(run.stdout)['reason'], 'duplicate-json-key')
            admin = self.run_cli(d, 'call', 'init', data='{}')
            self.assertNotEqual(admin.returncode, 0)

    def test_configuration_contains_no_credentials_and_does_not_write(self):
        with tempfile.TemporaryDirectory() as d:
            for client in ('mcp', 'claude', 'codex', 'opencode'):
                run = self.run_cli(Path(d)/'new', 'config', client)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertNotIn('Bearer', run.stdout)
                self.assertFalse((Path(d)/'new').exists())
            r = json.loads(self.run_cli(d, 'config', 'mcp').stdout)
            self.assertEqual(r['mcpServers']['jev-reflex']['args'], ['serve'])

    def test_doctor_is_secret_free_and_not_an_inference(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_cli(d, 'doctor')
            self.assertEqual(r.returncode, 0, r.stderr)
            value = json.loads(r.stdout)
            self.assertFalse(value['credential_available'])
            self.assertEqual(value['calls_today'], 0)
            self.assertEqual(value['status'], 'disabled-or-unavailable')

    def test_cli_large_job_does_not_hit_old_32k_limit(self):
        with tempfile.TemporaryDirectory() as d:
            key=dict(project='fixture',task='cli',request_id='job',privacy_namespace='public')
            payload=dict(**key,snapshot_id='v1',independent_items=True,
                         items=[dict(id=f'i{x}',primitive='noul',text='public fixture',question='Relevant?') for x in range(10000)])
            raw=json.dumps(payload)
            self.assertGreater(len(raw),32768)
            r=self.run_cli(d,'call','bulk',data=raw)
            self.assertEqual(r.returncode,0,r.stderr)
            value=json.loads(r.stdout)
            self.assertEqual(value['total_items'],10000)
            self.assertEqual(value['model_calls_this_invocation'],0)
            r=self.run_cli(d,'call','inspect_job',data=json.dumps(key | dict(offset=9900)))
            self.assertEqual(len(json.loads(r.stdout)['items']),100)
            r=self.run_cli(d,'call','cancel_job',data=json.dumps(key))
            self.assertTrue(json.loads(r.stdout)['cancelled'])


if __name__ == '__main__':
    unittest.main()
