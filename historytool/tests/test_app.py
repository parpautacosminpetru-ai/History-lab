"""Integration tests with isolated DB and actual locally generated PDF."""
from __future__ import annotations
import os, sys, tempfile, importlib
from pathlib import Path
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def setup():
    tmp=tempfile.TemporaryDirectory()
    os.environ['ATLAS_DATA_DIR']=tmp.name
    if 'app' in sys.modules:del sys.modules['app']
    import app
    client=TestClient(app.app)
    return tmp,client


def test_upload_index_query_and_laboratory():
    tmp,c=setup()
    try:
        assert c.get('/api/health').status_code==200
        a='În anul 1475, în Moldova, Ștefan cel Mare era menționat. În anul 1476, Ștefan cel Mare a plecat în Polonia.'
        b='În anul 1475, Polonia și Moldova sunt menționate. În anul 1475, în Moldova, Ștefan cel Mare era menționat.'
        up=c.post('/api/sources/upload',files=[('files',('A.txt',a.encode(),'text/plain')),('files',('B.txt',b.encode(),'text/plain'))])
        assert up.status_code==200,up.text
        assert len(up.json()['files'])==2
        dup=c.post('/api/sources/upload',files={'files':('C.txt',a.encode(),'text/plain')})
        assert dup.json()['files'][0]['duplicate']
        index=c.post('/api/index/run')
        assert index.status_code==200,index.text
        assert len(index.json()['results'])==2
        st=c.get('/api/state').json()['counts']
        assert st['sources']==2 and st['passages']==4,st
        assert st['statements']==3,st  # exact identical statement deduplicated across sources
        assert st['lexemes']>=10,st
        q=c.get('/api/query',params={'q':'Ștefan cel Mare'}).json()
        assert q['total']>=3,q
        assert q['sources'] and q['hits'][0]['page']==1
        match=c.get('/api/query',params={'q':'știrbei neexistent'}).json()
        assert match['total']==0
        entities=c.get('/api/entities').json()['entities']
        stefan=next((x for x in entities if x['name']=='Ștefan cel Mare'),None)
        moldova=next((x for x in entities if x['name']=='Moldova'),None)
        assert stefan and moldova,entities
        detail=c.get(f"/api/entity/{stefan['id']}").json()
        assert len(detail['appearances'])>=3,detail
        overlaps=c.get('/api/overlaps',params={'ids':f"{stefan['id']},{moldova['id']}"}).json()
        assert overlaps['count']>=2,overlaps
        layers=c.get('/api/layers',params={'year':1476}).json()
        assert not any(x['name']=='Moldova' for x in layers['regions'])  # no region displayed without evidence at selected date
        pol=next(x for x in layers['regions'] if x['name']=='Polonia')
        assert pol['evidence_count']>=1,pol
        p=c.get('/api/passages/'+str(q['hits'][0]['id']))
        assert p.status_code==200 and p.json()['passage']['source_title']
        n=c.post('/api/notes',json={'title':'Studiu propriu','body':'Observația cercetătorului.'}).json()
        assert n['id']
        assert c.post(f"/api/notes/{n['id']}/evidence",json={'passage_id':q['hits'][0]['id']}).status_code==200
        assert len(c.get('/api/notes').json()['notes'][0]['evidence'])==1
        export=c.get(f"/api/notes/{n['id']}/export")
        assert export.status_code==200 and 'Studiu propriu' in export.content.decode('utf-8-sig')
        assert c.post(f"/api/entities/{stefan['id']}/alias",json={'alias':'Ștefan voievod'}).status_code==200
        assert c.patch(f"/api/entities/{stefan['id']}",json={'status':'confirmat'}).status_code==200
    finally:tmp.cleanup()


def test_pdf_original_render_and_deduplicated_file():
    import fitz
    tmp,c=setup()
    try:
        doc=fitz.open();page=doc.new_page();page.insert_text((62,90),'In anul 1475, in Moldova, Stefan cel Mare a fost mentionat.',fontsize=13)
        data=doc.tobytes();doc.close()
        up=c.post('/api/sources/upload',files={'files':('manuscris.pdf',data,'application/pdf')})
        assert up.status_code==200,up.text
        assert c.post('/api/index/run').status_code==200
        search=c.get('/api/query',params={'q':'Moldova'}).json()
        assert search['total']>0,search
        pid=search['hits'][0]['id']
        img=c.get(f'/api/passages/{pid}/image')
        assert img.status_code==200,img.text[:300] if img.status_code!=200 else ''
        assert img.content[:8]==b'\x89PNG\r\n\x1a\n'
        o=c.get('/api/sources/1/original')
        assert o.content[:5]==b'%PDF-'
    finally:tmp.cleanup()


def test_demo_expressly_fictitious():
    tmp,c=setup()
    try:
        demo=c.post('/api/demo')
        assert demo.status_code==200 and 'inventate' in demo.json()['warning']
        idx=c.post('/api/index/run')
        assert idx.status_code==200,idx.text
        q=c.get('/api/query',params={'q':'Moldova Polonia'}).json()
        assert q['total']>0,q
        assert any('DEMO-FICTIV' in x['source_title'] for x in q['hits'])
    finally:tmp.cleanup()


def test_time_precision_is_not_invented():
    import engine
    assert engine.get_dates('În secolul al XV-lea se menționează un document.')[:4]==(1401,1500,'secol','secolul al XV-lea')
    assert engine.get_dates('În anul 1475 a existat o mențiune.')[:3]==(1475,1475,'an')
    assert engine.get_dates('La 12 iunie 1476 s-a scris o scrisoare.')[2:] == ('zi','12 iunie 1476',6,12)
    assert engine.get_dates('Acțiunea este menționată.')[2] == 'nedatat'
    tmp,c=setup()
    try:
        a='În anul 1476, în Moldova, un autor a scris. La 12 iunie 1476, în Polonia, un autor a scris.'
        c.post('/api/sources/upload',files={'files':('Precizie.txt',a.encode(),'text/plain')})
        c.post('/api/index/run')
        y=c.get('/api/layers',params={'year':1476}).json()
        assert any(v['name']=='Moldova' for v in y['regions'])
        june=c.get('/api/layers',params={'year':1476,'month':6,'day':12}).json()
        assert not any(v['name']=='Moldova' for v in june['regions'])
        assert any(v['name']=='Polonia' for v in june['regions'])
        assert june['unresolved_time']>=1
        may=c.get('/api/layers',params={'year':1476,'month':5,'day':12}).json()
        assert not may['regions']
    finally:tmp.cleanup()
