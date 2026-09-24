"""Explicit local source retention; no arbitrary paths or automatic uploads."""
import hashlib
import re
import sqlite3
from contextlib import closing
from .reflex import connection, digest, identifier, require, result, text


def db_for(service):
    db = connection(service.root/'artifacts.sqlite')
    return db


def put(service, project, privacy_namespace, content):
    identifier(project); identifier(privacy_namespace); text(content,1048576)
    data=content.encode('utf-8'); sha=hashlib.sha256(data).hexdigest(); scope=digest([project,privacy_namespace])
    with db_for(service) as db:
        db.execute('CREATE TABLE IF NOT EXISTS artifacts(scope TEXT,sha TEXT,content BLOB,PRIMARY KEY(scope,sha))')
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT content FROM artifacts WHERE scope=? AND sha=?',(scope,sha)).fetchone()
        require(old is None or bytes(old[0])==data,'artifact-corrupt')
        db.execute('INSERT OR IGNORE INTO artifacts VALUES(?,?,?)',(scope,sha,data)); db.commit()
    return result('ok',artifact_id=sha,utf8_bytes=len(data),storage='local-plaintext-explicit-opt-in',provider_calls=0)


def get(service, project, privacy_namespace, artifact_id, start=0, length=6000):
    identifier(project); identifier(privacy_namespace)
    require(type(artifact_id) is str and bool(re.fullmatch('[a-f0-9]{64}',artifact_id)),'artifact-id')
    require(type(start) is int and start>=0 and type(length) is int and 1<=length<=16000,'artifact-range')
    path=service.root/'artifacts.sqlite'
    require(path.is_file(),'artifact-not-found')
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        exists=db.execute("SELECT name FROM sqlite_master WHERE name='artifacts'").fetchone()
        row=db.execute('SELECT content FROM artifacts WHERE scope=? AND sha=?',
                       (digest([project,privacy_namespace]),artifact_id)).fetchone() if exists else None
    require(row is not None,'artifact-not-found')
    data=bytes(row[0]); require(hashlib.sha256(data).hexdigest()==artifact_id,'artifact-corrupt')
    content=data.decode('utf-8'); require(start<=len(content),'artifact-range')
    end=min(start+length,len(content))
    return result('ok',artifact_id=artifact_id,content=content[start:end],start=start,end=end,
                  total_characters=len(content),offset_unit='unicode-codepoints',provider_calls=0)
