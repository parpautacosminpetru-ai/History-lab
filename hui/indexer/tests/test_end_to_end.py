import json
import socket
import sqlite3
import zipfile
from pathlib import Path

from PIL import Image
import pytest

from hui_indexer.coverage import coverage
from hui_indexer.db import connect,normalize,stable_id
from hui_indexer.demo import make_pdf,TEXTS
from hui_indexer.ingestion import import_pdf,correct_structure
from hui_indexer.packages import export_package,import_package,validate_catalog
from hui_indexer.search import Query,search,natural_query,parse
from hui_indexer.semantics import (create_node,create_span,annotate,relation,review,
                                   provenance,publish,validate,add_variant,span_text)
from conftest import part


def confirm(db,*items):
    review(db,[{'type':kind,'id':id,'status':'human_confirmed'} for kind,id in items],reviewer='QA fixture')


def endpoints(db,segment,nth=0):
    x,y = create_node(db,'X','concept'),create_node(db,'Y','concept')
    xo,yo = annotate(db,x,[part(segment,'X',nth)]),annotate(db,y,[part(segment,'Y',nth)])
    return x,y,xo,yo


def test_01_pdf_text_page_and_coordinates(corpus):
    db,workspace,pdf,edition,segment = corpus
    result = search(db,Query('domnie'))
    assert len(result)==1 and result[0]['pdf_page']==2
    assert result[0]['edition_id']==edition
    assert (workspace/result[0]['original_path']).read_bytes()==pdf.read_bytes()
    for page in db.execute('SELECT * FROM Pages'):
        texts = db.execute('SELECT original_text FROM TextSegments WHERE page_id=? ORDER BY reading_order',(page['id'],))
        assert ''.join(r[0] for r in texts)==page['raw_text']
    assert validate(db)==[]


def test_02_real_source_highlight(corpus):
    db,workspace,_,_,segment = corpus
    node = create_node(db,'domnie','concept')
    occurrence = annotate(db,node,[part(segment,'domnie')])
    trace = provenance(db,occurrence)
    page = trace['parts'][0]
    assert page['pdf_page']==2 and page['boxes']
    image = Image.open(workspace/page['image_path']).convert('RGB')
    hits = 0
    for box in page['boxes']:
        assert 0<=box['x0']<=box['x1']<=1 and 0<=box['y0']<=box['y1']<=1
        rect = (int(box['x0']*image.width),int(box['y0']*image.height),
                max(int(box['x0']*image.width)+1,int(box['x1']*image.width)),
                max(int(box['y0']*image.height)+1,int(box['y1']*image.height)))
        if min(image.crop(rect).convert('L').getextrema())<150:
            hits+=1
    assert hits>=5  # Highlight rectangles actually intersect the rendered six-letter word.


def test_03_bidirectional_provenance(corpus):
    db,_,_,edition,segment = corpus
    node = create_node(db,'domnie','concept')
    occurrence = annotate(db,node,[part(segment,'domnie')])
    confirm(db,('node',node),('occurrence',occurrence))
    trace = provenance(db,occurrence)
    forward = search(db,Query('domnie',mode='index',source_id=trace['source_id']))
    assert forward[0]['edition_id']==edition
    assert forward[0]['annotations'][0]['node_id']==node
    assert trace['parts'][0]['structure_id']==segment['structure_id']


def test_04_negation_not_positive(corpus):
    db,_,_,_,segment = corpus
    x,y,xo,yo = endpoints(db,segment)
    evidence = [part(segment,'X nu a provocat Y.')]
    with pytest.raises(ValueError,match='Negation'):
        relation(db,xo,'causality',yo,evidence,connector='provocat',negated=False,modality='assertive',attribution='')
    rel = relation(db,xo,'causality',yo,evidence,connector='provocat',negated=True,modality='assertive',attribution='')
    confirm(db,('node',x),('node',y),('relation',rel))
    assert search(db,Query('X AND Y',mode='linked',relation_type='causality'))==[]
    found = search(db,Query('X AND Y',mode='linked',include_negated=True))
    assert found[0]['relations'][0]['negated']==1


def test_05_modality_and_attribution(corpus):
    db,_,_,_,segment = corpus
    _,_,xo,yo = endpoints(db,segment,nth=1)
    evidence = [part(segment,'Autorul presupune că X ar fi provocat Y.')]
    with pytest.raises(ValueError,match='certain'):
        relation(db,xo,'causality',yo,evidence,connector='provocat',negated=False,modality='certain',attribution='Autorul')
    with pytest.raises(ValueError,match='voice'):
        relation(db,xo,'causality',yo,evidence,connector='provocat',negated=False,modality='conditional',attribution='')
    rid = relation(db,xo,'causality',yo,evidence,connector='provocat',negated=False,modality='conditional',attribution='Autorul presupune')
    row = db.execute('SELECT * FROM ExplicitRelations WHERE id=?',(rid,)).fetchone()
    assert row['modality']=='conditional' and row['attribution']=='Autorul presupune'


def test_06_recurrence_and_12_incremental(corpus,tmp_path):
    db,workspace,_,edition,segment = corpus
    node = create_node(db,'domnie','concept')
    ids = [annotate(db,node,[part(segment,'domnie')])]
    for i,language in enumerate(['fr','de'],1):
        pdf = tmp_path/f'{language}.pdf'
        make_pdf(pdf,[TEXTS[i]])
        new = import_pdf(db,workspace,pdf,title=language,language=language)
        row = dict(db.execute('SELECT t.* FROM TextSegments t JOIN Pages p ON p.id=t.page_id WHERE p.edition_id=?',(new,)).fetchone())
        ids.append(annotate(db,node,[part(row,'domnie')],language=language))
    assert db.execute('SELECT count(*) FROM IndexNodes').fetchone()[0]==1
    assert len(set(ids))==3
    assert len({provenance(db,i)['source_id'] for i in ids})==3
    assert provenance(db,ids[0])['parts'][0]['segment_id']==segment['id']


def test_07_overlapping_annotations_without_text_duplication(corpus):
    db,_,_,_,segment = corpus
    a,b = create_node(db,'domnie','concept'),create_node(db,'Tema domnie','theme')
    annotate(db,a,[part(segment,'domnie')])
    annotate(db,b,[part(segment,'Tema domnie')])
    assert db.execute('SELECT count(*) FROM SpanParts WHERE segment_id=?',(segment['id'],)).fetchone()[0]==2
    assert db.execute('SELECT count(*) FROM TextSegments WHERE id=?',(segment['id'],)).fetchone()[0]==1


def test_08_homonyms_never_automatically_merged(corpus):
    db,*_ = corpus
    a = create_node(db,'Alexandria','locality',disambiguation='A')
    b = create_node(db,'Alexandria','locality',disambiguation='B')
    assert a!=b
    assert create_node(db,'ignored','concept',node_id=a)==a


def test_09_multilingual_validated_equivalences(corpus,tmp_path):
    db,workspace,_,_,segment = corpus
    pdf = tmp_path/'fr.pdf'
    make_pdf(pdf,[TEXTS[1]])
    edition = import_pdf(db,workspace,pdf,title='Français',language='fr')
    french = dict(db.execute('SELECT t.* FROM TextSegments t JOIN Pages p ON p.id=t.page_id WHERE p.edition_id=?',(edition,)).fetchone())
    node = create_node(db,'instituție de test','institution','ro')
    occurrence = annotate(db,node,[part(french,'institution de test')],language='fr')
    confirm(db,('node',node),('occurrence',occurrence))
    span = db.execute('SELECT span_id FROM Occurrences WHERE id=?',(occurrence,)).fetchone()[0]
    variant = add_variant(db,node,'institution de test','fr',span)
    assert search(db,Query('"institution de test"',mode='index'))==[]
    confirm(db,('variant',variant))
    assert len(search(db,Query('"institution de test"',mode='index')))==1
    assert search(db,Query('"Testinstitution"',mode='index'))==[]
    assert normalize('ÎN ȚARĂ')=='in tara'


def test_10_identical_results_with_network_disabled(corpus,monkeypatch):
    db,*_ = corpus
    before = search(db,Query('domnie'))
    def blocked(*args,**kwargs):
        raise AssertionError('Network access in deterministic engine')
    monkeypatch.setattr(socket,'socket',blocked)
    monkeypatch.setattr(socket,'create_connection',blocked)
    assert search(db,Query('domnie'))==before


def test_13_package_roundtrip_and_tampering(corpus,tmp_path):
    db,workspace,*_ = corpus
    publish(db,'QA')
    package = tmp_path/'test.hui'
    with pytest.raises(ValueError,match='permission'):
        export_package(db,workspace,package,include_originals=True)
    export_package(db,workspace,package,include_originals=True,rights_confirmed=True)
    restored = tmp_path/'reader'
    import_package(package,restored)
    offline = connect(restored/'catalog.sqlite',readonly=True)
    try:
        assert search(offline,Query('domnie'))==search(db,Query('domnie'))
    finally:
        offline.close()
    bad = tmp_path/'bad.hui'
    with zipfile.ZipFile(package) as src,zipfile.ZipFile(bad,'w') as dst:
        for name in src.namelist():
            value = src.read(name)
            dst.writestr(name,value+b'broken' if name=='catalog.sqlite' else value)
    old = (restored/'catalog.sqlite').read_bytes()
    with pytest.raises(ValueError,match='mismatch'):
        import_package(bad,restored)
    assert (restored/'catalog.sqlite').read_bytes()==old
    import_package(package,restored)
    assert restored.with_name('reader.backup').is_dir()


def test_14_physical_vs_human_coverage(corpus):
    db,_,_,_,segment = corpus
    node = create_node(db,'domnie','concept')
    occurrence = annotate(db,node,[part(segment,'domnie')])
    metrics = coverage(db)
    assert metrics['pages_processed']==metrics['physical_pages']==2
    assert metrics['human_verified_characters']==0
    assert metrics['semantic_exhaustiveness']=='not_measured'
    confirm(db,('node',node),('occurrence',occurrence))
    metrics = coverage(db)
    assert metrics['human_verified_characters']==6
    assert metrics['unclassified_intervals']


@pytest.mark.parametrize('name',['../escape','/escape','C:/escape','pages/../../escape','pages\\escape','pages//escape','pages/./escape'])
def test_15_malicious_archive_paths(corpus,tmp_path,name):
    db,workspace,*_ = corpus
    bad = tmp_path/'malicious.hui'
    with zipfile.ZipFile(bad,'w') as archive:
        archive.writestr(name,'malicious')
    with pytest.raises(ValueError):
        import_package(bad,tmp_path/'target')
    assert not (tmp_path/'target').exists()


def test_sql_injection_is_a_literal_query(corpus):
    db,*_ = corpus
    assert search(db,Query('"domnie\'; DROP TABLE Sources;--"'))==[]
    assert db.execute('SELECT count(*) FROM Sources').fetchone()[0]==1
    assert search(db,Query('domnie',source_id="' OR 1=1 --"))==[]


def test_source_text_is_immutable_and_spans_are_checked(corpus):
    db,_,_,_,segment = corpus
    with pytest.raises(sqlite3.IntegrityError):
        db.execute('UPDATE TextSegments SET original_text=? WHERE id=?',('changed',segment['id']))
    db.rollback()
    with pytest.raises(ValueError):
        create_span(db,[{'segment_id':segment['id'],'start':0,'end':999999}])
    node = create_node(db,'domnie','concept')
    before = db.execute('SELECT count(*) FROM EvidenceSpans').fetchone()[0]
    with pytest.raises(ValueError):
        annotate(db,node,[part(segment,'domnie')],quote='inventat')
    assert db.execute('SELECT count(*) FROM EvidenceSpans').fetchone()[0]==before


def test_operators_scopes_and_pagination(corpus):
    db,*_ = corpus
    assert len(search(db,Query('domnie AND NOT absent')))==1
    assert len(search(db,Query('(absent OR domnie) AND NOT impossible')))==1
    assert search(db,Query('"CAPITOLUL I" AND "Préface introductive"'))==[]
    assert len(search(db,Query('"CAPITOLUL I" AND "Préface introductive"',scope='source')))==2
    whole = search(db,Query())
    assert whole==search(db,Query(limit=1))+search(db,Query(limit=1,offset=1))
    assert natural_query('Unde apare Carol cel Mare în legătură cu Aachen?').mode=='linked'
    with pytest.raises(ValueError):
        natural_query('Explică istoria')
    with pytest.raises(ValueError):
        parse('domnie AND')


def test_cooccurrence_does_not_imply_relation(corpus):
    db,_,_,_,segment = corpus
    a,b,ao,bo = endpoints(db,segment)
    confirm(db,('node',a),('node',b),('occurrence',ao),('occurrence',bo))
    assert search(db,Query('X AND Y',mode='index'))
    assert search(db,Query('X AND Y',mode='linked'))==[]


def test_import_resume_dedup_and_edition_versions(tmp_path):
    workspace = tmp_path/'workspace'
    db = connect(workspace/'catalog.sqlite')
    try:
        pdf = tmp_path/'a.pdf'
        make_pdf(pdf,[['one'],['two'],['three']])
        first = import_pdf(db,workspace,pdf,title='A',stop_after=1)
        assert db.execute('SELECT count(*) FROM Pages').fetchone()[0]==1
        assert import_pdf(db,workspace,pdf,title='A')==first
        assert import_pdf(db,workspace,pdf,title='A')==first
        assert db.execute('SELECT count(*) FROM Pages').fetchone()[0]==3
        make_pdf(pdf,[['changed']])
        second = import_pdf(db,workspace,pdf,title='A')
        assert second!=first
        assert db.execute('SELECT count(*) FROM Sources').fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM SourceEditions').fetchone()[0]==2
    finally:
        db.close()


def test_human_review_batch_is_atomic(corpus):
    db,*_ = corpus
    node = create_node(db,'X','concept')
    with pytest.raises(ValueError):
        review(db,[{'type':'node','id':node,'status':'human_confirmed'},
                   {'type':'node','id':'missing','status':'human_confirmed'}],reviewer='Human')
    assert db.execute('SELECT verification FROM IndexNodes WHERE id=?',(node,)).fetchone()[0]=='proposed'
    assert db.execute('SELECT count(*) FROM ReviewLog').fetchone()[0]==0


def test_multi_page_and_overlapping_spans(corpus):
    db,_,_,_,second = corpus
    first = db.execute('SELECT t.* FROM TextSegments t JOIN Pages p ON p.id=t.page_id WHERE p.pdf_page=1').fetchone()
    span = create_span(db,[{'segment_id':first['id'],'start':0,'end':8},
                         {'segment_id':second['id'],'start':0,'end':9}])
    assert span_text(db,span)==first['original_text'][:8]+'\n'+second['original_text'][:9]


def test_schema_rejects_unknown_executable_objects(corpus):
    db,*_ = corpus
    publish(db,'QA')
    db.execute('CREATE VIEW malicious AS SELECT 1')
    with pytest.raises(ValueError,match='schema'):
        validate_catalog(db)
