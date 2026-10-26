from __future__ import annotations

from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path
import sqlite3
import json
from functools import lru_cache
import uuid

SCHEMA_VERSION = 1
NAMESPACE = uuid.UUID('537527d5-3e5a-4f96-b0a2-f47607cdb05c')


def stable_id(*parts: object) -> str:
    # Length prefixes avoid ambiguous concatenations.
    return str(uuid.uuid5(NAMESPACE, ''.join(f'{len(str(p))}:{p}' for p in parts)))


@lru_cache(maxsize=1)
def _normalization():
    return json.loads(files('hui_indexer').joinpath('assets/normalization.json').read_text())['replacements']


def normalize(text: str) -> str:
    replacements = _normalization()
    return ''.join(replacements.get(str(ord(c)),c) for c in text)


def connect(path: str | Path, *, readonly: bool = False) -> sqlite3.Connection:
    path = Path(path).resolve()
    if not readonly:
        path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path.as_uri() + '?mode=ro' if readonly else str(path), uri=readonly)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=5000')
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version > SCHEMA_VERSION or (readonly and version != SCHEMA_VERSION):
        db.close()
        raise ValueError(f'Unsupported HUI schema: {version}')
    if version == 0 and not readonly:
        sql = files('hui_indexer').joinpath('migrations/001_initial.sql').read_text(encoding='utf-8')
        try:
            db.executescript('BEGIN IMMEDIATE;\n' + sql + '\nCOMMIT;')
        except Exception:
            db.rollback()
            db.close()
            raise
    return db


@contextmanager
def transaction(db: sqlite3.Connection):
    # Savepoints support atomic operations inside a page or proposal batch.
    name = 'hui_' + uuid.uuid4().hex
    db.execute(f'SAVEPOINT {name}')
    try:
        yield
        db.execute(f'RELEASE SAVEPOINT {name}')
    except BaseException:
        db.execute(f'ROLLBACK TO SAVEPOINT {name}')
        db.execute(f'RELEASE SAVEPOINT {name}')
        raise


def integrity(db: sqlite3.Connection) -> None:
    if [r[0] for r in db.execute('PRAGMA integrity_check')] != ['ok']:
        raise ValueError('SQLite integrity check failed')
    if db.execute('PRAGMA foreign_key_check').fetchone():
        raise ValueError('Orphaned foreign key')
