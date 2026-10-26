"""Deterministic SQL queries. No network, model, embeddings or generated answers."""
from __future__ import annotations

from dataclasses import dataclass
import re

from .db import normalize
from .semantics import STATUSES


def parse(expression: str):
    if len(expression)>4000:
        raise ValueError('Query is too long')
    tokens, position = [], 0
    pattern = re.compile(r'\s*("(?:[^"\\]|\\.)*"|\(|\)|\+|\bAND\b|\bOR\b|\bNOT\b|[^\s()+"]+)')
    while position < len(expression.rstrip()):
        match = pattern.match(expression,position)
        if not match:
            raise ValueError('Invalid query; use quoted terms and AND/OR/NOT')
        tokens.append(match.group(1))
        position = match.end()
    if not tokens:
        return None
    if len(tokens)>64:
        raise ValueError('At most 64 query tokens are allowed')
    cursor = 0

    def atom():
        nonlocal cursor
        if cursor>=len(tokens):
            raise ValueError('Expected a term')
        token = tokens[cursor]
        cursor += 1
        if token == 'NOT':
            return ('not',atom())
        if token == '(':
            result = disjunction()
            if cursor>=len(tokens) or tokens[cursor]!=')':
                raise ValueError('Unclosed parentheses')
            cursor += 1
            return result
        if token in (')','AND','OR','+'):
            raise ValueError('Expected a literal term')
        if token.startswith('"'):
            token = token[1:-1].replace('\\"','"').replace('\\\\','\\')
        if not token.strip():
            raise ValueError('Empty term')
        return ('term',token)

    def conjunction():
        nonlocal cursor
        result = atom()
        while cursor<len(tokens) and tokens[cursor] not in (')','OR'):
            if tokens[cursor] in ('AND','+'):
                cursor+=1
            result = ('and',result,atom())
        return result

    def disjunction():
        nonlocal cursor
        result = conjunction()
        while cursor<len(tokens) and tokens[cursor]=='OR':
            cursor+=1
            result = ('or',result,conjunction())
        return result

    result = disjunction()
    if cursor!=len(tokens):
        raise ValueError('Unexpected closing parenthesis')
    return result


def _compile(ast, atom):
    if ast is None:
        return '1'
    if ast[0]=='term':
        return atom(ast[1])
    if ast[0]=='not':
        return '(NOT '+_compile(ast[1],atom)+')'
    return '('+_compile(ast[1],atom)+(' AND ' if ast[0]=='and' else ' OR ')+_compile(ast[2],atom)+')'


@dataclass(frozen=True)
class Query:
    expression: str = ''
    mode: str = 'text'
    scope: str = 'passage'
    source_id: str | None = None
    edition_id: str | None = None
    author: str | None = None
    context_id: str | None = None
    node_type: str | None = None
    relation_type: str | None = None
    statuses: tuple[str,...] = ('human_confirmed',)
    year_start: int | None = None
    year_end: int | None = None
    include_negated: bool = False
    limit: int = 50
    offset: int = 0


def natural_query(text: str) -> Query:
    match = re.fullmatch(r'Unde apare (.+?) în legătură cu (.+?)\??',text.strip(),re.IGNORECASE)
    if not match:
        raise ValueError('Întrebare nerecunoscută. Alege termenii, modul și filtrele explicit.')
    if any('"' in term for term in match.groups()):
        raise ValueError('Selectează indicii folosind filtrele')
    return Query(expression=f'"{match[1]}" AND "{match[2]}"',mode='linked')


def build_sql(query: Query) -> tuple[str,list]:
    if query.mode not in ('text','index','linked') or query.scope not in ('passage','context','source'):
        raise ValueError('Unknown search mode or scope')
    if not query.statuses or not set(query.statuses)<=STATUSES:
        raise ValueError('Unknown verification status')
    if not 1<=query.limit<=200 or query.offset<0:
        raise ValueError('Invalid pagination')
    ast, params = parse(query.expression), []
    status_marks = ','.join('?' for _ in query.statuses)
    scope = {'passage': 'ts.id=t.id', 'context': 'ts.structure_id=t.structure_id',
             'source': 'ee.source_id=e.source_id'}[query.scope]

    def node_match(term, alias='n'):
        params.extend([normalize(term),normalize(term)])
        return f"({alias}.normalized_label=? OR EXISTS(SELECT 1 FROM NodeVariants nv WHERE nv.node_id={alias}.id AND nv.normalized_form=? AND nv.verification='human_confirmed'))"

    def atom(term):
        if query.mode=='text':
            # Literal FTS phrase, never interpolate untrusted FTS/SQL operators.
            params.append('"'+term.replace('"','""')+'"')
            return f'''EXISTS(SELECT 1 FROM SegmentFTS JOIN TextSegments ts ON ts.rowid=SegmentFTS.rowid
              JOIN Pages pp ON pp.id=ts.page_id JOIN SourceEditions ee ON ee.id=pp.edition_id
              WHERE {scope} AND SegmentFTS MATCH ?)'''
        params.extend(query.statuses)
        params.extend(query.statuses)
        matching = node_match(term)
        return f'''EXISTS(SELECT 1 FROM Occurrences o JOIN IndexNodes n ON n.id=o.node_id
          JOIN SpanParts sp ON sp.span_id=o.span_id JOIN TextSegments ts ON ts.id=sp.segment_id
          JOIN Pages pp ON pp.id=ts.page_id JOIN SourceEditions ee ON ee.id=pp.edition_id
          WHERE {scope} AND o.verification IN ({status_marks}) AND n.verification IN ({status_marks}) AND {matching})'''

    if query.mode=='linked':
        params.extend(query.statuses)
        params.extend(query.statuses)
        params.extend(query.statuses)
        def linked_atom(term):
            return '('+node_match(term,'sn')+' OR '+node_match(term,'onode')+')'
        expr = _compile(ast,linked_atom)
        expression = f'''EXISTS(SELECT 1 FROM ExplicitRelations er JOIN RelationEvidence re ON re.relation_id=er.id
          JOIN SpanParts sp ON sp.span_id=re.span_id JOIN TextSegments ts ON ts.id=sp.segment_id
          JOIN Pages pp ON pp.id=ts.page_id JOIN SourceEditions ee ON ee.id=pp.edition_id
          JOIN IndexNodes sn ON sn.id=er.subject_id JOIN IndexNodes onode ON onode.id=er.object_id
          WHERE {scope} AND er.verification IN ({status_marks}) AND sn.verification IN ({status_marks})
          AND onode.verification IN ({status_marks}) AND {expr}'''
        if not query.include_negated:
            expression += ' AND er.negated=0'
        if query.relation_type:
            expression+=' AND er.predicate=?'
            params.append(query.relation_type)
        expression+=')'
    else:
        expression = _compile(ast,atom)
    filters = [expression,"e.status='ready'"]
    for value, column in ((query.source_id,'s.id'),(query.edition_id,'e.id'),(query.context_id,'t.structure_id')):
        if value is not None:
            filters.append(column+'=?')
            params.append(value)
    if query.author:
        filters.append('EXISTS(SELECT 1 FROM SourceAuthors sa JOIN Authors a ON a.id=sa.author_id WHERE sa.source_id=s.id AND a.name=?)')
        params.append(query.author)
    if query.node_type or query.year_start is not None or query.year_end is not None:
        condition = ['np.segment_id=t.id',"no.verification='human_confirmed'","nn.verification='human_confirmed'"]
        if query.node_type:
            condition.append('nn.node_type=?')
            params.append(query.node_type)
        if query.year_start is not None:
            condition.append('coalesce(nn.year_end,nn.year_start)>=?')
            params.append(query.year_start)
        if query.year_end is not None:
            condition.append('nn.year_start<=?')
            params.append(query.year_end)
        filters.append('EXISTS(SELECT 1 FROM Occurrences no JOIN IndexNodes nn ON nn.id=no.node_id JOIN SpanParts np ON np.span_id=no.span_id WHERE '+' AND '.join(condition)+')')
    if query.relation_type and query.mode!='linked':
        filters.append("EXISTS(SELECT 1 FROM RelationEvidence re JOIN ExplicitRelations er ON er.id=re.relation_id JOIN SpanParts rp ON rp.span_id=re.span_id WHERE rp.segment_id=t.id AND er.predicate=? AND er.verification='human_confirmed'"+('' if query.include_negated else ' AND er.negated=0')+')')
        params.append(query.relation_type)
    params.extend([query.limit,query.offset])
    sql = '''SELECT t.id AS segment_id,t.original_text,t.structure_id,p.id AS page_id,p.pdf_page,p.printed_page,
      p.image_path,p.width,p.height,p.rotation,e.id AS edition_id,e.edition,e.original_path,e.sha256,
      s.id AS source_id,s.title,s.language,ds.title AS context_title,
      (SELECT group_concat(a.name, '; ') FROM SourceAuthors sa JOIN Authors a ON a.id=sa.author_id WHERE sa.source_id=s.id ORDER BY sa.position) AS authors
      FROM TextSegments t JOIN Pages p ON p.id=t.page_id JOIN SourceEditions e ON e.id=p.edition_id
      JOIN Sources s ON s.id=e.source_id LEFT JOIN DocumentStructures ds ON ds.id=t.structure_id WHERE '''
    sql+=' AND '.join(filters)+' ORDER BY s.title COLLATE BINARY,e.sha256,p.pdf_page,t.reading_order,t.id LIMIT ? OFFSET ?'
    return sql,params


def search(db, query: Query) -> list[dict]:
    sql,params = build_sql(query)
    results = []
    for row in db.execute(sql,params):
        item = dict(row)
        item['annotations'] = [dict(r) for r in db.execute('''SELECT o.id,o.node_id,n.canonical_label,n.node_type,o.verification,sp.start_offset,sp.end_offset
          FROM SpanParts sp JOIN Occurrences o ON o.span_id=sp.span_id JOIN IndexNodes n ON n.id=o.node_id
          WHERE sp.segment_id=? AND o.verification!='rejected' ORDER BY sp.start_offset,n.canonical_label,o.id''',(row['segment_id'],))]
        item['relations'] = [dict(r) for r in db.execute('''SELECT DISTINCT er.* FROM ExplicitRelations er JOIN RelationEvidence re ON re.relation_id=er.id
          JOIN SpanParts sp ON sp.span_id=re.span_id WHERE sp.segment_id=? AND er.verification!='rejected' ORDER BY er.id''',(row['segment_id'],))]
        results.append(item)
    return results
