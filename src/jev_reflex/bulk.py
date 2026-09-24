"""Resumable explicit-input jobs. No raw-input spool, background daemon or retries."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import sqlite3
import time
from .capacity import MAX_JOB_BYTES, MAX_JOB_ITEMS
from .reflex import (ReflexError, build, build_shared, connection, digest, identifier,
                     packed, require, result, strict_json)


def job_identity(project, task, request_id, privacy_namespace):
    for label in (project, task, request_id, privacy_namespace):
        identifier(label)
    return digest(['bulk/v1', project, task, privacy_namespace, request_id])


def prepare(service, project, task, request_id, snapshot_id, privacy_namespace, items,
            independent_items, shared_state=None, recipe=None):
    identity = job_identity(project, task, request_id, privacy_namespace)
    identifier(snapshot_id)
    require(independent_items is True, 'dependent-items-separate-requests')
    require(not (recipe is not None and shared_state is not None), 'bulk-kind')
    encoded = packed([items, shared_state])
    require(len(encoded.encode('utf-8')) <= MAX_JOB_BYTES, 'job-size')
    items, shared_state = strict_json(encoded)
    require(type(items) is list and 1 <= len(items) <= MAX_JOB_ITEMS, 'job-item-count')
    limits = service.capacity()
    kind = 'recipe' if recipe is not None else 'shared' if shared_state is not None else 'items'
    if kind == 'recipe':
        from .recipes import prepare as expand
        expanded = expand(recipe, privacy_namespace, True, items, max_items=MAX_JOB_ITEMS)
    else:
        expanded = items
    seen = set()
    for item in expanded:
        require(type(item) is dict, 'item')
        name = identifier(item.get('id'))
        require(name not in seen, 'duplicate-item')
        seen.add(name)

    def builder(chunk, index):
        child_id = f'b:{identity}:{index}'
        if kind == 'shared':
            return build_shared(project, task, child_id, snapshot_id, privacy_namespace,
                                shared_state, chunk, True, service.profile, limits)
        wire, bound, _, op = build(project, task, child_id, snapshot_id, chunk, service.profile, limits)
        return wire, bound, digest([project, task, privacy_namespace]), op

    # Greedy stable partition. An oversized individual item is an error, never truncated.
    chunks, batch, start = [], [], 0
    for position, item in enumerate(expanded):
        try:
            built = builder(batch + [item], len(chunks))
        except ReflexError as exc:
            if not batch or str(exc) not in ('item-count', 'request-size', 'state-question-size'):
                raise
            chunks.append((start, position, builder(batch, len(chunks))))
            start, batch = position, []
            built = builder([item], len(chunks))
        batch.append(item)
    chunks.append((start, len(expanded), built))
    if kind == 'recipe':
        rebound = []
        for i,(a,b,built) in enumerate(chunks):
            _, ctx = service._prepare_recipe(project,task,f'b:{identity}:{i}',snapshot_id,
                                             privacy_namespace,recipe,items[a:b],True,False)
            rebound.append((a,b,(built[0],ctx['bound'],built[2],built[3])))
        chunks = rebound
    plan = [dict(index=i, item_ids=[x['id'] for x in items[a:b]],
                 wire_digest=digest(built[0]), request_digest=built[1],
                 request_bytes=len(packed(built[0]).encode('utf-8')),
                 call_identity=digest(['bulk-child/v1', identity, i]))
            for i, (a,b,built) in enumerate(chunks)]
    binding = digest(dict(schema='bulk/v1', identity=identity, snapshot=snapshot_id,
                          privacy_namespace=privacy_namespace, kind=kind, recipe=recipe,
                          items=items, state=shared_state, plan=plan,
                          # Execution pace is adjustable; partition/semantic input is not.
                          packing={k:limits[k] for k in ('max_questions','max_request_bytes','max_state_question_bytes')},
                          provider=service.profile.name, model=service.profile.returned_model))
    return identity, binding, plan, chunks, items, expanded, kind, limits


def run(service, project, task, request_id, snapshot_id, privacy_namespace, items,
        independent_items, shared_state=None, recipe=None, max_batches=32):
    require(type(max_batches) is int and 1 <= max_batches <= 256, 'max-batches')
    identity, bound, plan, chunks, items, expanded, kind, limits = prepare(
        service, project, task, request_id, snapshot_id, privacy_namespace,
        items, independent_items, shared_state, recipe)
    try:
        with connection(service.path) as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT digest FROM bulk_jobs WHERE identity=?', (identity,)).fetchone()
            if old and old['digest'] != bound:
                return result('unavailable', reason='idempotency-conflict')
            cancelled = db.execute('SELECT 1 FROM bulk_cancellations WHERE identity=?',(identity,)).fetchone() is not None
            db.execute('INSERT OR IGNORE INTO bulk_jobs(identity,digest,plan,snapshot,cancelled) VALUES (?,?,?,?,?)',
                       (identity,bound,packed(plan),snapshot_id,int(cancelled)))
            db.commit()
    except sqlite3.OperationalError:
        return result('unavailable', reason='ledger-busy')

    def attempt(i):
        a,b,built = chunks[i]
        if kind == 'recipe':
            return service.recipe(project,task,f'b:{identity}:{i}',snapshot_id,privacy_namespace,
                                  recipe,items[a:b],True,False,_job=(identity,i))
        return service._call(project,task,snapshot_id,expanded[a:b],built,_job=(identity,i))

    # Skip anything already reserved, including uncertain outcomes. No paid retry.
    with connection(service.path) as db:
        todo = [i for i,p in enumerate(plan)
                if db.execute('SELECT 1 FROM calls WHERE identity=?', (p['call_identity'],)).fetchone() is None]
        cancelled = bool(db.execute('SELECT cancelled FROM bulk_jobs WHERE identity=?',(identity,)).fetchone()[0])
    previous = inspect_job(service,project,task,request_id,privacy_namespace)
    blocked = cancelled or previous['batch_counts']['pending'] or previous['batch_counts']['failed']
    remaining = iter(todo[:max_batches] if not blocked else [])
    admitted_calls, refusals, inflight = 0, [], set()
    deadline = time.monotonic() + 2  # start window; issued transports retain their own 20s deadline
    halt = False
    with ThreadPoolExecutor(max_workers=limits['max_concurrency']) as pool:
        def fill():
            while not halt and len(inflight) < limits['max_concurrency'] and time.monotonic() < deadline:
                i = next(remaining, None)
                if i is None:
                    return
                inflight.add(pool.submit(attempt, i))
        fill()
        while inflight:
            done, inflight = wait(inflight, return_when=FIRST_COMPLETED)
            for future in done:
                try:
                    receipt = future.result()
                except Exception:
                    # A local failure may be after reservation. Preserve ledger truth,
                    # suppress arbitrary input/provider prose and stop further scheduling.
                    receipt = result('unavailable', reason='bulk-worker-uncertain')
                admitted_calls += receipt.get('model_calls_this_invocation', 0) or 0
                if receipt['status'] != 'ok':
                    halt = True
                    refusals.append({k:receipt[k] for k in ('reason','retry_after_ms') if k in receipt})
            fill()
    return inspect_job(service,project,task,request_id,privacy_namespace) | dict(
        model_calls_this_invocation=admitted_calls, run_refusals=refusals,
        automatic_retries=False, execution='bounded-foreground-no-daemon')


def inspect_job(service, project, task, request_id, privacy_namespace, offset=0, limit=100):
    identity = job_identity(project,task,request_id,privacy_namespace)
    require(type(offset) is int and 0 <= offset <= MAX_JOB_ITEMS, 'page-offset')
    require(type(limit) is int and 1 <= limit <= 256, 'page-limit')
    with connection(service.path) as db:
        job = db.execute('SELECT * FROM bulk_jobs WHERE identity=?', (identity,)).fetchone()
        if job is None:
            if db.execute('SELECT 1 FROM bulk_cancellations WHERE identity=?',(identity,)).fetchone():
                return result('cancelled',job_id=identity,cancelled=True,registered=False,next_step='stop')
            return result('not-found', job_id=identity)
        plan = strict_json(job['plan'])
        rows, counts, charged, total_items = [], dict(waiting=0,pending=0,ok=0,failed=0), 0, 0
        for p in plan:
            call = db.execute('SELECT state,charge,result FROM calls WHERE identity=?',(p['call_identity'],)).fetchone()
            receipt = strict_json(call['result']) if call and call['result'] else None
            state = 'waiting' if not call else 'pending' if not receipt else 'ok' if receipt['status']=='ok' else 'failed'
            counts[state] += 1
            charged += call['charge'] if call else 0
            for name in p['item_ids']:
                if offset <= total_items < offset+limit:
                    row = dict(id=name,batch_index=p['index'],state=state)
                    if receipt and state == 'ok':
                        row['answer'] = receipt['results'][name]
                    if receipt and state == 'failed':
                        row['reason'] = receipt.get('reason','unavailable')
                    rows.append(row)
                total_items += 1
        status = ('cancelling' if counts['pending'] else 'cancelled') if job['cancelled'] else (
            'pending' if counts['pending'] else 'partial-failure' if counts['failed'] else
            'ready' if counts['waiting'] else 'ok')
        next_step = ('inspect' if counts['pending'] else 'stop') if job['cancelled'] else (
            'inspect' if counts['pending'] else 'review-failures' if counts['failed'] else
            'continue-same-input' if counts['waiting'] else 'done')
        return result(status,job_id=identity,job_digest=job['digest'],snapshot_id=job['snapshot'],
                      batch_counts=counts,total_batches=len(plan),total_items=total_items,
                      accounted_microusd=charged,items=rows,offset=offset,
                      next_offset=offset+len(rows) if offset+len(rows)<total_items else None,
                      next_step=next_step,cancelled=bool(job['cancelled']),
                      raw_input_persisted=False,revalidate_snapshot_before_use=True)


def cancel_job(service, project, task, request_id, privacy_namespace):
    identity = job_identity(project,task,request_id,privacy_namespace)
    with connection(service.path) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('INSERT OR IGNORE INTO bulk_cancellations VALUES (?)',(identity,))
        db.execute('UPDATE bulk_jobs SET cancelled=1 WHERE identity=?',(identity,))
        db.commit()
    return inspect_job(service,project,task,request_id,privacy_namespace)
