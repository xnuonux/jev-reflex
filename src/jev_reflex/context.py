"""Source-bound context planning without reading, deleting, or uploading files implicitly."""
import hashlib
from .reflex import digest, identifier, require, text


def plan(service, project, task, request_id, privacy_namespace, goal, chunks, reuse_success=False):
    identifier(privacy_namespace)
    text(goal, 1000)
    require(type(chunks) is list and 1 <= len(chunks) <= 8, 'chunk-count')
    normalized, seen = [], set()
    for chunk in chunks:
        require(type(chunk) is dict and set(chunk) == {'id','text','source_ref','mandatory_pinned'}, 'chunk-fields')
        item_id = identifier(chunk['id'])
        require(item_id not in seen, 'duplicate-item')
        seen.add(item_id)
        require(type(chunk['mandatory_pinned']) is bool, 'mandatory-pinned')
        normalized.append(dict(id=item_id, text=text(chunk['text'],6000),
                               source_ref=text(chunk['source_ref'],1000), mandatory_pinned=chunk['mandatory_pinned']))
    snapshot = 'sha256:' + digest({'goal': goal, 'chunks': normalized})
    receipt = service.recipe(project,task,request_id,snapshot,privacy_namespace,'context_triage/v1',
                             [dict(id=c['id'],text=c['text'],privacy_namespace=privacy_namespace,
                                   goal=goal,mandatory_pinned=c['mandatory_pinned']) for c in normalized],
                             True,reuse_success)
    plan_rows = []
    for chunk in normalized:
        answer = receipt.get('results',{}).get(chunk['id'],{})
        advice = answer.get('advice',{})
        # Unavailable/abstaining decisions preserve visibility, never guess a reduction.
        show = advice.get('visibility','show_now') == 'show_now' or chunk['mandatory_pinned']
        plan_rows.append(dict(id=chunk['id'], source_ref=chunk['source_ref'],
                              source_sha256=hashlib.sha256(chunk['text'].encode('utf-8')).hexdigest(), utf8_bytes=len(chunk['text'].encode('utf-8')),
                              visibility='show_now' if show else 'collapse_recoverably',
                              retain_source=True, mandatory_pinned=chunk['mandatory_pinned']))
    return dict(receipt, context_plan=plan_rows, automatic_context_change=False,
                complete_input_snapshot=snapshot, input_utf8_bytes=sum(x['utf8_bytes'] for x in plan_rows),
                suggested_visible_utf8_bytes=sum(x['utf8_bytes'] for x in plan_rows if x['visibility']=='show_now'),
                source_verification='hashes supplied text, not external file authenticity',
                caller_must_retain_originals=True)
