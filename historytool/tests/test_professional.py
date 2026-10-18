"""Practical integrity, evidence, backup, OCR and background index acceptance tests."""
import io
import os
import sys
import time
import zipfile
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def setup_env():
    tmp=tempfile.TemporaryDirectory()
    os.environ['ATLAS_DATA_DIR']=tmp.name
    sys.modules.pop('app',None)
    import app
    return tmp,TestClient(app.app)

def seed(client):
    text=(
      'În anul 1475, în Moldova, Ștefan cel Mare a încheiat un tratat cu Polonia. '
      'La 12 iunie 1476, Ștefan cel Mare a plecat în Polonia. '
      'În secolul al XV-lea, un autor a descris Moldova.'
    )
    result=client.post('/api/sources/upload',files={'files':('Sursa1.txt',text.encode('utf-8'),'text/plain')})
    assert result.status_code==200,result.text
    result=client.post('/api/index/run')
    assert result.status_code==200,result.text
    names={x['name']:x['id'] for x in client.get('/api/entities').json()['entities']}
    assert 'Ștefan cel Mare' in names and 'Moldova' in names and 'Polonia' in names
    return names

def test_claim_exact_evidence_dedup_intersection_and_date_precision():
    tmp,c=setup_env()
    try:
        names=seed(c)
        passages=c.get('/api/query',params={'q':'tratat'}).json()['hits']
        pid=next(x['id'] for x in passages if 'a încheiat' in x['text'])
        payload={'passage_id':pid,'subject_id':names['Ștefan cel Mare'],'predicate':'a încheiat',
                 'object_id':names['Polonia'],'place_id':names['Moldova'],'theme':'diplomație'}
        # The verified relationship must be literally supported by source text.
        fail=c.post('/api/claims',json={**payload,'predicate':'a cucerit'})
        assert fail.status_code==422,fail.text
        wrong_entity=c.post('/api/claims',json={**payload,'subject_id':names['Ștefan cel Mare'],
                    'object_id':names['Moldova'],'place_id':None,'predicate':'nu exista'})
        assert wrong_entity.status_code==422
        one=c.post('/api/claims',json=payload)
        assert one.status_code==200,one.text
        cid=one.json()['id']
        repeat=c.post('/api/claims',json={**payload,'theme':'politică externă'})
        assert repeat.status_code==200 and repeat.json()['deduplicated']
        cl=c.get('/api/claims').json()['claims']
        assert len(cl)==1 and cl[0]['attestations']==1 and 'diplomație' in cl[0]['themes'] and 'politică externă' in cl[0]['themes']
        frame=c.get('/api/context').json()
        assert frame['total']==1 and len(frame['intersections'])==1 and not frame['regions'],frame
        assert frame['intersections'][0]['claims'][0]['id']==cid
        atYear=c.get('/api/context',params={'year':1475}).json()
        assert atYear['total']==1
        atDay=c.get('/api/context',params={'year':1475,'month':6,'day':12}).json()
        assert atDay['total']==0
        ev=c.get(f'/api/claims/{cid}/evidence').json()
        assert ev['passages'][0]['id']==pid
        assert c.delete(f'/api/claims/{cid}').status_code==200
        assert c.get('/api/claims').json()['claims']==[]
    finally:tmp.cleanup()

def test_backup_audit_verify_delete_source():
    tmp,c=setup_env()
    try:
        seed(c)
        verify=c.get('/api/verify').json()
        assert verify['verified']==verify['total']==1
        backup=c.get('/api/backup')
        assert backup.status_code==200 and backup.content[:2]==b'PK'
        z=zipfile.ZipFile(io.BytesIO(backup.content))
        assert 'manifest.json' in z.namelist()
        assert 'data/atlas.sqlite3' in z.namelist()
        assert any(x.endswith('.txt') for x in z.namelist())
        assert c.get('/api/audit').json()['entries']
        src=c.get('/api/state').json()['sources'][0]
        assert c.delete(f"/api/sources/{src['id']}").status_code==200
        assert c.get('/api/state').json()['counts']['passages']==0
        assert c.get('/api/verify').json()['total']==0
    finally:tmp.cleanup()

def test_job_progress_and_alias_no_duplication():
    tmp,c=setup_env()
    try:
        seed(c)
        q=c.get('/api/query',params={'q':'Ștefan cel Mare'}).json()
        assert q['total']>0
        result=c.post('/api/entities',json={'name':'Crucea Albă','kind':'instituție'})
        assert result.status_code==200
        assert c.post('/api/entities',json={'name':'Crucea Alba','kind':'instituție'}).json()['id']==result.json()['id']
        p=c.post('/api/index/start',params={'ocr':'false'})
        assert p.status_code==200
        for _ in range(100):
            current=c.get('/api/index/progress').json()
            if current['job']['status']!='running':break
            time.sleep(.05)
        assert current['job']['status']=='done',current
        assert not current['job']['result']['results']
    finally:tmp.cleanup()

def test_scanned_pdf_ocr_if_installed():
    import fitz, shutil
    if not shutil.which('tesseract'):return
    from PIL import Image,ImageDraw,ImageFont
    tmp,c=setup_env()
    try:
        im=Image.new('RGB',(1000,400),'white')
        draw=ImageDraw.Draw(im)
        font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',35)
        draw.text((30,65),'Moldova si Polonia in anul 1475.',fill='black',font=font)
        bio=io.BytesIO();im.save(bio,format='PNG')
        pdf=fitz.open();page=pdf.new_page(width=500,height=200);page.insert_image(page.rect,stream=bio.getvalue());content=pdf.tobytes();pdf.close()
        up=c.post('/api/sources/upload',files={'files':('Scan.pdf',content,'application/pdf')})
        assert up.status_code==200
        result=c.post('/api/index/run?ocr=true').json()
        assert result['results'][0]['status']=='indexed',result
        state=c.get('/api/state').json()
        assert state['counts']['passages']>=1,state
        x=c.get('/api/query',params={'q':'Polonia'}).json()
        assert x['hits'],x
        im=c.get(f"/api/passages/{x['hits'][0]['id']}/image")
        assert im.status_code==200 and im.content.startswith(b'\x89PNG')
    finally:tmp.cleanup()


def test_bce_ancient_time_not_silently_modernized():
    import engine
    assert engine.get_dates('În anul 44 î.Hr. s-a întâmplat.')[:3]==(-44,-44,'an')
    assert engine.get_dates('În secolul al II-lea î.Hr. a fost consemnat.')[:3]==(-200,-101,'secol')
    assert engine.get_dates('În anul 44 a fost scris un act.')[:3]==(44,44,'an')
    assert engine.get_dates('Nu există data menționată.')[:3]==(None,None,'nedatat')

def test_bibliography_printed_pagination_and_export():
    import fitz
    tmp,c=setup_env()
    try:
        doc=fitz.open()
        page=doc.new_page();page.insert_text((40,85),'In anul 1475, Moldova este mentionata in document.',fontsize=12)
        b=doc.tobytes();doc.close()
        r=c.post('/api/sources/upload',files={'files':('Carte.pdf',b,'application/pdf')})
        assert r.status_code==200,r.text
        sid=r.json()['files'][0]['id']
        assert c.post('/api/index/run').status_code==200
        params={'title':'Istoria Moldovei','author':'Autor cercetat','publication':'1913','edition':'Volumul I',
                'archival_ref':'Biblioteca X, cota 123','language':'română','remarks':'Ediție scanată'}
        u=c.put(f'/api/sources/{sid}/metadata',json=params)
        assert u.status_code==200,u.text
        assert c.get(f'/api/sources/{sid}/metadata').json()['author']=='Autor cercetat'
        lb=c.put(f'/api/sources/{sid}/pages/1/label',json={'printed_label':'VIII'})
        assert lb.status_code==200,lb.text
        pid=c.get('/api/query',params={'q':'Moldova'}).json()['hits'][0]['id']
        detail=c.get(f'/api/passages/{pid}').json()
        assert detail['passage']['printed_label']=='VIII'
        note=c.post('/api/notes',json={'title':'Raport','body':'Evaluarea istoricului.'}).json()
        assert c.post(f"/api/notes/{note['id']}/evidence",json={'passage_id':pid}).status_code==200
        exported=c.get(f"/api/notes/{note['id']}/export").content.decode('utf-8-sig')
        assert 'Autor cercetat' in exported and 'pagină tipărită VIII' in exported,exported
        assert 'Biblioteca X, cota 123' in exported
    finally:tmp.cleanup()
