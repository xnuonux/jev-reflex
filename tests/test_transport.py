import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from jev_reflex import transport
from jev_reflex.providers import OPENROUTER, TYPESAFE


class TransportTests(unittest.TestCase):
    def test_subprocess_route_map_matches_profile_and_uses_only_selected_key(self):
        for profile in (OPENROUTER,TYPESAFE):
            output=io.BytesIO()
            with patch.object(transport.sys,'stdin',SimpleNamespace(buffer=io.BytesIO(b'{}'))), \
                 patch.object(transport.sys,'stdout',SimpleNamespace(buffer=output)), \
                 patch.object(transport.sys,'argv',['transport.py',profile.name]), \
                 patch.dict(transport.os.environ,{profile.key_variable:'fixture-key'},clear=True), \
                 patch.object(transport,'build_opener') as opener:
                opener.return_value.open.return_value=io.BytesIO(b'{}')
                self.assertEqual(transport.main(),0)
                req=opener.return_value.open.call_args.args[0]
                self.assertEqual(req.full_url,profile.endpoint)
                self.assertEqual(req.get_header('Authorization'),'Bearer fixture-key')
                self.assertEqual(output.getvalue(),b'{}')

    def test_http_error_emits_status_only_without_body_or_headers(self):
        for status in (402, 429, 503):
            output=io.BytesIO()
            failure=HTTPError('https://example.invalid/secret-url',status,'secret-prose',
                              {'Authorization':'secret-header'},io.BytesIO(b'secret-body'))
            with patch.object(transport.sys,'stdin',SimpleNamespace(buffer=io.BytesIO(b'{}'))), \
                 patch.object(transport.sys,'stdout',SimpleNamespace(buffer=output)), \
                 patch.dict(transport.os.environ,{'OPENROUTER_API_KEY':'secret-key'}), \
                 patch.object(transport,'build_opener') as opener:
                opener.return_value.open.side_effect=failure
                self.assertEqual(transport.main(),2)
            self.assertEqual(json.loads(output.getvalue()),{'http_status':status})
            self.assertNotIn(b'secret',output.getvalue())
            failure.close()


if __name__=='__main__':unittest.main()
