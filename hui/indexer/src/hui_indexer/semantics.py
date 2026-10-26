"""Stand-off annotation, technical validation, explicit human decisions."""
from __future__ import annotations

import json
import re
import uuid

from .db import normalize, stable_id, transaction, integrity, SCHEMA_VERSION

STATUSES = {'proposed','auto_validated','needs_review','human_confirmed','rejected'}
TARGETS = {'node': 'IndexNodes','occurrence': 'Occurrences','relation': 'ExplicitRelations',
           'span': 'EvidenceSpans','variant': 'NodeVariants'}


def create_node(db, label: str, node_type: str, language: str = 'und', *,
                disambiguation: str = '', node_id: str | None = None,
                year_start: int | None = None, year_end: int | None = None) -> str:
    if not label.strip() or not node_type.strip():
        raise ValueError('A label and explicit index type are required')
    # No merge based on spelling. Reuse requires an explicit existing ID.
    if node_id:
        if not db.execute('SELECT 1 FROM IndexNodes WHERE id=?',(node_id,)).fetchone():
            raise ValueError('Unknown canonical index')
        return node_id
    node_id = str(uuid.uuid4())
    with transaction(db):
        db.execute('INSERT INTO IndexNodes(id,canonical_label,normalized_label,node_type,language,disambiguation,verification,year_start,year_end) VALUES(?,?,?,?,?,?,\'proposed\',?,?)',
                   (node_id,label,normalize(label),node_type,language,disambiguation,year_start,year_end))
    return node_id


def create_span(db, parts: list[dict], *, method: str = 'manual', uncertainty: str = '') -> str:
    if not parts or len(parts)>1000:
        raise ValueError('Evidence must have 1–1000 parts')
    edition_id, previous = None, None
    canonical = []
    for part in parts:
        segment, start, end = part['segment_id'], part['start'], part['end']
        row = db.execute('SELECT t.*,p.edition_id,p.pdf_page FROM TextSegments t JOIN Pages p ON p.id=t.page_id WHERE t.id=?',(segment,)).fetchone()
        if not row or type(start) is not int or type(end) is not int or not 0<=start<end<=len(row['original_text']):
            raise ValueError('Evidence interval outside source text')
        if edition_id and edition_id != row['edition_id']:
            raise ValueError('One evidence span must belong to one edition')
        order = (row['pdf_page'],row['reading_order'],start)
        if previous and order <= previous:
            raise ValueError('Evidence parts must follow source reading order')
        previous, edition_id = order, row['edition_id']
        canonical.append((segment,start,end))
    span_id = stable_id('span',json.dumps(canonical))
    with transaction(db):
        if not db.execute('SELECT 1 FROM EvidenceSpans WHERE id=?',(span_id,)).fetchone():
            db.execute("INSERT INTO EvidenceSpans(id,edition_id,method,verification,uncertainty) VALUES(?,?,?,'auto_validated',?)",
                       (span_id,edition_id,method,uncertainty))
            db.executemany('INSERT INTO SpanParts VALUES(?,?,?,?,?)',
                           ((span_id,i,*part) for i,part in enumerate(canonical)))
    return span_id


def span_text(db, span_id: str) -> str:
    rows = db.execute('SELECT t.original_text,sp.start_offset,sp.end_offset FROM SpanParts sp JOIN TextSegments t ON t.id=sp.segment_id WHERE sp.span_id=? ORDER BY sp.position',(span_id,)).fetchall()
    if not rows:
        raise ValueError('Evidence span is empty or unknown')
    return '\n'.join(r['original_text'][r['start_offset']:r['end_offset']] for r in rows)


def annotate(db, node_id: str, parts: list[dict], *, quote: str | None = None,
             method: str = 'manual', language: str = 'und', uncertainty: str = '') -> str:
    with transaction(db):
        if not db.execute('SELECT 1 FROM IndexNodes WHERE id=?',(node_id,)).fetchone():
            raise ValueError('Unknown index node')
        span_id = create_span(db,parts,method=method,uncertainty=uncertainty)
        original = span_text(db,span_id)
        if quote is not None and original != quote:
            raise ValueError('Quoted text differs from the immutable source interval')
        occurrence_id = stable_id('occurrence',node_id,span_id)
        db.execute("INSERT OR IGNORE INTO Occurrences VALUES(?,?,?,?,?,?,'auto_validated')",
                   (occurrence_id,node_id,span_id,original,language,method))
    return occurrence_id


def add_variant(db, node_id: str, form: str, language: str, justification_span_id: str) -> str:
    if form not in span_text(db,justification_span_id):
        raise ValueError('Variant must occur literally in its justification')
    variant_id = stable_id('variant',node_id,form,language)
    with transaction(db):
        db.execute("INSERT OR IGNORE INTO NodeVariants VALUES(?,?,?,?,?,?,'proposed')",
                   (variant_id,node_id,form,normalize(form),language,justification_span_id))
    return variant_id


def _contains(db, outer_span: str, inner_span: str) -> bool:
    outer = db.execute('SELECT * FROM SpanParts WHERE span_id=?',(outer_span,)).fetchall()
    inner = db.execute('SELECT * FROM SpanParts WHERE span_id=?',(inner_span,)).fetchall()
    return bool(inner) and all(any(a['segment_id']==b['segment_id'] and
                               a['start_offset']<=b['start_offset']<b['end_offset']<=a['end_offset']
                               for a in outer) for b in inner)


def relation(db, subject_occurrence_id: str, predicate: str, object_occurrence_id: str,
             parts: list[dict], *, connector: str, negated: bool, modality: str,
             attribution: str, tense: str = '', uncertainty: str = '',
             method: str = 'manual', relation_id: str | None = None) -> str:
    if type(negated) is not bool or not modality.strip() or not predicate.strip():
        raise ValueError('Negation, modality and predicate must be supplied explicitly')
    with transaction(db):
        span_id = create_span(db,parts,method=method,uncertainty=uncertainty)
        evidence = span_text(db,span_id)
        if not connector or connector not in evidence:
            raise ValueError('The grammatical connector must be quoted literally')
        lowered = normalize(evidence)
        # Conservative safety gates, never an NLP claim of full understanding.
        if re.search(r'\b(nu|not|never|ne|pas|nicht|non)\b',lowered) and not negated:
            raise ValueError('Negation in evidence cannot become positive causality/relation')
        if re.search(r'\b(ar fi|could|might|may|would|pourrait|aurait|konnte|wurde|posset)\b',lowered) and modality in ('certain','assertive','cert'):
            raise ValueError('Conditional/uncertain evidence cannot become certain')
        if re.search(r'\b(presupune|considera|according to|suggests|suppose|vermutet)\b',lowered) and not attribution.strip():
            raise ValueError('Attributed evidence must preserve its voice')
        subject = db.execute('SELECT * FROM Occurrences WHERE id=?',(subject_occurrence_id,)).fetchone()
        obj = db.execute('SELECT * FROM Occurrences WHERE id=?',(object_occurrence_id,)).fetchone()
        if not subject or not obj or not _contains(db,span_id,subject['span_id']) or not _contains(db,span_id,obj['span_id']):
            raise ValueError('Relation endpoints must occur inside its evidence')
        values = (subject['node_id'],predicate,obj['node_id'],connector,int(negated),modality,attribution,tense)
        if relation_id:
            existing = db.execute('SELECT * FROM ExplicitRelations WHERE id=?',(relation_id,)).fetchone()
            if not existing or tuple(existing[k] for k in ('subject_id','predicate','object_id','connector','negated','modality','attribution','tense')) != values:
                raise ValueError('Recurring assertion must preserve identity, voice and certainty')
        else:
            relation_id = str(uuid.uuid4())
            db.execute("INSERT INTO ExplicitRelations(id,subject_id,predicate,object_id,connector,negated,modality,attribution,tense,verification) VALUES(?,?,?,?,?,?,?,?,?,'auto_validated')",
                       (relation_id,*values))
        db.execute('INSERT OR IGNORE INTO RelationEvidence VALUES(?,?,?,?)',
                   (relation_id,span_id,subject_occurrence_id,object_occurrence_id))
    return relation_id


def review(db, decisions: list[dict], *, reviewer: str, note: str = ''):
    if not reviewer.strip():
        raise ValueError('A human reviewer name is required')
    with transaction(db):
        for decision in decisions:
            table = TARGETS.get(decision['type'])
            status = decision['status']
            if not table or status not in ('human_confirmed','rejected','needs_review'):
                raise ValueError('Invalid human decision')
            row = db.execute(f'SELECT verification FROM {table} WHERE id=?',(decision['id'],)).fetchone()
            if not row:
                raise ValueError('Review target not found')
            db.execute(f'UPDATE {table} SET verification=? WHERE id=?',(status,decision['id']))
            db.execute('INSERT INTO ReviewLog(target_type,target_id,previous_status,new_status,reviewer,note) VALUES(?,?,?,?,?,?)',
                       (decision['type'],decision['id'],row[0],status,reviewer,note))


def validate(db) -> list[str]:
    integrity(db)
    problems = []
    for span in db.execute('SELECT id FROM EvidenceSpans'):
        try:
            span_text(db,span['id'])
        except ValueError as error:
            problems.append(str(error))
    for occurrence in db.execute('SELECT * FROM Occurrences'):
        if occurrence['original_form'] != span_text(db,occurrence['span_id']):
            problems.append('Occurrence quote mismatch: '+occurrence['id'])
    for row in db.execute('SELECT * FROM RelationEvidence'):
        for column in ('subject_occurrence_id','object_occurrence_id'):
            occurrence = db.execute('SELECT span_id FROM Occurrences WHERE id=?',(row[column],)).fetchone()
            if not _contains(db,row['span_id'],occurrence['span_id']):
                problems.append('Relation endpoint outside evidence: '+row['relation_id'])
    return problems


def publish(db, description: str = '') -> int:
    with transaction(db):
        problems = validate(db)
        if problems:
            raise ValueError('\n'.join(problems))
        pending = db.execute("SELECT count(*) FROM SourceEditions WHERE status!='ready'").fetchone()[0]
        if pending:
            raise ValueError('Finish or resume document extraction before publishing')
        cursor = db.execute('INSERT INTO IndexVersions(description,schema_version) VALUES(?,?)',(description,SCHEMA_VERSION))
        return cursor.lastrowid


def provenance(db, occurrence_id: str) -> dict:
    row = db.execute('''SELECT o.*,n.canonical_label,n.node_type,e.source_id,e.edition,e.original_path,e.sha256,s.title
      FROM Occurrences o JOIN IndexNodes n ON n.id=o.node_id
      JOIN EvidenceSpans es ON es.id=o.span_id JOIN SourceEditions e ON e.id=es.edition_id
      JOIN Sources s ON s.id=e.source_id WHERE o.id=?''',(occurrence_id,)).fetchone()
    if not row:
        raise ValueError('Occurrence not found')
    result = dict(row)
    result['parts'] = [dict(p) for p in db.execute('''SELECT sp.*,p.pdf_page,p.printed_page,p.image_path,
      p.width,p.height,p.rotation,t.structure_id FROM SpanParts sp JOIN TextSegments t ON t.id=sp.segment_id
      JOIN Pages p ON p.id=t.page_id WHERE sp.span_id=? ORDER BY sp.position''',(row['span_id'],))]
    result['text'] = span_text(db,row['span_id'])
    for part in result['parts']:
        part['boxes'] = [dict(b) for b in db.execute('SELECT * FROM TextBoxes WHERE segment_id=? AND start_offset<? AND end_offset>? ORDER BY start_offset',
                                                    (part['segment_id'],part['end_offset'],part['start_offset']))]
    return result
