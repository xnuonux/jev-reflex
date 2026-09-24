"""Offline grouped evaluation and persistent holdout-exposure accounting."""
from .reflex import connection, digest, identifier, probability, require, result, text
from .workflows import fields, rows


def audit(service, project, privacy_namespace, recipe_revision, model, split, examples):
    for x in (project,privacy_namespace,recipe_revision): identifier(x)
    text(model,200); require(split in ('tune','holdout'),'calibration-split'); rows(examples,10000)
    scope=digest([project,privacy_namespace]); checked=[]; seen=set()
    for e in examples:
        fields(e,'family text expected probability_true')
        identifier(e['family']); text(e['text'],6000); require(type(e['expected']) is bool,'calibration-label')
        p=probability(e['probability_true']); key=digest(e['text'])
        require(key not in seen,'duplicate-example'); seen.add(key)
        assigned='holdout' if int(digest(e['family'])[:8],16)%5==0 else 'tune'
        checked.append(dict(key=key,family=digest(e['family']),assigned=assigned,p=p,y=e['expected']))
    selected=[e for e in checked if e['assigned']==split]
    require(bool(selected),'calibration-empty-split')
    contaminated=0
    with connection(service.root/'calibration.sqlite') as db:
        db.execute('CREATE TABLE IF NOT EXISTS exposure(scope TEXT,content TEXT,family TEXT,split TEXT,revision TEXT,model TEXT,PRIMARY KEY(scope,content,split,revision,model))')
        db.execute('BEGIN IMMEDIATE')
        for e in checked:
            old=db.execute('SELECT family,split,revision,model FROM exposure WHERE scope=? AND content=?',(scope,e['key'])).fetchall()
            require(all(r[0]==e['family'] for r in old),'example-family-changed')
        exposure = {}
        for e in selected:
            old=db.execute('SELECT split,revision,model FROM exposure WHERE scope=? AND (content=? OR family=?)',
                           (scope,e['key'],e['family'])).fetchall()
            exposure[e['key']] = bool(old)
        for e in selected:
            if split=='holdout' and exposure[e['key']]: contaminated+=1
            db.execute('INSERT OR IGNORE INTO exposure VALUES(?,?,?,?,?,?)',
                       (scope,e['key'],e['family'],split,recipe_revision,model))
        db.commit()
    accepted=[e for e in selected if e['p']>=.85 or e['p']<=.15]
    correct=sum((e['p']>=.85)==e['y'] for e in accepted)
    return result('ok',split=split,selected=len(selected),abstentions=len(selected)-len(accepted),
                  accepted=len(accepted),correct=correct,accepted_accuracy=correct/len(accepted) if accepted else None,
                  brier=sum((e['p']-int(e['y']))**2 for e in selected)/len(selected),
                  contaminated_examples=contaminated,fresh_holdout_in_local_ledger=split=='holdout' and contaminated==0,
                  qualification='caller-labeled-offline-only',automatic_promotion=False,
                  audit_candidates=[e['key'] for e in sorted(selected,key=lambda e:(abs(e['p']-.5),e['key']))[:5]],
                  provider_calls=0)
