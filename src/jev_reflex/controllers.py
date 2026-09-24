"""Durable advisory stream filtering over locally recorded raw Jev results."""
from .reflex import connection, digest, identifier, packed, require, result, strict_json, signal_contract

DEFAULT_POLICY = dict(confirmations=2, max_hold_sources=2, override_sources=4)
KEYS = ('project', 'task', 'privacy_namespace', 'controller_id')


def _key(project, task, privacy_namespace, controller_id):
    return digest([identifier(x) for x in (project, task, privacy_namespace, controller_id)])


def _integer(x, maximum=9007199254740991):
    require(type(x) is int and 0 <= x <= maximum, 'controller-integer')
    return x


def _view(state, **extra):
    return result('ok', schema='controller/v1', controller=state,
                  model_calls_this_invocation=0, revalidate_snapshot_before_use=True, **extra)


def _read(db, key):
    row = db.execute('SELECT state FROM controllers WHERE identity=?', (key,)).fetchone()
    require(row is not None, 'controller-missing')
    return strict_json(row['state'])


def _clear(s):
    s.update(selected_id=None, supported_snapshot=None, supported_epoch=None,
             selection_origin=None, supporting_evidence=None, confirmation_evidence=[],
             challenger=None, override_epoch=None)


def open_controller(service, project, task, privacy_namespace, controller_id,
                    snapshot_id, signal, policy=None):
    key = _key(project, task, privacy_namespace, controller_id)
    identifier(snapshot_id)
    signal = signal_contract(signal)
    primitive = signal['primitive']
    options = sorted(signal['choices']) if primitive == 'choice' else ['false', 'true']
    signal_hash = digest(signal)
    if policy is None:
        policy = DEFAULT_POLICY.copy()
    require(type(policy) is dict and set(policy) == set(DEFAULT_POLICY), 'controller-policy')
    policy = dict(policy)
    require(1 <= _integer(policy['confirmations'], 8), 'controller-confirmations')
    _integer(policy['max_hold_sources'], 32)
    _integer(policy['override_sources'], 32)
    contract = digest(dict(snapshot_id=snapshot_id, signal_digest=signal_hash, policy=policy))
    with connection(service.path) as db:
        db.execute('BEGIN IMMEDIATE')
        old = db.execute('SELECT contract FROM controllers WHERE identity=?', (key,)).fetchone()
        if old:
            require(old['contract'] == contract, 'controller-contract-conflict')
            return _view(_read(db, key), replayed=True)
        state = dict(revision=0, phase='active', snapshot_id=snapshot_id, source_epoch=0,
                     primitive=primitive, options=options, signal_digest=signal_hash, policy=policy, voted=False,
                     last_evidence=None, reason='awaiting-evidence')
        _clear(state)
        db.execute('INSERT INTO controllers VALUES (?,?,?)', (key, contract, packed(state)))
        db.execute('INSERT INTO controller_snapshots VALUES (?,?)', (key, digest(snapshot_id)))
        db.commit()
    return _view(state, replayed=False)


def inspect(service, project, task, privacy_namespace, controller_id):
    key = _key(project, task, privacy_namespace, controller_id)
    with connection(service.path) as db:
        return _view(_read(db, key))


def _answer(db, s, project, task, namespace, ref):
    require(type(ref) is dict and set(ref) == {'kind', 'request_id', 'item_id'}, 'controller-receipt-fields')
    require(ref['kind'] in ('batch', 'shared'), 'controller-receipt-kind')
    request = identifier(ref['request_id'])
    item = identifier(ref['item_id'])
    identity = digest([project, task, request] if ref['kind'] == 'batch' else
                      [project, task, namespace, 'shared', request])
    row = db.execute('SELECT state,result,digest FROM calls WHERE identity=?', (identity,)).fetchone()
    require(row is not None and row['state'] == 'settled' and row['result'], 'controller-receipt-unsettled')
    receipt = strict_json(row['result'])
    require(receipt['status'] == 'ok' and 'recipe_version' not in receipt, 'controller-raw-success-required')
    require(receipt['snapshot_id'] == s['snapshot_id'], 'controller-stale-snapshot')
    require(item in receipt['results'], 'controller-receipt-item')
    require(receipt.get('signal_digests', {}).get(item) == s['signal_digest'], 'controller-signal-mismatch')
    a = receipt['results'][item]
    if s['primitive'] == 'choice':
        require('probabilities' in a and sorted(a['probabilities']) == s['options'], 'controller-vocabulary')
        choice = a['selected_id']
    else:
        require('probability_true' in a, 'controller-vocabulary')
        choice = None if a['value'] is None else ('true' if a['value'] else 'false')
    evidence = dict(request_digest=row['digest'], item_id=item, snapshot_id=receipt['snapshot_id'],
                    provider_route=receipt['provider_route'], returned_model=receipt['returned_model'],
                    evidence_origin=receipt.get('evidence_origin', 'legacy-unlabelled'),
                    status=a['status'])
    return choice if a['status'] == 'proposal' else None, evidence


def event(service, project, task, privacy_namespace, controller_id, event_id,
          expected_revision, event):
    key = _key(project, task, privacy_namespace, controller_id)
    identifier(event_id)
    _integer(expected_revision)
    require(type(event) is dict, 'controller-event')
    kind = event.get('kind')
    fields = {'bind': {'snapshot_id'}, 'observe': {'receipt'}, 'override': {'selected_id'},
              'release': set(), 'pause': set(), 'resume': set(), 'stop': set()}
    require(type(kind) is str and kind in fields, 'controller-event-kind')
    require(set(event) == {'kind'} | fields[kind], 'controller-event-fields')
    # Copy nested JSON once; strict JSON public transports reject duplicates/non-finite values.
    event = strict_json(packed(event))
    bound = digest([expected_revision, event])
    with connection(service.path) as db:
        db.execute('BEGIN IMMEDIATE')
        s = _read(db, key)
        prior = db.execute('SELECT digest FROM controller_events WHERE identity=? AND event_id=?',
                           (key, event_id)).fetchone()
        if prior:
            require(prior['digest'] == bound, 'controller-event-conflict')
            return _view(s, replayed=True)
        require(s['phase'] != 'stopped' or kind == 'stop', 'controller-stopped')
        if kind not in ('pause', 'stop'):
            require(s['revision'] == expected_revision, 'controller-revision-conflict')
        if kind in ('pause', 'stop'):
            _clear(s)
            # Invalidate even an unobserved source: a pre-pause in-flight result
            # must not land after resume just because it never voted previously.
            s.update(phase='stopped' if kind == 'stop' else 'paused', reason=kind, voted=True)
        elif kind == 'resume':
            require(s['phase'] == 'paused', 'controller-not-paused')
            _clear(s)
            s.update(phase='active', reason='awaiting-new-snapshot' if s['voted'] else 'awaiting-evidence')
        else:
            require(s['phase'] == 'active', 'controller-not-active')
            if kind == 'bind':
                snap = identifier(event['snapshot_id'])
                seen = db.execute('SELECT 1 FROM controller_snapshots WHERE identity=? AND snapshot=?',
                                  (key, digest(snap))).fetchone()
                require(seen is None, 'controller-snapshot-reused')
                db.execute('INSERT INTO controller_snapshots VALUES (?,?)', (key, digest(snap)))
                if not s['voted']:
                    s['challenger'] = None
                s.update(snapshot_id=snap, source_epoch=s['source_epoch']+1, voted=False,
                         reason='awaiting-evidence')
                anchor = s['override_epoch'] if s['override_epoch'] is not None else s['supported_epoch']
                limit = s['policy']['override_sources'] if s['override_epoch'] is not None else s['policy']['max_hold_sources']
                if anchor is not None and s['source_epoch'] - anchor > limit:
                    _clear(s)
                    s['reason'] = 'hint-expired'
                elif s['override_epoch'] is not None:
                    s['reason'] = 'caller-override'
            elif kind == 'override':
                selected = identifier(event['selected_id'])
                require(selected in s['options'], 'controller-option')
                _clear(s)
                s.update(selected_id=selected, supported_snapshot=s['snapshot_id'],
                         supported_epoch=s['source_epoch'], override_epoch=s['source_epoch'],
                         selection_origin='caller-override', reason='caller-override')
            elif kind == 'release':
                _clear(s)
                s['reason'] = 'awaiting-new-snapshot' if s['voted'] else 'awaiting-evidence'
            elif kind == 'observe':
                require(not s['voted'], 'controller-source-already-observed')
                choice, evidence = _answer(db, s, project, task, privacy_namespace, event['receipt'])
                s.update(voted=True, last_evidence=evidence)
                if s['override_epoch'] is not None:
                    s['reason'] = 'caller-override'
                elif choice is None:
                    s.update(challenger=None, reason='abstained-held' if s['selected_id'] else 'abstained')
                elif choice == s['selected_id'] or s['selected_id'] is None:
                    s.update(selected_id=choice, supported_snapshot=s['snapshot_id'],
                             supported_epoch=s['source_epoch'], challenger=None,
                             supporting_evidence=evidence,
                             confirmation_evidence=[evidence],
                             selection_origin='recorded-jev-result', reason='supported')
                else:
                    previous = s['challenger']
                    votes = previous['votes']+1 if (previous and previous['selected_id'] == choice
                            and previous['source_epoch'] == s['source_epoch']-1) else 1
                    confirmations = (previous['evidence'] if votes > 1 else []) + [evidence]
                    s['challenger'] = dict(selected_id=choice, votes=votes, source_epoch=s['source_epoch'],
                                          evidence=confirmations)
                    s['reason'] = 'challenger-pending'
                    if votes >= s['policy']['confirmations']:
                        s.update(selected_id=choice, supported_snapshot=s['snapshot_id'],
                                 supported_epoch=s['source_epoch'], challenger=None,
                                 supporting_evidence=evidence,
                                 confirmation_evidence=confirmations,
                                 selection_origin='recorded-jev-result', reason='switched')
        s['revision'] += 1
        db.execute('UPDATE controllers SET state=? WHERE identity=?', (packed(s), key))
        db.execute('INSERT INTO controller_events VALUES (?,?,?)', (key, event_id, bound))
        db.commit()
    return _view(s, replayed=False)
