"""historytool | Local evidence-preserving historical research workstation.
Run: python app.py ; open http://127.0.0.1:8765

It indexes all extracted words/statements, provides auditable evidence and a
conservative universal entity index. It does NOT perform complete semantic
interpretation of arbitrary texts; suggestions require historian verification.
"""
from __future__ import annotations
import os, json, re, mimetypes, hashlib, secrets, contextlib, threading, tempfile, zipfile, shutil, sqlite3
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Body
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, JSONResponse, Response
from starlette.background import BackgroundTask
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
import engine

HERE=Path(__file__).resolve().parent
DATA=Path(os.environ.get('HISTORYTOOL_DATA_DIR',os.environ.get('ATLAS_DATA_DIR',HERE/'data'))).resolve()
DATA.mkdir(parents=True,exist_ok=True)
UPLOAD_DIR=DATA/'sources';UPLOAD_DIR.mkdir(exist_ok=True)
DB=DATA/'atlas.sqlite3'
app=FastAPI(title='historytool – stație locală de cercetare',version='1.0.1',docs_url='/api/docs',openapi_url='/api/openapi.json')
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1','localhost','testserver'])
app.mount('/static',StaticFiles(directory=str(HERE/'static')),name='static')
SUPPORTED={'.pdf','.txt','.md','.docx','.png','.jpg','.jpeg'}
MAX_FILE_SIZE=100*1024*1024
index_lock=threading.Lock()
job={'status':'idle','started':None,'finished':None,'result':None,'error':None}

def audit(db,action,subject,info=''):
    db.execute('INSERT INTO audit_log(created_at,action,subject,info) VALUES(?,?,?,?)',(now(),action,str(subject),str(info)[:4000]))

@contextlib.contextmanager
def database():
    conn=engine.connect(DB)
    try:yield conn
    finally:conn.close()

with database() as _db:
    # Repair absolute paths after restoring a backup or moving the application.
    for _row in _db.execute('SELECT id,sha256,format,file_path FROM sources'):
        _old=Path(_row['file_path'])
        if not _old.is_file():
            _new=UPLOAD_DIR/(_row['sha256'][:20]+_row['format'])
            if _new.is_file() and hashlib.sha256(_new.read_bytes()).hexdigest()==_row['sha256']:
                _db.execute('UPDATE sources SET file_path=? WHERE id=?',(str(_new),_row['id']))
    engine.seed_entities(_db)
    _db.commit()

def as_dict(row):return dict(row) if row is not None else None

def now():return datetime.now(timezone.utc).isoformat()

@app.get('/',response_class=FileResponse)
def home():return str(HERE/'static'/'index.html')

@app.get('/api/health')
def health():
    with database() as db:
        return {'status':'ok','sources':db.execute('SELECT COUNT(*) FROM sources').fetchone()[0],
                'indexed':db.execute('SELECT COUNT(*) FROM sources WHERE status="indexed"').fetchone()[0]}

@app.get('/api/state')
def state():
    with database() as db:
        return {'sources':[dict(x) for x in db.execute('SELECT id,title,filename,format,status,page_count,passage_count,warning FROM sources ORDER BY id DESC')],
                'counts':{
                    'sources':db.execute('SELECT COUNT(*) FROM sources').fetchone()[0],
                    'pages':db.execute('SELECT COALESCE(SUM(page_count),0) FROM sources WHERE status="indexed"').fetchone()[0],
                    'passages':db.execute('SELECT COUNT(*) FROM passages').fetchone()[0],
                    'statements':db.execute('SELECT COUNT(*) FROM statements').fetchone()[0],
                    'entities':db.execute('SELECT COUNT(*) FROM entities WHERE id IN (SELECT entity_id FROM mentions)').fetchone()[0],
                    'mentions':db.execute('SELECT COUNT(*) FROM mentions').fetchone()[0],
                    'lexemes':db.execute('SELECT COUNT(*) FROM lexemes').fetchone()[0],
                    'pending':db.execute('SELECT COUNT(*) FROM sources WHERE status IN ("pending","needs_ocr")').fetchone()[0]
                }, 'engine':'Android local: PDF text, DOCX, TXT, MD; dovezi exacte și verificare umană. OCR scanări indisponibil în această ediție.'}

async def put_file(db, upload):
    fname=Path(upload.filename or 'document').name
    ext=Path(fname).suffix.lower()
    if ext not in SUPPORTED: raise HTTPException(415,f'Format nesuportat: {ext}. Acceptate: PDF, DOCX, TXT, MD, PNG, JPG.')
    content=await upload.read(MAX_FILE_SIZE+1)
    if len(content)>MAX_FILE_SIZE:raise HTTPException(413,'Document prea mare pentru încărcare (maxim 100 MB).')
    if not content:raise HTTPException(422,'Fișier gol.')
    sha=hashlib.sha256(content).hexdigest()
    prev=db.execute('SELECT id,title FROM sources WHERE sha256=?',(sha,)).fetchone()
    if prev:return {'id':prev['id'],'filename':fname,'duplicate':True,'message':'Fișierul identic există deja; nu a fost duplicat.'}
    safe_name=sha[:20]+ext
    target=UPLOAD_DIR/safe_name
    target.write_bytes(content)
    title=Path(fname).stem
    cur=db.execute('INSERT INTO sources(title,filename,format,sha256,file_path,status,added_at) VALUES(?,?,?,?,?,?,?)',
                   (title,fname,ext,sha,str(target),'pending',now()))
    audit(db,'source.upload',cur.lastrowid,fname)
    db.commit()
    return {'id':cur.lastrowid,'filename':fname,'duplicate':False,'message':'Adăugat în bibliografie. Apasă „Indexează sursele”.'}

@app.post('/api/sources/upload')
async def upload_sources(files: list[UploadFile]=File(...)):
    if len(files)>100:raise HTTPException(400,'Încarcă maximum 100 de fișiere per lot.')
    with database() as db:
        results=[]
        for file in files:results.append(await put_file(db,file))
        return {'files':results}

@app.post('/api/demo')
async def add_demo():
    """All demo events are fabricated, with explicit DEMO labeling."""
    class VirtualFile:
        def __init__(self,name,contents):self.filename=name;self.contents=contents.encode('utf-8')
        async def read(self,n):return self.contents
    files=[
     VirtualFile('DEMO-FICTIV_01-Moldova.txt',
      'DEMONSTRAȚIE FICTIVĂ — NU ESTE SURSĂ ISTORICĂ.\n\n'
      'În anul 1475, în Moldova, Ștefan cel Mare a fost menționat în documentul A. '
      'În anul 1475, un tratat între Moldova și Polonia a fost descris în documentul A.\n\n'
      'La 12 iunie 1476, Ștefan cel Mare s-a aflat în Polonia, potrivit documentului fictiv A. '
      'Documentul A nu oferă alte precizări despre acea deplasare.\n\n'
      'În secolul al XV-lea, un autor a descris Moldova. Această afirmație nu precizează anul.'),
     VirtualFile('DEMO-FICTIV_02-Polonia.txt',
      'DEMONSTRAȚIE FICTIVĂ — NU ESTE SURSĂ ISTORICĂ.\n\n'
      'În anul 1475, Polonia a fost menționată împreună cu Moldova în documentul B. '
      'Tratatul dintre Moldova și Polonia apare în documentul B.\n\n'
      'La 12 iunie 1476, documentul B îl menționează pe Ștefan cel Mare în Polonia. '
      'În anul 1477, în Țara Românească a fost menționat Vlad Țepeș.\n\n'
      'Nicio dată exactă nu a fost precizată pentru această afirmație separată.')
    ]
    with database() as db:
        out=[]
        for f in files:out.append(await put_file(db,f))
    return {'files':out,'warning':'Datele demonstrative sunt inventate și marcate ca atare.'}

@app.post('/api/index/run')
def index_sources(ocr:bool=False):
    with database() as db:
        pending=db.execute('SELECT * FROM sources WHERE status IN ("pending","error","needs_ocr") ORDER BY id').fetchall()
        results=[]
        for row in pending:
            src=dict(row)
            try:
                # Every source is isolated. A corrupt document can't block the rest.
                db.execute('DELETE FROM passages WHERE source_id=?',(src['id'],))
                pages,parts,issues=engine.create_passages(db,src['id'],src['file_path'],src['format'],use_ocr=ocr)
                warn=('Probleme sau notificări la '+str(len(issues))+' pagini: '+ '; '.join(issues[:12]) if issues else '')
                db.execute('UPDATE sources SET status=?,page_count=?,passage_count=?,warning=? WHERE id=?',
                           ('indexed' if parts else 'needs_ocr',pages,parts,warn,src['id']))
                audit(db,'source.index',src['id'],f'{pages} pagini; {parts} pasaje; OCR={ocr}')
                db.commit()
                results.append({'source':src['title'],'pages':pages,'passages':parts,'status':'indexed','warning':warn})
            except Exception as ex:
                db.rollback()
                db.execute('UPDATE sources SET status=?,warning=? WHERE id=?',('error',str(ex)[:300],src['id']))
                db.commit()
                results.append({'source':src['title'],'status':'error','error':str(ex)[:300]})
        if pending:
            try:
                engine.rebuild_mentions_and_lexemes(db)
                audit(db,'index.rebuild','universal',f'{len(pending)} surse')
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {'results':results,'message':f'{len(results)} surse procesate; indexul universal actualizat.'}

@app.get('/api/entities')
def entities(q:str='',kind:str='',limit:int=80):
    with database() as db:
        where=['EXISTS(SELECT 1 FROM mentions m WHERE m.entity_id=e.id)']; args=[]
        if kind and kind!='toate':where.append('e.kind=?');args.append(kind)
        if q:where.append('e.normalized LIKE ?');args.append('%'+engine.norm(q)+'%')
        stmt=('''SELECT e.*,COUNT(DISTINCT m.passage_id) AS appearances,COUNT(DISTINCT p.source_id) AS sources
                FROM entities e JOIN mentions m ON m.entity_id=e.id
                JOIN passages p ON p.id=m.passage_id WHERE ''' + ' AND '.join(where) +
                ' GROUP BY e.id ORDER BY appearances DESC,e.name COLLATE NOCASE LIMIT ?')
        args.append(min(300,max(1,limit)))
        return {'entities':[dict(r) for r in db.execute(stmt,args)]}

@app.get('/api/lexemes')
def lexemes(q:str='',limit:int=100):
    with database() as db:
        a=('%'+engine.norm(q)+'%',min(max(limit,1),300))
        return {'lexemes':[dict(r) for r in db.execute('SELECT * FROM lexemes WHERE form LIKE ? ORDER BY occurrences DESC LIMIT ?',a)]}

@app.get('/api/statements')
def statements(q:str='',limit:int=75):
    with database() as db:
        where='WHERE s.normalized LIKE ?' if q else ''
        args=(f'%{engine.norm(q)}%',) if q else ()
        res=db.execute(f'''SELECT s.id,s.text,COUNT(se.passage_id) AS attestations
             FROM statements s JOIN statement_evidence se ON se.statement_id=s.id {where}
             GROUP BY s.id ORDER BY attestations DESC,s.id LIMIT ?''',(*args,min(max(limit,1),300)))
        return {'statements':[dict(x) for x in res]}

@app.get('/api/entity/{id}')
def entity_detail(id:int,year:int|None=None,month:int|None=None,day:int|None=None,limit:int=250):
    with database() as db:
        entity=db.execute('SELECT * FROM entities WHERE id=?',(id,)).fetchone()
        if not entity:raise HTTPException(404,'Entitatea nu a fost găsită.')
        q='''SELECT p.*,s.title AS source_title,s.id AS sid,s.format
             FROM mentions m JOIN passages p ON m.passage_id=p.id
             JOIN sources s ON s.id=p.source_id WHERE m.entity_id=? ORDER BY s.title,p.page,p.seq LIMIT ?'''
        evidence=[dict(x) for x in db.execute(q,(id,min(max(limit,1),1000))) if engine.within_date(x,year,month,day)]
        other=db.execute('''SELECT e.id,e.name,e.kind,COUNT(DISTINCT m2.passage_id) AS shared_passages
            FROM mentions m1 JOIN mentions m2 ON m1.passage_id=m2.passage_id AND m2.entity_id<>m1.entity_id
            JOIN entities e ON e.id=m2.entity_id WHERE m1.entity_id=?
            GROUP BY e.id ORDER BY shared_passages DESC LIMIT 60''',(id,)).fetchall()
        return {'entity':dict(entity),'aliases':[x[0] for x in db.execute('SELECT alias FROM aliases WHERE entity_id=?',(id,))],
                'appearances':evidence,'overlaps':[dict(x) for x in other],
                'disclaimer':'Suprapunerile din aceeași afirmație nu demonstrează automat relații istorice.'}

@app.get('/api/overlaps')
def overlaps(ids:str='',year:int|None=None,month:int|None=None,day:int|None=None):
    with database() as db:
        try:lst=list(dict.fromkeys(int(x.strip()) for x in ids.split(',') if x.strip()))
        except ValueError:raise HTTPException(400,'ID-uri invalide.')
        if len(lst)>12:raise HTTPException(400,'Maximum 12 elemente simultan.')
        found=engine.passages_for(db,lst,year,500,month,day)
        entity_rows=[]
        if lst:
            entity_rows=[dict(x) for x in db.execute('SELECT id,name,kind FROM entities WHERE id IN ('+','.join('?'*len(lst))+')',lst)]
        return {'selected':entity_rows,'appearances':found,'count':len(found),
                'meaning':'Pasaje în care elementele sunt menționate împreună (nu relații deduse).'}

@app.get('/api/layers')
def layers(year:int|None=None,month:int|None=None,day:int|None=None,limit:int=14):
    with database() as db:
        places=[dict(x) for x in db.execute('''SELECT e.id,e.name,COUNT(DISTINCT m.passage_id) AS appearances
          FROM entities e JOIN mentions m ON e.id=m.entity_id WHERE e.kind='loc'
          GROUP BY e.id ORDER BY appearances DESC LIMIT ?''',(max(1,min(limit,40)),))]
        for pl in places:
            # Only literal co-appearance. If not attested as localization, interface says so.
            evidence=engine.passages_for(db,[pl['id']],year,200,month,day)
            pl['evidence_count']=len(evidence)
            pl['items']=[]
            seen=set()
            for p in evidence:
                others=db.execute('''SELECT e.id,e.name,e.kind FROM mentions m JOIN entities e ON e.id=m.entity_id
                    WHERE m.passage_id=? AND e.id<>? ORDER BY e.kind,e.name LIMIT 8''',(p['id'],pl['id']))
                for ent in others:
                    if ent['id'] in seen:continue
                    seen.add(ent['id'])
                    # classify only localized passage if explicitly contains 'în/din/la PLACE'
                    has_loc=bool(re.search(r'\b(?:în|din|la|spre)\s+'+re.escape(pl['name'])+r'\b',p['text'],re.I))
                    pl['items'].append({'id':ent['id'],'name':ent['name'],'kind':ent['kind'],
                                        'passage_id':p['id'],'co_mentioned':True,'location_claim':has_loc,
                                        'precision':p['precision'],'literal':p['time_literal']})
                    if len(pl['items'])>=18:break
                if len(pl['items'])>=18:break
        if year is not None:
            places=[p for p in places if p['evidence_count']>0]
        undated=db.execute('SELECT COUNT(*) FROM passages WHERE precision="nedatat"').fetchone()[0]
        unresolved=0
        if year is not None and month is not None:
            unresolved=db.execute('SELECT COUNT(*) FROM passages WHERE year_start<=? AND year_end>=? AND (month IS NULL OR month<>?'+(' OR day IS NULL OR day<>?' if day is not None else '')+')',
                        (year,year,month,*([day] if day is not None else []))).fetchone()[0]
        return {'year':year,'month':month,'day':day,'regions':places,'unresolved_time':unresolved,'undated_passages':undated,
                'warning':'Casetele reprezintă numai contextul atestat textual. Contiguitatea sau coapariția nu implică localizare ori legături istorice.'}

STOPWORDS=set('cine ce care unde cand când cum câte cati cât câți cu pe in în din de despre la sa să se si și este era sunt a au un o ce este era fost afla află aflau numele persoana persoanele ce spune sursa sursele textul pentru prin iar daca dacă toate tot al ale ai ale'.split())

def query_terms(q):
    terms=[]
    for t in engine.WORD.findall(q):
        s=engine.norm(t)
        if len(s)<3 or s in STOPWORDS:continue
        if s not in terms:terms.append(s)
    return terms[:20]

@app.get('/api/query')
def search(q:str,limit:int=180,offset:int=0):
    terms=query_terms(q)
    if not terms:
        return {'query':q,'terms':[],'hits':[],'sources':[],'total':0,'returned':0,
                'offset':0,'next_offset':None,'has_more':False,
                'warning':'Introdu termeni concreți pentru căutare.'}
    if not 0<=offset<=5_000_000:
        raise HTTPException(422,'Offset-ul trebuie să fie între 0 și 5.000.000.')
    limit=min(max(1,limit),500)
    with database() as db:
        match=' OR '.join('"'+t.replace('"','')+'"' for t in terms)
        try:
            total=db.execute('SELECT COUNT(*) FROM passage_fts WHERE passage_fts MATCH ?',(match,)).fetchone()[0]
            rows=db.execute('''SELECT p.id,p.source_id,p.page,p.seq,p.text,p.bbox,p.year_start,p.year_end,p.month,p.day,p.precision,p.time_literal,
                                s.title AS source_title,s.format,
                                bm25(passage_fts) AS rank
                          FROM passage_fts JOIN passages p ON passage_fts.rowid=p.id
                          JOIN sources s ON s.id=p.source_id WHERE passage_fts MATCH ?
                          ORDER BY rank,p.id LIMIT ? OFFSET ?''',(match,limit,offset)).fetchall()
        except Exception as e:
            raise HTTPException(400,'Interogare invalidă: '+str(e))
        hits=[]
        for p in rows:
            content=engine.norm(p['text'])
            present=[t for t in terms if re.search(r'\b'+re.escape(t)+r'\b',content)]
            # FTS and accent folding occasionally differ. Never fabricate a matching token.
            if not present:continue
            score=100*len(present)/len(terms)+sum(content.count(t) for t in present)
            if len(terms)>1 and ' '.join(terms) in content:score+=25
            hit=dict(p);hit['score']=round(score,2);hit['terms']=present
            hits.append(hit)
        hits.sort(key=lambda x:(-x['score'],x['source_title'],x['page']))
        bysource={}
        for h in hits:
            key=h['source_id']
            if key not in bysource:bysource[key]={'source_id':key,'title':h['source_title'],'hits':0,'tags':[]}
            bysource[key]['hits']+=1
            bysource[key]['tags'].append({'passage_id':h['id'],'page':h['page'],'excerpt':h['text'][:175],
                                          'time':h['time_literal'],'precision':h['precision']})
        more=offset+len(rows)<total
        return {'query':q,'terms':terms,'hits':hits,'sources':list(bysource.values()),
                'total':total,'returned':len(hits),'offset':offset,'next_offset':offset+len(rows) if more else None,
                'has_more':more,
                'warning':'Potriviri lexicale din textul indexat, cu paginare. Nu reprezintă indexare semantică exhaustivă. Fiecare pasaj trebuie verificat în original.'}

@app.get('/api/passages/{id}')
def passage_detail(id:int):
    with database() as db:
        p=db.execute('''SELECT p.*,s.title AS source_title,s.id AS sid,s.format,s.filename
                        FROM passages p JOIN sources s ON s.id=p.source_id WHERE p.id=?''',(id,)).fetchone()
        if not p:raise HTTPException(404,'Pasaj inexistent.')
        others=[dict(x) for x in db.execute('''SELECT p.id,p.seq,p.text FROM passages p WHERE p.source_id=? AND p.page=? ORDER BY p.seq''',(p['source_id'],p['page']))]
        associated=[dict(x) for x in db.execute('''SELECT DISTINCT e.id,e.name,e.kind FROM mentions m JOIN entities e ON e.id=m.entity_id WHERE m.passage_id=?''',(id,))]
        printed=db.execute('SELECT printed_label FROM printed_page_labels WHERE source_id=? AND pdf_page=?',(p['sid'],p['page'])).fetchone()
        return {'passage':{**dict(p),'printed_label':printed['printed_label'] if printed else None},'page_passages':others,'entities':associated}

@app.get('/api/passages/{id}/image')
def passage_image(id:int):
    with database() as db:
        row=db.execute('''SELECT p.text,p.page,p.bbox,s.file_path,s.format FROM passages p
            JOIN sources s ON s.id=p.source_id WHERE p.id=?''',(id,)).fetchone()
        if not row:raise HTTPException(404,'Pasaj inexistent.')
        if row['format'] in ('.png','.jpg','.jpeg'):
            return FileResponse(Path(row['file_path']),media_type='image/png' if row['format']=='.png' else 'image/jpeg',headers={'Cache-Control':'no-store'})
        if row['format']!='.pdf':raise HTTPException(404,'Imaginea originală este disponibilă pentru PDF sau imagine.')
        try:
            # Android PdfRenderer displays the untouched facsimile.
            # pypdf has no reliable bounding boxes for an exact highlight, so
            # the precise extracted quotation is shown separately in the viewer.
            from java import jclass
            png_b64=jclass('ro.historytool.mobile.PdfRender').renderBase64(
                str(row['file_path']),int(row['page'])-1,1.8)
            import base64
            return Response(content=base64.b64decode(str(png_b64)),media_type='image/png',
                            headers={'Cache-Control':'no-store'})
        except Exception as e:
            raise HTTPException(422,'Nu s-a putut reda pagina PDF pe Android: '+str(e)[:180])

@app.get('/api/sources/{id}/original')
def original_file(id:int):
    with database() as db:
        s=db.execute('SELECT file_path,filename,format FROM sources WHERE id=?',(id,)).fetchone()
        if not s:raise HTTPException(404,'Sursă inexistentă.')
        path=Path(s['file_path'])
        if not path.exists():raise HTTPException(410,'Fișierul original lipsește.')
        mt={'.pdf':'application/pdf','.txt':'text/plain; charset=utf-8','.md':'text/markdown; charset=utf-8',
            '.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg'}
        return FileResponse(path,media_type=mt.get(s['format']),filename=s['filename'],content_disposition_type='inline')


# Background indexing: UI stays responsive even for large bibliographies.
@app.post('/api/index/start')
def start_index(ocr:bool=False):
    global job
    if not index_lock.acquire(blocking=False):
        return {'status':'running','message':'Indexare deja în curs.'}
    job={'status':'running','started':now(),'finished':None,'result':None,'error':None,'ocr':ocr}
    def worker():
        try:
            outcome=index_sources(ocr=ocr)
            job.update(status='done',finished=now(),result=outcome)
        except Exception as exc:
            job.update(status='error',finished=now(),error=str(exc)[:800])
        finally:
            index_lock.release()
    threading.Thread(target=worker,name='historytool-index',daemon=True).start()
    return {'status':'running','message':'Indexare pornită în fundal.'}

@app.get('/api/index/progress')
def index_progress():
    with database() as db:
        status={k:db.execute('SELECT COUNT(*) FROM sources WHERE status=?',(k,)).fetchone()[0] for k in ('pending','indexed','error')}
    return {'job':job,'sources':status}

@app.get('/api/audit')
def get_audit(limit:int=100):
    with database() as db:
        return {'entries':[dict(r) for r in db.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT ?',(min(1000,max(1,limit)),))]}

@app.get('/api/verify')
def verify_sources():
    with database() as db:
        checked=[]
        for row in db.execute('SELECT id,title,sha256,file_path,page_count,passage_count,warning,status FROM sources'):
            f=Path(row['file_path'])
            current=hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
            x=dict(row);x.pop('file_path');x['integrity']='ok' if current==row['sha256'] else 'FIȘIER LIPSĂ/MODIFICAT'
            checked.append(x)
        return {'sources':checked,'verified':sum(s['integrity']=='ok' for s in checked),'total':len(checked),
                'note':'SHA-256 verifică integritatea fișierelor, nu corectitudinea OCR/semanticii.'}

@app.get('/api/backup')
def download_backup():
    temporary=Path(tempfile.mkdtemp(prefix='historytool-backup-'))
    outfile=temporary/'historytool_backup.zip'
    backupdb=temporary/'atlas.sqlite3'
    with database() as db:
        out=sqlite3.connect(str(backupdb))
        try:db.backup(out)
        finally:out.close()
        sources=[dict(row) for row in db.execute('SELECT id,filename,sha256,file_path FROM sources')]
    with zipfile.ZipFile(outfile,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=5,allowZip64=True) as z:
        z.write(backupdb,'data/atlas.sqlite3')
        for src in sources:
            f=Path(src['file_path'])
            if f.is_file():z.write(f,'data/sources/'+f.name)
        z.writestr('manifest.json',json.dumps({'exported_at':now(),'sources':[{'id':x['id'],'filename':x['filename'],'sha256':x['sha256']} for x in sources]},ensure_ascii=False,indent=2))
        z.writestr('RESTORE.txt','Oprește aplicația, apoi restabilește folderul data/ din această arhivă în directorul historytool. Păstrează o copie înainte de restaurare.\\n')
    return FileResponse(str(outfile),media_type='application/zip',filename='historytool_backup.zip',background=BackgroundTask(shutil.rmtree,temporary,ignore_errors=True))

@app.delete('/api/sources/{id}')
def delete_source(id:int):
    if index_lock.locked():raise HTTPException(409,'Așteaptă terminarea indexării.')
    with database() as db:
        src=db.execute('SELECT * FROM sources WHERE id=?',(id,)).fetchone()
        if not src:raise HTTPException(404,'Sursă inexistentă.')
        path=Path(src['file_path'])
        # Remove evidence first; never keep unsupported verified claims.
        db.execute('DELETE FROM sources WHERE id=?',(id,))
        db.execute('DELETE FROM statements WHERE NOT EXISTS (SELECT 1 FROM statement_evidence WHERE statement_id=statements.id)')
        db.execute('DELETE FROM verified_claims WHERE NOT EXISTS (SELECT 1 FROM verified_claim_evidence WHERE claim_id=verified_claims.id)')
        engine.rebuild_mentions_and_lexemes(db)
        audit(db,'source.delete',id,src['filename'])
        db.commit()
        if path.is_file():
            trash=DATA/'trash';trash.mkdir(exist_ok=True)
            dest=trash/path.name
            if not dest.exists():shutil.move(str(path),str(dest))
        return {'ok':True,'message':'Sursa a fost retrasă din index; fișierul se păstrează recuperabil în data/trash.'}

class NewEntity(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    kind:str='candidat'

@app.post('/api/entities')
def create_entity(v:NewEntity):
    allowed={'loc','persoană','eveniment','instituție','concept','acțiune','obiect','candidat','altul'}
    if v.kind not in allowed:raise HTTPException(422,'Categorie invalidă.')
    with database() as db:
        eid=engine.add_entity(db,v.name,v.kind,'candidat')
        engine.rebuild_mentions_and_lexemes(db)
        audit(db,'entity.create',eid,v.name)
        db.commit()
        return {'id':eid,'name':v.name,'status':'candidat','warning':'Candidat de identitate. Verificarea îi aparține istoricului.'}

# Verified claims use literal evidence only. Never generate a link between two entities
# on the basis of co-occurrence. Users explicitly attest (and can revoke) each link.
class ClaimAdd(BaseModel):
    passage_id:int
    subject_id:int
    predicate:str=Field(min_length=2,max_length=160)
    object_id:int|None=None
    object_literal:str=''
    place_id:int|None=None
    theme:str=''
    quote:str=''
    reviewed_by:str='istoric'

@app.post('/api/claims')
def create_claim(v:ClaimAdd):
    with database() as db:
        p=db.execute('SELECT * FROM passages WHERE id=?',(v.passage_id,)).fetchone()
        if not p:raise HTTPException(404,'Pasaj inexistent.')
        quote=v.quote.strip() or p['text']
        if quote not in p['text']:
            raise HTTPException(422,'Citatul trebuie să fie un fragment exact din pasajul original.')
        if engine.norm(v.predicate) not in engine.norm(quote):
            raise HTTPException(422,'Predicatul trebuie preluat literal din citatul ales, fără reformulare.')
        for label,eid in [('subiect',v.subject_id),('obiect',v.object_id),('loc',v.place_id)]:
            if eid is None:continue
            ent=db.execute('SELECT * FROM entities WHERE id=?',(eid,)).fetchone()
            if not ent:raise HTTPException(422,f'Entitatea {label} nu există.')
            literal=db.execute('SELECT 1 FROM mentions WHERE entity_id=? AND passage_id=?',(eid,v.passage_id)).fetchone()
            if not literal:raise HTTPException(422,f'Entitatea {label} nu este atestată explicit în pasaj; adaugă/confirmă mai întâi forma ei din sursă.')
        if v.object_literal and engine.norm(v.object_literal) not in engine.norm(quote):
            raise HTTPException(422,'Obiectul literal nu apare exact în citat.')
        key=[str(v.subject_id),engine.norm(v.predicate),str(v.object_id or ''),engine.norm(v.object_literal),str(v.place_id or ''),str(p['year_start']),str(p['year_end']),str(p['month']),str(p['day']),p['precision']]
        fingerprint=hashlib.sha256(json.dumps(key,ensure_ascii=False).encode('utf-8')).hexdigest()
        row=db.execute('SELECT id FROM verified_claims WHERE fingerprint=?',(fingerprint,)).fetchone()
        if row: cid=row['id']
        else:
            c=db.execute('''INSERT INTO verified_claims(fingerprint,subject_id,predicate,object_id,object_literal,place_id,theme,year_start,year_end,month,day,precision,quote,created_at,reviewed_by)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
             (fingerprint,v.subject_id,v.predicate.strip(),v.object_id,v.object_literal.strip(),v.place_id,v.theme.strip(),p['year_start'],p['year_end'],p['month'],p['day'],p['precision'],quote,now(),v.reviewed_by.strip() or 'istoric'))
            cid=c.lastrowid
        if v.theme.strip():
            db.execute('INSERT OR IGNORE INTO claim_themes(claim_id,theme) VALUES(?,?)',(cid,v.theme.strip()))
        db.execute('INSERT OR IGNORE INTO verified_claim_evidence(claim_id,passage_id) VALUES(?,?)',(cid,v.passage_id))
        audit(db,'claim.attest',cid,f'pasaj {v.passage_id}')
        db.commit()
        return {'ok':True,'id':cid,'deduplicated':bool(row),'message':'Afirmația explicită a fost atașată pasajului; atestările identice sunt grupate.'}

@app.get('/api/claims')
def get_claims(year:int|None=None,month:int|None=None,day:int|None=None,subject_id:int|None=None,place_id:int|None=None,limit:int=500):
    with database() as db:
        where=[];args=[]
        if subject_id is not None:where.append('c.subject_id=?');args.append(subject_id)
        if place_id is not None:where.append('c.place_id=?');args.append(place_id)
        sql='''SELECT c.*,sub.name subject, obj.name object_name, plc.name place,
            COUNT(ce.passage_id) AS attestations,MIN(ce.passage_id) AS passage_id, (SELECT GROUP_CONCAT(theme, ' / ') FROM claim_themes ct WHERE ct.claim_id=c.id) AS themes
            FROM verified_claims c JOIN entities sub ON sub.id=c.subject_id
            LEFT JOIN entities obj ON obj.id=c.object_id
            LEFT JOIN entities plc ON plc.id=c.place_id
            JOIN verified_claim_evidence ce ON ce.claim_id=c.id '''
        if where:sql+=' WHERE '+' AND '.join(where)
        sql+=' GROUP BY c.id ORDER BY c.id DESC LIMIT ?'
        data=[dict(x) for x in db.execute(sql,(*args,min(10000,max(1,limit))))]
        if year is not None:data=[x for x in data if engine.within_date(x,year,month,day)]
        return {'claims':data,'count':len(data),'meaning':'Numai afirmații înregistrate explicit și validate de utilizator, fiecare cu dovadă.'}

@app.get('/api/claims/{id}/evidence')
def claim_evidence(id:int):
    with database() as db:
        claim=db.execute('SELECT * FROM verified_claims WHERE id=?',(id,)).fetchone()
        if not claim:raise HTTPException(404,'Afirmație inexistentă.')
        rows=db.execute('''SELECT p.id,p.page,p.seq,p.text,s.id source_id,s.title source_title,s.format
             FROM verified_claim_evidence ce JOIN passages p ON ce.passage_id=p.id
             JOIN sources s ON s.id=p.source_id WHERE ce.claim_id=? ORDER BY s.title,p.page,p.seq''',(id,)).fetchall()
        return {'claim':dict(claim),'passages':[dict(r) for r in rows]}

@app.delete('/api/claims/{id}')
def delete_claim(id:int):
    with database() as db:
        if not db.execute('SELECT 1 FROM verified_claims WHERE id=?',(id,)).fetchone():raise HTTPException(404,'Afirmație inexistentă.')
        db.execute('DELETE FROM verified_claims WHERE id=?',(id,))
        audit(db,'claim.delete',id)
        db.commit()
        return {'ok':True}

@app.get('/api/context')
def context_frame(year:int|None=None,month:int|None=None,day:int|None=None):
    all_claims=get_claims(year,month,day,limit=10000)['claims']
    regions={}
    intersections={}
    unplaced=[]
    with database() as db:
        place_ids={r['id'] for r in db.execute("SELECT id FROM entities WHERE kind='loc'")}
    for cl in all_claims:
        # A claim involving two different named locations belongs to their
        # INTERSECTION, never gets duplicated as two independent claims.
        if cl['place_id'] and cl['object_id'] in place_ids and cl['object_id']!=cl['place_id']:
            keys=tuple(sorted([cl['place_id'],cl['object_id']]))
            if keys not in intersections:
                with database() as db:
                    label=[db.execute('SELECT name FROM entities WHERE id=?',(i,)).fetchone()['name'] for i in keys]
                intersections[keys]={'ids':keys,'names':label,'claims':[]}
            intersections[keys]['claims'].append(cl)
        elif cl['place_id']:
            rid=cl['place_id']
            if rid not in regions:regions[rid]={'id':rid,'name':cl['place'],'claims':[],'subjects':{}}
            bucket=regions[rid]
            bucket['claims'].append(cl)
            key=cl['subject_id']
            if key not in bucket['subjects']:bucket['subjects'][key]={'id':key,'name':cl['subject'],'claims':[]}
            bucket['subjects'][key]['claims'].append(cl)
        else:unplaced.append(cl)
    for reg in regions.values():reg['subjects']=list(reg['subjects'].values())
    return {'regions':list(regions.values()),'intersections':list(intersections.values()),'unplaced':unplaced,'total':len(all_claims),
      'caution':'Casetele reprezintă numai contexte verificate explicit. Nu sunt hărți geografice.'}



class SourceMetadataInput(BaseModel):
    title:str=Field(min_length=1,max_length=350)
    author:str=''
    edition:str=''
    archival_ref:str=''
    publication:str=''
    language:str=''
    remarks:str=''

@app.get('/api/sources/{id}/metadata')
def source_metadata(id:int):
    with database() as db:
        src=db.execute('SELECT id,title,filename,page_count,format FROM sources WHERE id=?',(id,)).fetchone()
        if not src:raise HTTPException(404,'Sursă inexistentă.')
        metadata=db.execute('SELECT * FROM source_metadata WHERE source_id=?',(id,)).fetchone()
        return {**dict(src),**(dict(metadata) if metadata else {}),
                'page_labels':[dict(x) for x in db.execute('SELECT pdf_page,printed_label FROM printed_page_labels WHERE source_id=? ORDER BY pdf_page',(id,))]}

@app.put('/api/sources/{id}/metadata')
def set_source_metadata(id:int,v:SourceMetadataInput):
    with database() as db:
        if not db.execute('SELECT 1 FROM sources WHERE id=?',(id,)).fetchone():raise HTTPException(404,'Sursă inexistentă.')
        db.execute('UPDATE sources SET title=? WHERE id=?',(v.title.strip(),id))
        db.execute('''INSERT INTO source_metadata(source_id,author,edition,archival_ref,publication,language,remarks)
            VALUES(?,?,?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET
            author=excluded.author,edition=excluded.edition,archival_ref=excluded.archival_ref,
            publication=excluded.publication,language=excluded.language,remarks=excluded.remarks''',
            (id,v.author.strip(),v.edition.strip(),v.archival_ref.strip(),v.publication.strip(),v.language.strip(),v.remarks.strip()))
        audit(db,'source.metadata',id,v.title)
        db.commit()
        return {'ok':True}

class PageLabelInput(BaseModel):
    printed_label:str=Field(max_length=75)

@app.put('/api/sources/{id}/pages/{page}/label')
def put_page_label(id:int,page:int,v:PageLabelInput):
    with database() as db:
        src=db.execute('SELECT page_count,format FROM sources WHERE id=?',(id,)).fetchone()
        if not src or src['format']!='.pdf':raise HTTPException(404,'PDF inexistent.')
        if not 1<=page<=src['page_count']:raise HTTPException(422,'Pagina fizică nu există în PDF.')
        label=v.printed_label.strip()
        if label:
            db.execute('INSERT INTO printed_page_labels(source_id,pdf_page,printed_label) VALUES(?,?,?) ON CONFLICT(source_id,pdf_page) DO UPDATE SET printed_label=excluded.printed_label',(id,page,label))
        else:db.execute('DELETE FROM printed_page_labels WHERE source_id=? AND pdf_page=?',(id,page))
        audit(db,'source.page_label',id,f'PDF p. {page} = {label}')
        db.commit()
        return {'ok':True,'source_id':id,'page':page,'printed_label':label}

class EntityUpdate(BaseModel):
    name:str|None=None
    kind:str|None=None
    status:str|None=None

@app.patch('/api/entities/{id}')
def change_entity(id:int,change:EntityUpdate):
    if change.kind and change.kind not in {'loc','persoană','eveniment','instituție','concept','acțiune','obiect','candidat','altul'}:
        raise HTTPException(422,'Categorie invalidă.')
    if change.status and change.status not in {'candidat','confirmat','controlat'}:raise HTTPException(422,'Statut invalid.')
    with database() as db:
        e=db.execute('SELECT * FROM entities WHERE id=?',(id,)).fetchone()
        if not e:raise HTTPException(404,'Entitate inexistentă.')
        new_name=(change.name or e['name']).strip()
        normalized=engine.norm(new_name)
        if len(new_name)<2:raise HTTPException(422,'Nume invalid.')
        taken=db.execute('SELECT id FROM entities WHERE normalized=? AND id<>?',(normalized,id)).fetchone()
        if taken:raise HTTPException(409,'Există deja o entitate cu acest nume; folosește alias sau fuziune verificată.')
        db.execute('UPDATE entities SET name=?,normalized=?,kind=?,status=? WHERE id=?',
          (new_name,normalized,change.kind or e['kind'],change.status or e['status'],id))
        db.commit()
        return {'ok':True,'id':id}

class AliasAdd(BaseModel):
    alias:str=Field(min_length=2,max_length=120)

@app.post('/api/entities/{id}/alias')
def add_alias(id:int,payload:AliasAdd):
    with database() as db:
        if not db.execute('SELECT 1 FROM entities WHERE id=?',(id,)).fetchone():raise HTTPException(404,'Entitate inexistentă.')
        k=engine.norm(payload.alias)
        existing=db.execute('SELECT entity_id FROM aliases WHERE alias=?',(k,)).fetchone()
        if existing and existing['entity_id']!=id:raise HTTPException(409,'Această formă aparține altei entități; nu unim identități fără verificare.')
        db.execute('INSERT OR IGNORE INTO aliases(alias,entity_id) VALUES(?,?)',(k,id))
        engine.rebuild_mentions_and_lexemes(db)
        audit(db,'entity.alias',id,payload.alias)
        db.commit()
        return {'ok':True,'message':'Alias adăugat. Toate aparițiile din corpus au fost actualizate.'}

class Merge(BaseModel):
    source_id:int
    confirmation:bool=False

@app.post('/api/entities/{target_id}/merge')
def merge_entities(target_id:int,p:Merge):
    if not p.confirmation:
        raise HTTPException(422,'Fuziunea trebuie confirmată explicit de istoric.')
    if target_id==p.source_id:
        raise HTTPException(422,'Aceeași entitate.')
    with database() as db:
        for eid in (target_id,p.source_id):
            if not db.execute('SELECT 1 FROM entities WHERE id=?',(eid,)).fetchone():
                raise HTTPException(404,'Entitate inexistentă.')
        # Remap every verified claim BEFORE removing the source identity.
        # Collision: preserve all evidence and thematic labels under one claim ID.
        affected=db.execute('''SELECT * FROM verified_claims WHERE subject_id=? OR object_id=? OR place_id=?
                             ORDER BY id''',(p.source_id,p.source_id,p.source_id)).fetchall()
        for cl in affected:
            subject=target_id if cl['subject_id']==p.source_id else cl['subject_id']
            obj=target_id if cl['object_id']==p.source_id else cl['object_id']
            place=target_id if cl['place_id']==p.source_id else cl['place_id']
            key=[str(subject),engine.norm(cl['predicate']),str(obj or ''),engine.norm(cl['object_literal']),
                 str(place or ''),str(cl['year_start']),str(cl['year_end']),str(cl['month']),str(cl['day']),cl['precision']]
            fingerprint=hashlib.sha256(json.dumps(key,ensure_ascii=False).encode('utf-8')).hexdigest()
            prior=db.execute('SELECT id FROM verified_claims WHERE fingerprint=? AND id<>?',(fingerprint,cl['id'])).fetchone()
            if prior:
                db.execute('''INSERT OR IGNORE INTO verified_claim_evidence(claim_id,passage_id)
                            SELECT ?,passage_id FROM verified_claim_evidence WHERE claim_id=?''',(prior['id'],cl['id']))
                db.execute('''INSERT OR IGNORE INTO claim_themes(claim_id,theme)
                            SELECT ?,theme FROM claim_themes WHERE claim_id=?''',(prior['id'],cl['id']))
                db.execute('DELETE FROM verified_claims WHERE id=?',(cl['id'],))
            else:
                db.execute('''UPDATE verified_claims SET fingerprint=?,subject_id=?,object_id=?,place_id=? WHERE id=?''',
                           (fingerprint,subject,obj,place,cl['id']))
        db.execute('''INSERT OR IGNORE INTO mentions(entity_id,passage_id,surface,start_pos,end_pos)
            SELECT ?,passage_id,surface,start_pos,end_pos FROM mentions WHERE entity_id=?''',(target_id,p.source_id))
        db.execute('UPDATE OR IGNORE aliases SET entity_id=? WHERE entity_id=?',(target_id,p.source_id))
        db.execute('DELETE FROM entities WHERE id=?',(p.source_id,))
        audit(db,'entity.merge',target_id,f'identitate {p.source_id}; {len(affected)} afirmații reatribuite')
        db.commit()
        return {'ok':True,'message':'Identitățile au fost unite; atestările și afirmațiile documentate au fost păstrate.'}

@app.get('/api/notes')
def get_notes():
    with database() as db:
        notes=[dict(x) for x in db.execute('SELECT * FROM notes ORDER BY updated_at DESC')]
        for n in notes:
            n['evidence']=[dict(x) for x in db.execute('''SELECT p.id,p.text,p.page,s.title AS source_title,s.id AS source_id,s.format FROM note_evidence ne JOIN passages p ON ne.passage_id=p.id JOIN sources s ON s.id=p.source_id WHERE ne.note_id=? ORDER BY ne.rowid''',(n['id'],))]
        return {'notes':notes}

class NoteData(BaseModel):
    id:int|None=None
    title:str='Proiect fără titlu'
    body:str=''

@app.post('/api/notes')
def save_note(note:NoteData):
    with database() as db:
        if note.id:
            if not db.execute('SELECT 1 FROM notes WHERE id=?',(note.id,)).fetchone():raise HTTPException(404,'Proiect inexistent.')
            db.execute('UPDATE notes SET title=?,body=?,updated_at=? WHERE id=?',(note.title,note.body,now(),note.id))
            nid=note.id
        else:
            c=db.execute('INSERT INTO notes(title,body,created_at,updated_at) VALUES(?,?,?,?)',(note.title,note.body,now(),now()))
            nid=c.lastrowid
        audit(db,'note.save',nid,note.title)
        db.commit()
        return {'id':nid,'ok':True}

class EvidenceToNote(BaseModel):
    passage_id:int

@app.post('/api/notes/{note_id}/evidence')
def add_evidence(note_id:int,v:EvidenceToNote):
    with database() as db:
        if not db.execute('SELECT 1 FROM notes WHERE id=?',(note_id,)).fetchone():raise HTTPException(404,'Proiect inexistent.')
        if not db.execute('SELECT 1 FROM passages WHERE id=?',(v.passage_id,)).fetchone():raise HTTPException(404,'Pasaj inexistent.')
        db.execute('INSERT OR IGNORE INTO note_evidence(note_id,passage_id) VALUES(?,?)',(note_id,v.passage_id))
        db.commit()
        return {'ok':True}

@app.get('/api/notes/{note_id}/export')
def export_note(note_id:int):
    with database() as db:
        note=db.execute('SELECT * FROM notes WHERE id=?',(note_id,)).fetchone()
        if not note:raise HTTPException(404,'Proiect inexistent.')
        evidence=db.execute('''SELECT p.text,p.page,s.title,s.filename,s.format,sm.author,sm.edition,sm.archival_ref,pl.printed_label
        FROM note_evidence ne JOIN passages p ON p.id=ne.passage_id JOIN sources s ON s.id=p.source_id
        LEFT JOIN source_metadata sm ON sm.source_id=s.id
        LEFT JOIN printed_page_labels pl ON pl.source_id=s.id AND pl.pdf_page=p.page
        WHERE ne.note_id=? ORDER BY ne.rowid''',(note_id,)).fetchall()
        output='# '+note['title']+'\n\n'+note['body']+'\n\n## Trimiteri la surse\n\n'
        for i,x in enumerate(evidence,1):
            position=('PDF p.' if x['format']=='.pdf' else 'segmentul')
            author=(x['author']+', ') if x['author'] else ''
            archival=('; '+x['archival_ref']) if x['archival_ref'] else ''
            printed=('; pagină tipărită '+x['printed_label']) if x['printed_label'] else ''
            output+=f'[{i}] {author}{x["title"]}, {position} {x["page"]}{printed}{archival} (fișier: {x["filename"]})\n> {x["text"]}\n\n'
        output+='\n---\nExportat din historytool. Verifică fiecare trimitere în documentul original.\n'
        return Response(content=output.encode('utf-8-sig'),media_type='text/markdown; charset=utf-8',
                        headers={'Content-Disposition':f'attachment; filename="proiect_{note_id}.md"'})

if __name__=='__main__':
    import uvicorn
    import webbrowser
    from threading import Timer
    port=int(os.environ.get('HISTORYTOOL_PORT',os.environ.get('ATLAS_PORT','8765')))
    print(f'\nhistorytool: http://127.0.0.1:{port}\nDate stocate local: {DATA}\n')
    if os.environ.get('HISTORYTOOL_NO_BROWSER',os.environ.get('ATLAS_NO_BROWSER'))!='1':
        Timer(1.2,lambda:webbrowser.open(f'http://127.0.0.1:{port}')).start()
    uvicorn.run(app,host='127.0.0.1',port=port,log_level='warning')
