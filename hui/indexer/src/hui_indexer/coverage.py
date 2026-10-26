def merge_ranges(ranges):
    merged = []
    for start,end in sorted(ranges):
        if merged and start<=merged[-1][1]:
            merged[-1] = (merged[-1][0],max(merged[-1][1],end))
        else:
            merged.append((start,end))
    return merged


def coverage(db):
    counts = {}
    for name,sql in {
        'documents_imported': 'SELECT count(*) FROM SourceEditions',
        'physical_pages': 'SELECT coalesce(sum(page_count),0) FROM SourceEditions',
        'pages_processed': 'SELECT count(*) FROM Pages',
        'pages_with_text': "SELECT count(*) FROM Pages WHERE length(trim(raw_text))>0",
        'transcriptions_verified': 'SELECT count(*) FROM Pages WHERE transcription_verified=1',
        'structures_detected': 'SELECT count(*) FROM DocumentStructures',
        'indices_proposed': "SELECT count(*) FROM IndexNodes WHERE verification!='rejected'",
        'indices_confirmed': "SELECT count(*) FROM IndexNodes WHERE verification='human_confirmed'",
        'relations_proposed': "SELECT count(*) FROM ExplicitRelations WHERE verification!='rejected'",
        'relations_confirmed': "SELECT count(*) FROM ExplicitRelations WHERE verification='human_confirmed'",
        'unresolved_issues': 'SELECT count(*) FROM Issues WHERE resolved=0',
    }.items():
        counts[name] = db.execute(sql).fetchone()[0]
    total, proposed, confirmed, gaps = 0,0,0,[]
    for segment in db.execute('SELECT id,original_text FROM TextSegments'):
        length = len(segment['original_text'])
        total += length
        ranges = {}
        for state in ('proposed','confirmed'):
            verification = "='human_confirmed'" if state=='confirmed' else "!='rejected'"
            rows = db.execute(f'''SELECT sp.start_offset,sp.end_offset FROM SpanParts sp
              WHERE sp.segment_id=? AND (EXISTS(SELECT 1 FROM Occurrences o WHERE o.span_id=sp.span_id AND o.verification{verification})
              OR EXISTS(SELECT 1 FROM RelationEvidence re JOIN ExplicitRelations er ON er.id=re.relation_id WHERE re.span_id=sp.span_id AND er.verification{verification}))''',(segment['id'],))
            ranges[state] = merge_ranges((r[0],r[1]) for r in rows)
        proposed += sum(b-a for a,b in ranges['proposed'])
        confirmed += sum(b-a for a,b in ranges['confirmed'])
        cursor = 0
        for start,end in ranges['confirmed']+[(length,length)]:
            if cursor<start:
                gaps.append({'segment_id':segment['id'],'start':cursor,'end':start})
            cursor = end
    counts.update(text_characters=total,annotated_characters=proposed,
                  human_verified_characters=confirmed,unclassified_intervals=gaps,
                  semantic_exhaustiveness='not_measured')
    return counts
