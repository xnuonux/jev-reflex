"""One fixed-endpoint request. Parent enforces the wall deadline. No retries."""
import json
import os
import sys
from urllib.error import HTTPError
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def main():
    wire = sys.stdin.buffer.read(60001)
    if len(wire) > 60000:
        return 1
    profile = sys.argv[1] if len(sys.argv) == 2 else 'openrouter'
    profiles = {'openrouter': ('https://openrouter.ai/api/alpha/decisions', 'OPENROUTER_API_KEY'),
                'typesafe': ('https://api.typesafe.ai/v1/systemone', 'TYPESAFE_API_KEY')}
    if profile not in profiles:
        return 1
    endpoint, key_variable = profiles[profile]
    key = os.environ.get(key_variable)
    if not key:
        return 1
    req = Request(endpoint, data=wire,
                  headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    try:
        with build_opener(NoRedirect(), ProxyHandler({})).open(req, timeout=15) as response:
            data = response.read(4194305)
        if len(data) > 4194304:
            return 1
        sys.stdout.buffer.write(data)
        return 0
    except HTTPError as exc:
        # Never persist provider bodies, headers, URLs, or exception prose.
        sys.stdout.buffer.write(json.dumps({'http_status': exc.code}).encode('ascii'))
        return 2
    except Exception:
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
