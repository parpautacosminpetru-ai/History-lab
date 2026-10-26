"""HUI v1: stored ZIP, checksummed files, staged atomic installation."""
from __future__ import annotations

from importlib.resources import files
import json
import re
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import stat
import tempfile
import uuid
import zipfile

from .db import connect, integrity, SCHEMA_VERSION
from .ingestion import sha256
from .semantics import validate

MAX_FILES = 50000
MAX_BYTES = 2 * 1024**3


def safe_path(name: str) -> str:
    if not re.fullmatch(r'[A-Za-z0-9/_.-]+',name) or name.startswith('/'):
        raise ValueError('Unsafe package path')
    path = PurePosixPath(name)
    if any(p in ('','.','..') for p in name.split('/')) or str(path)!=name:
        raise ValueError('Unsafe package path')
    if name not in ('catalog.sqlite','manifest.json') and not name.startswith(('originals/','pages/')):
        raise ValueError('Unexpected package path')
    return name


def schema_fingerprint(db):
    return [tuple(row) for row in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")]


def validate_catalog(db):
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version != SCHEMA_VERSION:
        raise ValueError(f'Incompatible schema {version}')
    reference = sqlite3.connect(':memory:')
    try:
        reference.executescript(files('hui_indexer').joinpath('migrations/001_initial.sql').read_text(encoding='utf-8'))
        if schema_fingerprint(db)!=schema_fingerprint(reference):
            raise ValueError('Unrecognized SQLite schema, views or triggers')
    finally:
        reference.close()
    integrity(db)
    problems = validate(db)
    if problems:
        raise ValueError('; '.join(problems))
    if not db.execute('SELECT 1 FROM IndexVersions').fetchone():
        raise ValueError('No published index version')
    if db.execute("SELECT 1 FROM SourceEditions WHERE status!='ready'").fetchone():
        raise ValueError('Incomplete extraction')
    for table,column in (('SourceEditions','original_path'),('Pages','image_path')):
        for row in db.execute(f'SELECT {column} FROM {table} WHERE {column} IS NOT NULL'):
            safe_path(row[0])


def export_package(db, workspace: Path, output: Path, *, include_originals=False,
                   rights_confirmed=False):
    workspace, output = Path(workspace).resolve(), Path(output).resolve()
    if include_originals and not rights_confirmed:
        raise ValueError('Explicit distribution permission is required for PDFs and page images')
    output.parent.mkdir(parents=True,exist_ok=True)
    temp_output = output.with_name(output.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with tempfile.TemporaryDirectory(prefix='hui-export-') as temp:
            snapshot_path = Path(temp)/'catalog.sqlite'
            snapshot = sqlite3.connect(snapshot_path)
            try:
                db.backup(snapshot)
            finally:
                snapshot.close()
            snapshot = connect(snapshot_path,readonly=True)
            try:
                validate_catalog(snapshot)
                paths = {'catalog.sqlite':snapshot_path}
                if include_originals:
                    for row in snapshot.execute('SELECT original_path,sha256 FROM SourceEditions'):
                        path = workspace/safe_path(row['original_path'])
                        if path.is_symlink() or not path.is_file() or sha256(path)!=row['sha256']:
                            raise ValueError('Original PDF missing or changed')
                        paths[row['original_path']] = path
                    for row in snapshot.execute('SELECT image_path FROM Pages WHERE image_path IS NOT NULL'):
                        path = workspace/safe_path(row[0])
                        if path.is_symlink() or not path.is_file():
                            raise ValueError('Original page image missing')
                        paths[row[0]] = path
                version = snapshot.execute('SELECT max(id) FROM IndexVersions').fetchone()[0]
                manifest = {'format':'hui','format_version':1,'schema_version':SCHEMA_VERSION,
                            'index_version':version,'includes_originals':include_originals,
                            'files':{name:{'sha256':sha256(path),'size':path.stat().st_size} for name,path in sorted(paths.items())}}
                encoded_manifest=json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)
                if len(encoded_manifest.encode('utf-8'))>4*1024**2:
                    raise ValueError('Manifest exceeds HUI v1 safety limits')
                if len(paths)+1>MAX_FILES or sum(p.stat().st_size for p in paths.values())>MAX_BYTES:
                    raise ValueError('Package exceeds HUI v1 safety limits')
                with zipfile.ZipFile(temp_output,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
                    for name,path in sorted(paths.items()):
                        archive.write(path,name)
                    archive.writestr('manifest.json',encoded_manifest)
            finally:
                snapshot.close()
        temp_output.replace(output)
        return manifest
    finally:
        temp_output.unlink(missing_ok=True)


def verify_package(package: Path, destination: Path):
    """Only writes inside a new staging directory supplied by the caller."""
    with zipfile.ZipFile(package) as archive:
        entries = archive.infolist()
        if len(entries)>MAX_FILES or sum(e.file_size for e in entries)>MAX_BYTES:
            raise ValueError('Package exceeds safety limits')
        names,portable_names = set(),set()
        for entry in entries:
            safe_path(entry.filename)
            mode = (entry.external_attr>>16)&0xffff
            if entry.filename.casefold() in portable_names or entry.is_dir() or stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0,stat.S_IFREG)):
                raise ValueError('Duplicate, directory or nonregular ZIP entry')
            if entry.compress_type != zipfile.ZIP_STORED or entry.flag_bits & 1:
                raise ValueError('HUI v1 accepts unencrypted stored ZIP entries only')
            names.add(entry.filename)
            portable_names.add(entry.filename.casefold())
        if 'manifest.json' not in names or archive.getinfo('manifest.json').file_size>4*1024**2:
            raise ValueError('Missing or oversized manifest')
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('format')!='hui' or manifest.get('format_version')!=1 or manifest.get('schema_version')!=SCHEMA_VERSION:
            raise ValueError('Unsupported package or schema version')
        expected = manifest.get('files')
        if not isinstance(expected,dict) or set(expected)|{'manifest.json'}!=names or 'catalog.sqlite' not in expected:
            raise ValueError('Manifest file list differs from archive')
        for name,metadata in expected.items():
            safe_path(name)
            path = destination/name
            path.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(name) as stream,path.open('xb') as target:
                shutil.copyfileobj(stream,target,length=1024**2)
            if path.stat().st_size!=metadata['size'] or sha256(path)!=metadata['sha256']:
                raise ValueError('Hash or size mismatch: '+name)
        (destination/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False),encoding='utf-8')
    db = connect(destination/'catalog.sqlite',readonly=True)
    try:
        db.execute('PRAGMA trusted_schema=OFF')
        validate_catalog(db)
        if manifest.get('index_version')!=db.execute('SELECT max(id) FROM IndexVersions').fetchone()[0]:
            raise ValueError('Manifest index version mismatch')
        included = manifest.get('includes_originals')
        if type(included) is not bool:
            raise ValueError('Missing originals policy')
        for row in db.execute('SELECT original_path,sha256 FROM SourceEditions'):
            path = destination/row['original_path']
            if included and (not path.is_file() or sha256(path)!=row['sha256']):
                raise ValueError('Original PDF identity mismatch')
        if not included and any(n.startswith(('pages/','originals/')) for n in names):
            raise ValueError('Unexpected copyrighted assets in index-only package')
        if included:
            for row in db.execute('SELECT image_path FROM Pages WHERE image_path IS NOT NULL'):
                if not (destination/row[0]).is_file():
                    raise ValueError('Missing page image')
    finally:
        db.close()
    return manifest


def import_package(package: Path, destination: Path):
    destination = Path(destination).resolve()
    destination.parent.mkdir(parents=True,exist_ok=True)
    backup = destination.with_name(destination.name+'.backup')
    if backup.exists():
        if not destination.exists():
            backup.rename(destination)
        else:
            backup = destination.with_name(destination.name+'.backup.'+uuid.uuid4().hex)
    staging = Path(tempfile.mkdtemp(prefix=destination.name+'.staging.',dir=destination.parent))
    moved = False
    try:
        manifest = verify_package(Path(package),staging)
        if destination.exists():
            if destination.is_symlink() or not destination.is_dir():
                raise ValueError('Destination must be a regular workspace directory')
            destination.rename(backup)
            moved = True
        try:
            staging.rename(destination)
        except BaseException:
            if moved:
                backup.rename(destination)
            raise
        return manifest
    finally:
        if staging.exists():
            shutil.rmtree(staging)
