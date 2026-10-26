import stat
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from hui_indexer.packages import import_package,export_package
from hui_indexer.semantics import create_node,annotate,validate,publish
from conftest import part


def test_imported_offsets_are_revalidated_even_after_bypassing_insert_trigger(corpus):
    db,_,_,_,segment=corpus
    node=create_node(db,'domnie','concept')
    occurrence=annotate(db,node,[part(segment,'domnie')])
    span=db.execute('SELECT span_id FROM Occurrences WHERE id=?',(occurrence,)).fetchone()[0]
    db.execute('UPDATE SpanParts SET end_offset=999999 WHERE span_id=?',(span,));db.commit()
    assert any('outside source text' in message for message in validate(db))
    with pytest.raises(ValueError):publish(db,'must fail')
    assert db.execute('SELECT count(*) FROM IndexVersions').fetchone()[0]==0


def test_visual_ranges_are_revalidated(corpus):
    db,_,_,_,segment=corpus
    db.execute('UPDATE TextBoxes SET end_offset=999999 WHERE segment_id=?',(segment['id'],));db.commit()
    assert any('Visual box' in message for message in validate(db))


@pytest.mark.parametrize('kind',['symlink','duplicate','compressed'])
def test_archive_nonregular_duplicate_and_compressed_entries(tmp_path,kind):
    path=tmp_path/'attack.hui'
    with zipfile.ZipFile(path,'w') as archive:
        if kind=='symlink':
            entry=zipfile.ZipInfo('pages/link');entry.create_system=3;entry.external_attr=(stat.S_IFLNK|0o777)<<16
            archive.writestr(entry,'/etc/passwd')
        elif kind=='duplicate':
            archive.writestr('catalog.sqlite','a')
            with pytest.warns(UserWarning):archive.writestr('catalog.sqlite','b')
        else:archive.writestr('catalog.sqlite','x'*1000,compress_type=zipfile.ZIP_DEFLATED)
    with pytest.raises(ValueError):import_package(path,tmp_path/'reader')
    assert not (tmp_path/'reader').exists()


def test_failed_install_after_backup_restores_existing_workspace(corpus,tmp_path,monkeypatch):
    db,workspace,*_=corpus
    publish(db,'QA')
    package=tmp_path/'valid.hui';export_package(db,workspace,package)
    target=tmp_path/'reader';import_package(package,target)
    before=(target/'catalog.sqlite').read_bytes()
    original=Path.rename
    def fail_install(self,destination):
        if '.staging.' in self.name and Path(destination)==target:
            raise OSError('Simulated failed installation rename')
        return original(self,destination)
    monkeypatch.setattr(Path,'rename',fail_install)
    with pytest.raises(OSError):import_package(package,target)
    assert (target/'catalog.sqlite').read_bytes()==before


def test_case_collisions_cannot_alias_files_on_windows(corpus,tmp_path):
    db,workspace,*_=corpus
    publish(db,'QA')
    original=tmp_path/'valid.hui'
    export_package(db,workspace,original,include_originals=True,rights_confirmed=True)
    malicious=tmp_path/'case-alias.hui'
    with zipfile.ZipFile(original) as source,zipfile.ZipFile(malicious,'w') as target:
        manifest=json.loads(source.read('manifest.json'))
        for name in source.namelist():
            if name!='manifest.json':target.writestr(name,source.read(name))
        for name,data in [('pages/collision.png',b'first'),('pages/COLLISION.png',b'second')]:
            target.writestr(name,data)
            manifest['files'][name]={'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)}
        target.writestr('manifest.json',json.dumps(manifest))
    with pytest.raises(ValueError,match='Duplicate'):import_package(malicious,tmp_path/'reader')
