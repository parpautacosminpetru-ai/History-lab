"""Deterministic evidence-indexing kernel. No historical inference is made.

Cross-mentions are NOT historical relationships; they are only evidence-context overlaps.
Entity names guessed from capitalization are flagged 'candidate'.
Every cited statement retains text and source location.
"""
from __future__ import annotations
import hashlib
import re
import shutil
import sqlite3
import unicodedata
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

DB_SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS sources (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, filename TEXT NOT NULL, format TEXT NOT NULL,
 sha256 TEXT NOT NULL UNIQUE, file_path TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
 page_count INTEGER DEFAULT 0, passage_count INTEGER DEFAULT 0, added_at TEXT NOT NULL,
 warning TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS source_metadata (
 source_id INTEGER PRIMARY KEY REFERENCES sources(id) ON DELETE CASCADE,
 author TEXT NOT NULL DEFAULT '', edition TEXT NOT NULL DEFAULT '',
 archival_ref TEXT NOT NULL DEFAULT '', publication TEXT NOT NULL DEFAULT '',
 language TEXT NOT NULL DEFAULT '', remarks TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS printed_page_labels (
 source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
 pdf_page INTEGER NOT NULL,
 printed_label TEXT NOT NULL,
 PRIMARY KEY(source_id,pdf_page)
);
CREATE TABLE IF NOT EXISTS passages (
 id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
 page INTEGER NOT NULL, seq INTEGER NOT NULL, text TEXT NOT NULL,
 bbox TEXT, ocr_used INTEGER DEFAULT 0, year_start INTEGER, year_end INTEGER, month INTEGER, day INTEGER, precision TEXT NOT NULL DEFAULT 'nedatat',
 time_literal TEXT DEFAULT '', UNIQUE(source_id,page,seq)
);
CREATE INDEX IF NOT EXISTS idx_passages_source ON passages(source_id,page,seq);
CREATE INDEX IF NOT EXISTS idx_passages_years ON passages(year_start,year_end);
CREATE VIRTUAL TABLE IF NOT EXISTS passage_fts USING fts5(text, content='passages',content_rowid='id',tokenize='unicode61 remove_diacritics 2');
CREATE TRIGGER IF NOT EXISTS passage_ai AFTER INSERT ON passages BEGIN
 INSERT INTO passage_fts(rowid,text) VALUES(new.id,new.text);
END;
CREATE TRIGGER IF NOT EXISTS passage_ad AFTER DELETE ON passages BEGIN
 INSERT INTO passage_fts(passage_fts,rowid,text) VALUES('delete',old.id,old.text);
END;
CREATE TABLE IF NOT EXISTS statements (
 id INTEGER PRIMARY KEY, normalized TEXT NOT NULL UNIQUE, text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS statement_evidence (
 statement_id INTEGER NOT NULL REFERENCES statements(id) ON DELETE CASCADE,
 passage_id INTEGER NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
 original TEXT NOT NULL, PRIMARY KEY(statement_id,passage_id,original)
);
CREATE TABLE IF NOT EXISTS entities (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, normalized TEXT NOT NULL UNIQUE,
 kind TEXT NOT NULL DEFAULT 'candidat', status TEXT NOT NULL DEFAULT 'candidat',
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS aliases (
 alias TEXT PRIMARY KEY, entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS mentions (
 entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
 passage_id INTEGER NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
 surface TEXT NOT NULL, start_pos INTEGER NOT NULL, end_pos INTEGER NOT NULL,
 PRIMARY KEY(entity_id,passage_id,start_pos,end_pos)
);
CREATE INDEX IF NOT EXISTS idx_mentions_entity ON mentions(entity_id,passage_id);
CREATE INDEX IF NOT EXISTS idx_mentions_passage ON mentions(passage_id,entity_id);
CREATE TABLE IF NOT EXISTS lexemes (
 form TEXT PRIMARY KEY, occurrences INTEGER NOT NULL DEFAULT 0, passages INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS verified_claims (
 id INTEGER PRIMARY KEY,
 fingerprint TEXT NOT NULL UNIQUE,
 subject_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE RESTRICT,
 predicate TEXT NOT NULL,
 object_id INTEGER REFERENCES entities(id) ON DELETE RESTRICT,
 object_literal TEXT NOT NULL DEFAULT '',
 place_id INTEGER REFERENCES entities(id) ON DELETE RESTRICT,
 theme TEXT NOT NULL DEFAULT '',
 year_start INTEGER,
 year_end INTEGER,
 month INTEGER,
 day INTEGER,
 precision TEXT NOT NULL DEFAULT 'nedatat',
 quote TEXT NOT NULL,
 created_at TEXT NOT NULL,
 reviewed_by TEXT NOT NULL DEFAULT 'istoric',
 status TEXT NOT NULL DEFAULT 'confirmat'
);
CREATE TABLE IF NOT EXISTS claim_themes (
 claim_id INTEGER NOT NULL REFERENCES verified_claims(id) ON DELETE CASCADE,
 theme TEXT NOT NULL, PRIMARY KEY(claim_id,theme)
);
CREATE TABLE IF NOT EXISTS verified_claim_evidence (
 claim_id INTEGER NOT NULL REFERENCES verified_claims(id) ON DELETE CASCADE,
 passage_id INTEGER NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
 PRIMARY KEY(claim_id,passage_id)
);
CREATE INDEX IF NOT EXISTS idx_claims_place ON verified_claims(place_id,year_start,year_end);
CREATE TABLE IF NOT EXISTS audit_log (
 id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, action TEXT NOT NULL,
 subject TEXT NOT NULL, info TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS notes (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS note_evidence (
 note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
 passage_id INTEGER NOT NULL REFERENCES passages(id) ON DELETE CASCADE,
 PRIMARY KEY(note_id,passage_id)
);
"""

COMMON_PLACES = [
 ('Moldova', ['Moldova','Moldovei','Moldovii','Moldovei']),
 ('Polonia',['Polonia','Poloniei']),
 ('Țara Românească',['Țara Românească','Țării Românești','Tara Romaneasca','Tarii Romanesti']),
 ('Transilvania',['Transilvania','Transilvaniei']),
 ('Ungaria',['Ungaria','Ungariei']),
 ('Europa',['Europa','Europei']),
 ('Cracovia',['Cracovia','Cracoviei']),
 ('Suceava',['Suceava','Sucevei']),
 ('Putna',['Putna','Putnei']),
 ('Iași',['Iași','Iașilor','Iasi','Iasilor']),
 ('Imperiul Otoman',['Imperiul Otoman','Imperiului Otoman']),
 ('București',['București','Bucuresti']),
 ('Franța',['Franța','Franței']),
 ('Italia',['Italia','Italiei']),
 ('Germania',['Germania','Germaniei']),
]
COMMON_PERSONS = [
 ('Ștefan cel Mare',['Ștefan cel Mare','Stefan cel Mare']),
 ('Vlad Țepeș',['Vlad Țepeș','Vlad Tepes']),
]
# Keep broad/capitalized guesses as suggestions, not verified entities.
BAD_CANDIDATE_WORDS = {'În','Din','La','Pe','Cu','De','Despre','Dar','Iar','Un','O','Și','El','Ea','Acesta','Aceasta',
 'Când','După','Pentru','Prin','Care','Unde','Apoi','Este','Sunt','Cel','Cele','A','Al','Ai','Ale','Se',
 'Secolul','Anul','Ziua','Luna','Textul','Sursa','Documentul','Capitolul','Regele','Domnul','Principele',
 'In','The','And','This','That','At','Of','However','Capitolul','România'}
ROMAN = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000}
WORD = re.compile(r"[\wĂÂÎȘȚăâîșț]+(?:[-’'][\wĂÂÎȘȚăâîșț]+)*", re.UNICODE)
YEAR = re.compile(r'(?<!\d)(1[0-9]{3}|2[0-1][0-9]{2}|[3-9][0-9]{2})(?!\d)')
CENTURY = re.compile(r'\b(?:sec(?:ol(?:ul|ului)?)?\.?|veacul|veacului)\s*(?:al\s*)?([IVXLCDM]{1,8})(?:[-‑–]lea)?\b', re.I)
DATE = re.compile(r'\b(0?[1-9]|[12]\d|3[01])\s+(ianuarie|februarie|martie|aprilie|mai|iunie|iulie|august|septembrie|octombrie|noiembrie|decembrie)\s+([1-9]\d{0,3})\b',re.I)
MONTH = re.compile(r'\b(ianuarie|februarie|martie|aprilie|mai|iunie|iulie|august|septembrie|octombrie|noiembrie|decembrie)\s+([1-9]\d{0,3})\b',re.I)
MONTHS=['ianuarie','februarie','martie','aprilie','mai','iunie','iulie','august','septembrie','octombrie','noiembrie','decembrie']
YEAR_RANGE = re.compile(r'\b(\d{3,4})\s*[–—-]\s*(\d{3,4})\b')
BCE_SUFFIX=re.compile(r'^\s*(?:î\s*\.?\s*Hr\.?|î\s*\.?\s*e\s*\.?\s*n\.?|BC\b|BCE\b)',re.I)
BCE_YEAR=re.compile(r'(?<!\d)([1-9][0-9]{0,3})\s*(?:î\s*\.?\s*Hr\.?|î\s*\.?\s*e\s*\.?\s*n\.?|BCE?\b)',re.I)
EXPLICIT_SMALL_YEAR=re.compile(r'\b(?:anul|anii|anilor|în\s+anul)\s+([1-9]\d{0,2})\b',re.I)
CANDIDATE = re.compile(r'(?<!\w)([A-ZĂÂÎȘȚ][a-zăâîșț]+(?:\s+(?:cel|cea|al|a|de|din|d[eiu]l|[A-ZĂÂÎȘȚ][a-zăâîșț]+)){1,4})(?!\w)')
SENT_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[„\"«A-ZĂÂÎȘȚ0-9])')


def norm(s: str) -> str:
    s = s.replace('ş','ș').replace('ţ','ț').replace('Ş','Ș').replace('Ţ','Ț')
    s = ''.join(ch for ch in unicodedata.normalize('NFKD',s) if not unicodedata.combining(ch))
    return re.sub(r'\s+',' ',s).casefold().strip()


def roman_to_num(s):
    s = s.upper(); result=0; previous=0
    for letter in reversed(s):
        n=ROMAN.get(letter,0)
        if n < previous: result-=n
        else: result+=n; previous=n
    return result


def get_dates(text):
    """Return only attested time precision. BCE years negative; 0 is never inferred."""
    exact = DATE.search(text)
    if exact:
        year=int(exact.group(3))
        return year,year,'zi',exact.group(0),MONTHS.index(exact.group(2).casefold())+1,int(exact.group(1))
    monthmatch=MONTH.search(text)
    if monthmatch:
        year=int(monthmatch.group(2))
        return year,year,'lună',monthmatch.group(0),MONTHS.index(monthmatch.group(1).casefold())+1,None
    ran = YEAR_RANGE.search(text)
    if ran:
        a,b=map(int,ran.groups())
        if 100<=a<=b<=2200 and b-a<=600:
            return a,b,'interval',ran.group(0),None,None
    bce=BCE_YEAR.search(text)
    if bce:
        y=-int(bce.group(1))
        return y,y,'an',bce.group(0),None,None
    year=YEAR.search(text)
    if year:
        y=int(year.group(1))
        return y,y,'an',year.group(0),None,None
    small=EXPLICIT_SMALL_YEAR.search(text)
    if small:
        y=int(small.group(1))
        return y,y,'an',small.group(0),None,None
    cent = CENTURY.search(text)
    if cent:
        c=roman_to_num(cent.group(1))
        if 1<=c<=40:
            if BCE_SUFFIX.match(text[cent.end():]):
                return -c*100,-((c-1)*100+1),'secol',text[cent.start():cent.end()+BCE_SUFFIX.match(text[cent.end():]).end()],None,None
            return (c-1)*100+1,c*100,'secol',cent.group(0),None,None
    return None,None,'nedatat','',None,None


def connect(path):
    db=sqlite3.connect(str(path),timeout=30)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript(DB_SCHEMA)
    # Small forward-compatible migration for preexisting 0.1 databases.
    if 'ocr_used' not in {c[1] for c in db.execute('PRAGMA table_info(passages)')}:
        db.execute('ALTER TABLE passages ADD COLUMN ocr_used INTEGER DEFAULT 0')
    return db


def add_entity(db,name,kind='candidat',status='candidat',aliases=()):
    n=norm(name)
    if not n: return None
    row=db.execute('SELECT id FROM entities WHERE normalized=?',(n,)).fetchone()
    if row: eid=row['id']
    else:
        cur=db.execute('INSERT INTO entities(name,normalized,kind,status,created_at) VALUES(?,?,?,?,?)',
          (name,n,kind,status,datetime.now(timezone.utc).isoformat()))
        eid=cur.lastrowid
    for a in [name,*aliases]:
        k=norm(a)
        existing=db.execute('SELECT entity_id FROM aliases WHERE alias=?',(k,)).fetchone()
        if not existing: db.execute('INSERT INTO aliases(alias,entity_id) VALUES(?,?)',(k,eid))
    return eid


def seed_entities(db):
    # A controlled place/person vocabulary helps navigation; appearances still require exact text.
    for name, aliases in COMMON_PLACES: add_entity(db,name,'loc','controlat',aliases)
    for name, aliases in COMMON_PERSONS: add_entity(db,name,'persoană','controlat',aliases)
    db.commit()


def split_sentences(text):
    # split sentences while preserving original text (except whitespace normalization)
    chunks=SENT_SPLIT.split(text.replace('\u00ad','').strip())
    output=[]
    for part in chunks:
        part=part.strip()
        if not part: continue
        if len(part)<=2400: output.append(part)
        else:
            # Avoid huge block UI while preserving each constituent string.
            for i in range(0,len(part),2200): output.append(part[i:i+2200])
    return output


def text_pages(filepath,ext,use_ocr=False):
    """Mobile import. Source page indices are preserved; OCR is never passed off as source text."""
    if ext=='.pdf':
        from pypdf import PdfReader
        reader=PdfReader(filepath,strict=False)
        for page_num,page in enumerate(reader.pages,1):
            issue='';ocr_used=0
            try:
                raw=page.extract_text(extraction_mode='layout') or ''
            except Exception as ex:
                raw='';issue='Extragere PDF nereușită: '+str(ex)[:150]
            if len(raw.strip())<12 and use_ocr:
                try:
                    from java import jclass
                    detected=str(jclass('ro.historytool.mobile.OfflineOcr').recognizePdfPage(str(filepath),page_num-1))
                    if detected.strip():
                        raw=detected;ocr_used=1
                        issue='OCR automat local, NECONFIRMAT; verifică textul în imaginea originală.'
                    else: issue='OCR nu a recunoscut textul; pagina nu este indexată.'
                except Exception as ex:
                    issue='OCR indisponibil/eroare: '+str(ex)[:160]
            out=[(sentence,None,ocr_used) for sentence in split_sentences(raw) if sentence.strip()]
            if not out and not issue:
                issue='Pagină PDF fără text selectabil; activează OCR pentru scanări.'
            yield page_num,out,issue
    elif ext in ('.jpg','.jpeg','.png'):
        raw='';issue='Imagine fără OCR; activează OCR pentru scanări.';ocr_used=0
        if use_ocr:
            try:
                from java import jclass
                raw=str(jclass('ro.historytool.mobile.OfflineOcr').recognizeImage(str(filepath)))
                issue=('OCR automat local, NECONFIRMAT; verifică textul în imaginea originală.'
                       if raw.strip() else 'Nu s-a recunoscut text în imagine.')
                ocr_used=1 if raw.strip() else 0
            except Exception as ex:
                issue='OCR indisponibil/eroare: '+str(ex)[:160]
        yield 1,[(sentence,None,ocr_used) for sentence in split_sentences(raw) if sentence.strip()],issue
    elif ext=='.docx':
        from zipfile import ZipFile
        from xml.etree import ElementTree as ET
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        with ZipFile(filepath) as z:
            root=ET.fromstring(z.read('word/document.xml'))
        parts=[]
        for paragraph in root.findall('.//w:p',ns):
            lines=[''.join(t.itertext()) for t in paragraph.findall('.//w:t',ns)]
            raw=''.join(lines).strip()
            if raw:parts.append(raw)
        for i in range(0,len(parts),24):
            yield 1+i//24,[(sent,None) for raw in parts[i:i+24] for sent in split_sentences(raw)],''
    else:
        text=Path(filepath).read_text(encoding='utf-8-sig',errors='replace')
        paras=[s.strip() for s in re.split(r'\n\s*\n',text) if s.strip()]
        if not paras:paras=[text]
        batch=[];size=0;page=1
        for para in paras:
            if size>=4500 and batch:
                yield page,batch,'';page+=1;batch=[];size=0
            for sent in split_sentences(para):
                batch.append((sent,None));size+=len(sent)
        if batch:yield page,batch,''

def detect_candidates(db):
    counts=defaultdict(int)
    for (t,) in db.execute('SELECT text FROM passages'):
        for m in CANDIDATE.finditer(t):
            s=m.group(1).strip(' .,;:()[]„”«»')
            tokens=s.split()
            while tokens and tokens[-1].casefold() in {'a','al','ai','ale','cel','cea','de','din','dupa','la','in','în'}:
                tokens.pop()
            s=' '.join(tokens)
            if len(tokens)<2 or tokens[0] in BAD_CANDIDATE_WORDS or len(s)>70: continue
            if norm(s) in {'tara romaneasca'}:continue
            counts[s]+=1
    # Discovery from literal capitalized named phrases. No identification claim.
    for name, c in counts.items():
        if c>=1: add_entity(db,name,'candidat','candidat')


def create_passages(db,src_id,path,ext,use_ocr=False):
    pages=0; passages=0; issues=[]
    for page_num,sentences,issue in text_pages(path,ext,use_ocr=use_ocr):
        pages+=1
        if issue:issues.append(f'pagina {page_num}: {issue}')
        for seq,item in enumerate(sentences):
            sentence,bbox=item[:2]
            ocr_used=item[2] if len(item)>2 else 0
            if not sentence.strip():continue
            a,b,granularity,datelabel,month,day=get_dates(sentence)
            cur=db.execute('INSERT INTO passages(source_id,page,seq,text,bbox,ocr_used,year_start,year_end,month,day,precision,time_literal) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                (src_id,page_num,seq,sentence,bbox,ocr_used,a,b,month,day,granularity,datelabel))
            pid=cur.lastrowid;passages+=1
            key=norm(re.sub(r'[\W_]+',' ',sentence,flags=re.UNICODE))
            if key:
                db.execute('INSERT OR IGNORE INTO statements(normalized,text) VALUES(?,?)',(key,sentence))
                sid=db.execute('SELECT id FROM statements WHERE normalized=?',(key,)).fetchone()[0]
                db.execute('INSERT OR IGNORE INTO statement_evidence(statement_id,passage_id,original) VALUES(?,?,?)',
                         (sid,pid,sentence))
    return pages,passages,issues


def rebuild_mentions_and_lexemes(db):
    db.execute('DELETE FROM mentions')
    db.execute('DELETE FROM lexemes')
    detect_candidates(db)
    aliased=defaultdict(list)
    for a,e in db.execute('SELECT alias,entity_id FROM aliases'): aliased[e].append(a)
    # Because casefold indexing offset doesn't preserve accents, use literal regex patterns for each alias.
    ent=db.execute('SELECT entities.id,aliases.alias FROM entities JOIN aliases ON entities.id=aliases.entity_id').fetchall()
    aliases=sorted([(r['id'],r['alias']) for r in ent], key=lambda x:-len(x[1]))
    # Avoid O(passages*aliases) for candidate-heavy corpora: compile a chunked alternation.
    alternatives=defaultdict(list)
    for eid,a in aliases: alternatives[a].append(eid)
    keys=sorted(alternatives,key=len,reverse=True)
    # Construct normalized map separately; regex Unicode case insensitive for source strings, with accent variants via norm offset mapping.
    # Only common (safe) alias forms, dedup exact. For each source passage, normalize each character and map offsets to original.
    compiled=[]
    for i in range(0,len(keys),350):
        chunk=keys[i:i+350]
        compiled.append(re.compile(r'(?<!\w)(?:'+'|'.join(re.escape(x) for x in chunk)+r')(?!\w)',re.I))
    lex=defaultdict(lambda:[0,0])
    for row in db.execute('SELECT id,text FROM passages'):
        pid,t=row
        normalized='';offsets=[]
        for i,ch in enumerate(t):
            converted=''.join(c for c in unicodedata.normalize('NFKD',ch) if not unicodedata.combining(c)).casefold()
            normalized+=converted
            offsets.extend([i]*len(converted))
        # scan aliases once per passage; each occurrence gets 1 identity and all exact positions.
        seen_positions=set()
        for pattern in compiled:
            for m in pattern.finditer(normalized):
                alias=m.group(0); ids=alternatives.get(alias,[])
                if len(ids)!=1:continue # avoid ambiguous aliases
                st=offsets[m.start()]; en=offsets[m.end()-1]+1
                pos=(st,en)
                if pos in seen_positions:continue
                seen_positions.add(pos)
                db.execute('INSERT OR IGNORE INTO mentions(entity_id,passage_id,surface,start_pos,end_pos) VALUES(?,?,?,?,?)',
                           (ids[0],pid,t[st:en],st,en))
        tokens=[norm(m.group()) for m in WORD.finditer(t)]
        for w in tokens:lex[w][0]+=1
        for w in set(tokens):lex[w][1]+=1
    db.executemany('INSERT INTO lexemes(form,occurrences,passages) VALUES(?,?,?)',
                   ((k,*v) for k,v in lex.items()))


def passages_for(db,ids,year=None,limit=100,month=None,day=None):
    """All selected entity IDs must be mentioned within same attested sentence (coappearance).
       This does not imply a historical relationship.
    """
    ids=[int(x) for x in ids]
    if not ids:return []
    placeholders=','.join('?' for _ in ids)
    q=f'''SELECT p.*,s.title AS source_title,s.format,s.id AS sid,
      GROUP_CONCAT(DISTINCT m.entity_id) AS entity_ids
    FROM passages p JOIN sources s ON s.id=p.source_id JOIN mentions m ON m.passage_id=p.id
    WHERE m.entity_id IN ({placeholders}) GROUP BY p.id HAVING COUNT(DISTINCT m.entity_id)=?
    ORDER BY s.title,p.page,p.seq LIMIT ?'''
    return [dict(x) for x in db.execute(q,(*ids,len(ids),limit)) if within_date(x,year,month,day)]


def within_date(p,year=None,month=None,day=None):
    """A missing month/day is never interpreted as a known month/day."""
    if year is None or year=='':return True
    a,b=p['year_start'],p['year_end']
    if a is None or not a<=int(year)<=b:return False
    if month is None:return True
    if p['precision'] not in ('lună','zi') or p['month']!=int(month):return False
    if day is None:return True
    return p['precision']=='zi' and p['day']==int(day)

def within_year(p,year):
    return within_date(p,year)
