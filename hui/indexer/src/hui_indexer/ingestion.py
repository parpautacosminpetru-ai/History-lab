"""Resumable, local-only PDF extraction. No document text is executable."""
from __future__ import annotations

import csv
import ctypes
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import pypdfium2 as pdfium
import pypdfium2.raw as raw

from . import __version__
from .db import normalize, stable_id, transaction

LANGUAGES = {'ro': 'ron', 'en': 'eng', 'fr': 'fra', 'de': 'deu', 'la': 'lat'}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _device_box(page, box):
    """PDFium applies crop box + intrinsic rotation, as it does when rendering."""
    width, height = page.get_size()
    device_w, device_h = math.ceil(width * 1000), math.ceil(height * 1000)
    left, bottom, right, top = box
    points = []
    for px, py in ((left, bottom), (left, top), (right, bottom), (right, top)):
        dx, dy = ctypes.c_int(), ctypes.c_int()
        if not raw.FPDF_PageToDevice(page, 0, 0, device_w, device_h, 0,
                                     px, py, ctypes.byref(dx), ctypes.byref(dy)):
            raise ValueError('PDF coordinate conversion failed')
        points.append((min(1., max(0., dx.value/device_w)),
                       min(1., max(0., dy.value/device_h))))
    return (min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points))


def extract_digital(page):
    textpage = page.get_textpage()
    try:
        text = textpage.get_text_range(force_this=True, errors='strict')
        # PDFium text indices are UTF-16 units. The database uses Unicode code points.
        utf16_to_cp, units = {0: 0}, 0
        for cp, char in enumerate(text):
            units += len(char.encode('utf-16-le')) // 2
            utf16_to_cp[units] = cp + 1
        boxes = []
        for char_index in range(textpage.count_chars()):
            unit = raw.FPDFText_GetTextIndexFromCharIndex(textpage, char_index)
            if unit not in utf16_to_cp or utf16_to_cp[unit] >= len(text):
                continue  # Excluded PDF control character, never fabricate alignment.
            start = utf16_to_cp[unit]
            if text[start].isspace():
                continue
            box = _device_box(page, textpage.get_charbox(char_index))
            boxes.append((start, start+1, *box, None))
        return text, boxes
    finally:
        textpage.close()


def extract_ocr(image_path: Path, language: str):
    language = LANGUAGES.get(language, language)
    if not re.fullmatch(r'[a-z]{3}(?:\+[a-z]{3})*', language):
        raise ValueError('Invalid Tesseract language code')
    if not shutil.which('tesseract'):
        raise RuntimeError('Tesseract is not installed; install it locally for OCR')
    result = subprocess.run(['tesseract', str(image_path.resolve()), 'stdout',
                             '-l', language, '--psm', '3', 'tsv'],
                            capture_output=True, text=True, encoding='utf-8', timeout=300)
    if result.returncode:
        raise RuntimeError('Tesseract: ' + result.stderr[-1000:])
    from PIL import Image
    with Image.open(image_path) as image:
        width, height = image.size
    parts, boxes, previous, offset, confidences = [], [], None, 0, []
    for row in csv.DictReader(io.StringIO(result.stdout), delimiter='\t', quoting=csv.QUOTE_NONE):
        word = row.get('text', '')
        if row.get('level') != '5' or not word.strip():
            continue
        line = tuple(row[k] for k in ('block_num', 'par_num', 'line_num'))
        separator = '' if previous is None else (' ' if line == previous else '\n')
        parts.extend([separator, word])
        offset += len(separator)
        x, y, w, h = (int(row[k]) for k in ('left', 'top', 'width', 'height'))
        confidence = max(0., min(100., float(row['conf']))) / 100
        boxes.append((offset, offset+len(word), x/width, y/height,
                      min(1., (x+w)/width), min(1., (y+h)/height), confidence))
        confidences.append(confidence)
        offset += len(word)
        previous = line
    return ''.join(parts), boxes, (sum(confidences)/len(confidences) if confidences else None)


def _issue(db, edition_id, page_id, category, detail):
    db.execute('INSERT OR IGNORE INTO Issues(id,edition_id,page_id,category,detail) VALUES(?,?,?,?,?)',
               (stable_id(edition_id,page_id,category,detail),edition_id,page_id,category,detail))


def import_pdf(db, workspace: Path, pdf: Path, *, title: str, authors: list[str] | None = None,
               language: str = 'und', edition: str = 'Ediție nespecificată',
               bibliographic_id: str | None = None, year: int | None = None,
               ocr_language: str | None = None, stop_after: int | None = None) -> str:
    """Commit each page once; interrupted imports resume without changing existing IDs."""
    workspace, pdf = Path(workspace).resolve(), Path(pdf).resolve()
    digest = sha256(pdf)
    edition_id = stable_id('edition',digest)
    existing = db.execute('SELECT * FROM SourceEditions WHERE sha256=?',(digest,)).fetchone()
    if existing and existing['status'] == 'ready':
        return existing['id']
    source_id = existing['source_id'] if existing else stable_id('source',bibliographic_id or
                                                               json.dumps([title,authors or [],year],ensure_ascii=False))
    document = pdfium.PdfDocument(str(pdf))
    try:
        if not len(document):
            raise ValueError('PDF has no pages')
        original_rel = f'originals/{digest}.pdf'
        original = workspace / original_rel
        original.parent.mkdir(parents=True,exist_ok=True)
        if not original.exists():
            temp = original.with_suffix('.tmp')
            shutil.copyfile(pdf,temp)
            if sha256(temp) != digest:
                temp.unlink(missing_ok=True)
                raise ValueError('PDF changed during import')
            temp.replace(original)
        elif sha256(original) != digest:
            raise ValueError('Managed original has changed')
        with transaction(db):
            db.execute('INSERT OR IGNORE INTO Sources(id,title,language,bibliographic_id,publication_year) VALUES(?,?,?,?,?)',
                       (source_id,title,language,bibliographic_id,year))
            for position, name in enumerate(authors or []):
                author_id = stable_id('author',source_id,position,name)
                db.execute('INSERT OR IGNORE INTO Authors VALUES(?,?)',(author_id,name))
                db.execute('INSERT OR IGNORE INTO SourceAuthors VALUES(?,?,?)',(source_id,author_id,position))
            db.execute('INSERT OR IGNORE INTO SourceEditions(id,source_id,edition,original_path,sha256,page_count,processing_version,language_hint) VALUES(?,?,?,?,?,?,?,?)',
                       (edition_id,source_id,edition,original_rel,digest,len(document),__version__,language))
            db.execute("INSERT OR REPLACE INTO ProcessingJobs(edition_id,stage,status,last_page) VALUES(?,'extraction','running',coalesce((SELECT last_page FROM ProcessingJobs WHERE edition_id=? AND stage='extraction'),0))",(edition_id,edition_id))
            db.execute("INSERT OR IGNORE INTO DocumentStructures(id,edition_id,kind,title,start_page,end_page,method) VALUES(?,?,'document',?,1,?,'import')",
                       (stable_id(edition_id,'root'),edition_id,title,len(document)))
        processed = 0
        for number in range(1,len(document)+1):
            page_id = stable_id(edition_id,'page',number)
            if db.execute('SELECT 1 FROM Pages WHERE id=?',(page_id,)).fetchone():
                continue
            page = document[number-1]
            try:
                width, height = page.get_size()
                text, boxes = extract_digital(page)
                method, confidence = 'pdf_text', None
                image_rel = f'pages/{edition_id}/{number}.png'
                image_path = workspace/image_rel
                image_path.parent.mkdir(parents=True,exist_ok=True)
                bitmap = page.render(scale=2)
                try:
                    bitmap.to_pil().save(image_path,format='PNG')
                finally:
                    bitmap.close()
                if not text.strip():
                    method = 'empty_or_scan'
                    if ocr_language:
                        text, boxes, confidence = extract_ocr(image_path,ocr_language)
                        method = 'tesseract'
                with transaction(db):
                    db.execute('INSERT INTO Pages(id,edition_id,pdf_page,width,height,rotation,image_path,raw_text,normalized_text,extraction_method,ocr_confidence,reading_order_uncertain) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                               (page_id,edition_id,number,width,height,page.get_rotation(),image_rel,text,
                                normalize(text),method,confidence,1))
                    if method == 'empty_or_scan':
                        _issue(db,edition_id,page_id,'missing_text','Pagină fără text extras: scanare sau pagină goală; OCR neexecutat.')
                    if method == 'tesseract':
                        _issue(db,edition_id,page_id,'ocr_review','Transcriere OCR neconfruntată cu imaginea originală.')
                    _issue(db,edition_id,page_id,'reading_order','Ordinea PDF/OCR necesită verificare, în special pentru coloane multiple.')
                    if language == 'und':
                        _issue(db,edition_id,page_id,'language','Limba nu a fost declarată; nu este ghicită automat.')
                    chapter = db.execute("SELECT id FROM DocumentStructures WHERE edition_id=? AND kind='chapter' ORDER BY start_page DESC,start_offset DESC LIMIT 1",(edition_id,)).fetchone()
                    parent = chapter['id'] if chapter else stable_id(edition_id,'root')
                    for match in re.finditer(r'(?im)^(?:capitolul|chapter|chapitre|kapitel|caput)\b[^\r\n]*',text):
                        structure = stable_id(edition_id,'chapter',number,match.start())
                        if parent != stable_id(edition_id,'root'):
                            db.execute('UPDATE DocumentStructures SET end_page=? WHERE id=?',(number,parent))
                        db.execute("INSERT INTO DocumentStructures(id,edition_id,parent_id,kind,title,start_page,end_page,start_offset,method) VALUES(?,?,?,'chapter',?,?,?,?, 'heading_rule')",
                                   (structure,edition_id,stable_id(edition_id,'root'),match.group(),number,len(document),match.start()))
                        parent = structure
                    if text:
                        segment_id = stable_id(page_id,'text')
                        # One lossless page segment. Finer manual structures can overlap it.
                        db.execute('INSERT INTO TextSegments VALUES(?,?,?,?,?,?,?,?)',
                                   (segment_id,page_id,parent,number,0,len(text),text,normalize(text)))
                        db.executemany('INSERT OR IGNORE INTO TextBoxes VALUES(?,?,?,?,?,?,?,?)',
                                       ((segment_id,*box) for box in boxes))
                    db.execute("UPDATE ProcessingJobs SET last_page=? WHERE edition_id=? AND stage='extraction'",(number,edition_id))
                processed += 1
                if stop_after and processed >= stop_after:
                    return edition_id
            finally:
                page.close()
        with transaction(db):
            methods = {r[0] for r in db.execute('SELECT extraction_method FROM Pages WHERE edition_id=?',(edition_id,))}
            kind = 'digital' if methods == {'pdf_text'} else ('mixed' if 'pdf_text' in methods else 'scanned_or_empty')
            db.execute("UPDATE SourceEditions SET status='ready',document_kind=? WHERE id=?",(kind,edition_id))
            db.execute("UPDATE ProcessingJobs SET status='complete',error=NULL WHERE edition_id=? AND stage='extraction'",(edition_id,))
        return edition_id
    except Exception as error:
        if db.execute('SELECT 1 FROM SourceEditions WHERE id=?',(edition_id,)).fetchone():
            with transaction(db):
                db.execute("UPDATE SourceEditions SET status='error' WHERE id=?",(edition_id,))
                db.execute("UPDATE ProcessingJobs SET status='error',error=? WHERE edition_id=? AND stage='extraction'",(str(error),edition_id))
        raise
    finally:
        document.close()


def correct_structure(db, structure_id: str, *, title: str, start_page: int, end_page: int,
                      reviewer: str):
    row = db.execute('SELECT * FROM DocumentStructures WHERE id=?',(structure_id,)).fetchone()
    if not row or not reviewer.strip():
        raise ValueError('Structure and reviewer are required')
    count = db.execute('SELECT page_count FROM SourceEditions WHERE id=?',(row['edition_id'],)).fetchone()[0]
    if not 1 <= start_page <= end_page <= count:
        raise ValueError('Structure range outside edition')
    with transaction(db):
        db.execute("UPDATE DocumentStructures SET title=?,start_page=?,end_page=?,verification='human_confirmed' WHERE id=?",
                   (title,start_page,end_page,structure_id))
        db.execute('INSERT INTO ReviewLog(target_type,target_id,previous_status,new_status,reviewer,note) VALUES(?,?,?,?,?,?)',
                   ('structure',structure_id,row['verification'],'human_confirmed',reviewer,'Corectare structură'))
