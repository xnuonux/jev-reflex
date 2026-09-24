"""Portable local controls. Administrative setup is never exposed as an MCP tool."""
import argparse
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import sqlite3
import sys
from .api import METHODS, invoke
from .reflex import DEFAULT_POLICY, ROOT, ReflexError, Service, require, strict_json
from .capacity import MAX_JOB_BYTES


def emit(value):
    print(json.dumps(value, ensure_ascii=True, allow_nan=False, indent=2))


def configuration(client):
    command = 'jev-reflex'
    if client == 'codex':
        return '[mcp_servers.jev-reflex]\ncommand = "jev-reflex"\nargs = ["serve"]\nenv_vars = ["OPENROUTER_API_KEY", "TYPESAFE_API_KEY", "JEV_REFLEX_PROVIDER", "JEV_REFLEX_HOME"]\n'
    if client == 'opencode':
        return {'mcp': {'jev-reflex': {'type': 'local', 'command': [command, 'serve'], 'enabled': True}}}
    return {'mcpServers': {'jev-reflex': {'command': command, 'args': ['serve']}}}


def initialize(root, daily_usd, enabled):
    try:
        amount = Decimal(daily_usd)
        require(amount.is_finite() and 0 <= amount <= 100, 'daily-budget')
        micro = amount * 1000000
        require(micro == micro.to_integral_value(), 'daily-budget-precision')
    except InvalidOperation:
        raise ReflexError('daily-budget') from None
    policy = DEFAULT_POLICY | {'enabled': enabled, 'daily_limit_microusd': int(micro)}
    require(not (root/'quota-overrides.json').exists(), 'existing-quota-override-review-required')
    root.mkdir(parents=True, exist_ok=True)
    # Exclusive create, never truncate an existing policy or erase accounting.
    try:
        fd = os.open(root/'policy.json', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ReflexError('policy-already-exists') from None
    with os.fdopen(fd, 'w', encoding='utf-8') as handle:
        json.dump(policy, handle, indent=2)
        handle.write('\n')
    return dict(status='configured', **policy, authority='host-configuration',
                credentials_written=False, ledger_reset=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Jev Reflex: small decisions, host-owned actions.')
    parser.add_argument('--version', action='version', version='jev-reflex 0.5.0')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('serve', help='Start stdio MCP; install the [mcp] extra.')
    sub.add_parser('doctor', help='Local readiness/accounting only; no inference.')
    sub.add_parser('demo', help='Offline synthetic replay, reuse and context-pin demonstration.')
    sub.add_parser('controller-demo', help='Offline stateful vs stateless trace; no inference.')
    sub.add_parser('catalog', help='List versioned recipes and their boundaries.')
    sub.add_parser('evaluate', help='Compare paired workflow measurements from JSON stdin; no inference.')
    sub.add_parser('shadow-report', help='Offline confusion matrices for labelled semantic decisions.')
    call = sub.add_parser('call', help='Call one operation with JSON arguments on stdin.')
    call.add_argument('method', choices=list(METHODS))
    init = sub.add_parser('init', help='Create a host-owned policy; never overwrite.')
    init.add_argument('--daily-usd', required=True)
    init.add_argument('--enable', action='store_true')
    config = sub.add_parser('config', help='Print client config; never modify it.')
    config.add_argument('client', choices=['mcp', 'claude', 'codex', 'opencode'])
    args = parser.parse_args(argv)
    try:
        if args.command == 'config':
            value = configuration(args.client)
            print(value) if type(value) is str else emit(value)
        elif args.command == 'init':
            emit(initialize(ROOT, args.daily_usd, args.enable))
        elif args.command == 'controller-demo':
            from .controller_demo import run
            emit(run())
        elif args.command == 'demo':
            from .demo import run
            emit(run())
        elif args.command == 'catalog':
            from .recipes import RECIPE_VERSIONS
            emit(dict(recipes=list(RECIPE_VERSIONS), authority='none', score_supported=False))
        elif args.command == 'serve':
            try:
                from .server import make_server
            except ImportError:
                raise ReflexError('mcp-extra-required') from None
            make_server().run(transport='stdio')
        elif args.command == 'evaluate':
            from .evaluation import compare
            data = sys.stdin.buffer.read(8388609)
            require(len(data) <= 8388608, 'evaluation-size')
            emit(compare(strict_json(data.decode('utf-8'))))
        elif args.command == 'shadow-report':
            from .shadow import report
            data = sys.stdin.buffer.read(MAX_JOB_BYTES+1)
            require(len(data) <= MAX_JOB_BYTES, 'evaluation-size')
            emit(report(strict_json(data.decode('utf-8'))))
        elif args.command == 'call':
            data = sys.stdin.buffer.read(MAX_JOB_BYTES+1)
            require(len(data) <= MAX_JOB_BYTES, 'arguments-size')
            arguments = strict_json(data.decode('utf-8'))
            emit(invoke(Service(), args.method, arguments))
        else:
            emit(Service().status())
        return 0
    except (ReflexError, ValueError, UnicodeError, OSError, sqlite3.Error) as exc:
        code = str(exc) if isinstance(exc, ReflexError) else 'local-input-or-state-error'
        emit(dict(status='error', reason=code, authority='none', may_execute=False))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
