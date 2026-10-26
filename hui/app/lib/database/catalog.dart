import 'dart:isolate';
import 'dart:io';
import 'package:path/path.dart' as p;
import 'package:sqlite3/sqlite3.dart';
import '../core/normalization.dart';
import '../services/query.dart';

typedef HuiRow = Map<String, Object?>;

List<HuiRow> rows(Database db, String sql, [List<Object?> parameters = const []]) =>
    db.select(sql, parameters).map((r) => Map<String, Object?>.from(r)).toList();

class Catalog {
  Catalog(this.root, this.normalizationData)
      : db = sqlite3.open(p.join(root.path, 'catalog.sqlite'), mode: OpenMode.readOnly) {
    db.execute('PRAGMA query_only=ON');
    db.execute('PRAGMA trusted_schema=OFF');
    db.execute('PRAGMA foreign_keys=ON');
    if (db.select('PRAGMA user_version').single.values.single != 1) {
      close();
      throw const FormatException('Versiune de schemă incompatibilă');
    }
  }
  final Directory root;
  final String normalizationData;
  final Database db;
  void close() => db.dispose();
  String asset(String relative) {
    if (relative.startsWith('/') || relative.contains('\\') || relative.contains(':') ||
        relative.split('/').any((v) => v == '..' || v == '.' || v.isEmpty)) {
      throw const FormatException('Cale documentară invalidă');
    }
    return p.joinAll([root.path, ...relative.split('/')]);
  }

  List<HuiRow> library() => rows(db, '''SELECT e.*,s.title,s.language,
    (SELECT group_concat(a.name, '; ') FROM SourceAuthors sa JOIN Authors a ON a.id=sa.author_id WHERE sa.source_id=s.id ORDER BY sa.position) AS authors,
    (SELECT count(*) FROM Pages pg WHERE pg.edition_id=e.id) AS processed_pages,
    (SELECT count(DISTINCT o.id) FROM Occurrences o JOIN EvidenceSpans es ON es.id=o.span_id WHERE es.edition_id=e.id) AS occurrence_count,
    (SELECT count(DISTINCT o.id) FROM Occurrences o JOIN EvidenceSpans es ON es.id=o.span_id WHERE es.edition_id=e.id AND o.verification='human_confirmed') AS confirmed_count
    FROM SourceEditions e JOIN Sources s ON s.id=e.source_id ORDER BY s.title COLLATE BINARY,e.sha256''');
  List<HuiRow> structures(String editionId) => rows(db,
    'SELECT * FROM DocumentStructures WHERE edition_id=? ORDER BY start_page,start_offset,id', [editionId]);
  List<HuiRow> pages(String editionId) => rows(db,
    'SELECT * FROM Pages WHERE edition_id=? ORDER BY pdf_page', [editionId]);
  List<HuiRow> annotations(String segmentId) => rows(db, '''SELECT o.*,n.canonical_label,n.node_type,n.disambiguation,sp.start_offset,sp.end_offset,es.uncertainty
    FROM SpanParts sp JOIN Occurrences o ON o.span_id=sp.span_id JOIN IndexNodes n ON n.id=o.node_id JOIN EvidenceSpans es ON es.id=sp.span_id
    WHERE sp.segment_id=? AND o.verification!='rejected' ORDER BY sp.start_offset,n.canonical_label,o.id''', [segmentId]);
  List<HuiRow> relations(String segmentId) => rows(db, '''SELECT DISTINCT er.*,sn.canonical_label AS subject_label,onode.canonical_label AS object_label
    FROM ExplicitRelations er JOIN RelationEvidence re ON re.relation_id=er.id JOIN SpanParts sp ON sp.span_id=re.span_id
    JOIN IndexNodes sn ON sn.id=er.subject_id JOIN IndexNodes onode ON onode.id=er.object_id
    WHERE sp.segment_id=? AND er.verification!='rejected' ORDER BY er.id''', [segmentId]);
  List<HuiRow> boxes(String segmentId, int start, int end) => rows(db,
    'SELECT * FROM TextBoxes WHERE segment_id=? AND start_offset<? AND end_offset>? ORDER BY start_offset',
    [segmentId,end,start]);
  List<HuiRow> sourceResults(String editionId, int pageNumber) => rows(db, '''SELECT t.id AS segment_id,t.original_text,t.structure_id,p.id AS page_id,p.pdf_page,p.printed_page,
    p.image_path,p.width,p.height,p.rotation,e.id AS edition_id,e.edition,e.original_path,e.sha256,
    s.id AS source_id,s.title,s.language,ds.title AS context_title
    FROM TextSegments t JOIN Pages p ON p.id=t.page_id JOIN SourceEditions e ON e.id=p.edition_id
    JOIN Sources s ON s.id=e.source_id LEFT JOIN DocumentStructures ds ON ds.id=t.structure_id
    WHERE e.id=? AND p.pdf_page=? ORDER BY t.reading_order''', [editionId,pageNumber]);
  List<HuiRow> occurrences(String nodeId) => rows(db, '''SELECT o.*,p.pdf_page,p.printed_page,p.edition_id,t.id AS segment_id,s.title,
    sp.start_offset,sp.end_offset FROM Occurrences o JOIN SpanParts sp ON sp.span_id=o.span_id
    JOIN TextSegments t ON t.id=sp.segment_id JOIN Pages p ON p.id=t.page_id
    JOIN SourceEditions e ON e.id=p.edition_id JOIN Sources s ON s.id=e.source_id
    WHERE o.node_id=? AND o.verification!='rejected' ORDER BY s.title COLLATE BINARY,e.sha256,p.pdf_page,o.id,sp.position''', [nodeId]);

  Future<List<HuiRow>> search(Query query) {
    final path = root.path, data = normalizationData;
    return Isolate.run(() {
      final db = sqlite3.open(p.join(path,'catalog.sqlite'), mode: OpenMode.readOnly);
      try {
        db.execute('PRAGMA query_only=ON');
        db.execute('PRAGMA trusted_schema=OFF');
        final compiled = buildQuery(query, TextNormalizer.fromJson(data));
        return rows(db, compiled.sql, compiled.parameters);
      } finally { db.dispose(); }
    });
  }

  List<HuiRow> matrix(String rowType, String columnType) => rows(db, '''SELECT a.node_id AS row_id,na.canonical_label AS row_label,
    b.node_id AS column_id,nb.canonical_label AS column_label,count(DISTINCT er.id) AS assertions
    FROM ExplicitRelations er JOIN RelationEvidence re ON re.relation_id=er.id
    JOIN Occurrences a ON a.id=re.subject_occurrence_id JOIN Occurrences b ON b.id=re.object_occurrence_id
    JOIN IndexNodes na ON na.id=a.node_id JOIN IndexNodes nb ON nb.id=b.node_id
    WHERE na.node_type=? AND nb.node_type=? AND er.verification='human_confirmed' AND er.negated=0
    AND na.verification='human_confirmed' AND nb.verification='human_confirmed'
    GROUP BY a.node_id,b.node_id ORDER BY row_label COLLATE BINARY,column_label COLLATE BINARY,row_id,column_id LIMIT 200''', [rowType,columnType]);

  Map<String,int> coverage() {
    final result = <String,int>{};
    const metrics = {
      'Documente importate':'SELECT count(*) AS n FROM SourceEditions',
      'Pagini fizice':'SELECT coalesce(sum(page_count),0) AS n FROM SourceEditions',
      'Pagini procesate':'SELECT count(*) AS n FROM Pages',
      'Pagini cu text':'SELECT count(*) AS n FROM Pages WHERE length(trim(raw_text))>0',
      'Transcrieri confruntate cu imaginea':'SELECT count(*) AS n FROM Pages WHERE transcription_verified=1',
      'Structuri detectate':'SELECT count(*) AS n FROM DocumentStructures',
      'Indici propuși':"SELECT count(*) AS n FROM IndexNodes WHERE verification!='rejected'",
      'Indici confirmați':"SELECT count(*) AS n FROM IndexNodes WHERE verification='human_confirmed'",
      'Relații propuse':"SELECT count(*) AS n FROM ExplicitRelations WHERE verification!='rejected'",
      'Relații confirmate':"SELECT count(*) AS n FROM ExplicitRelations WHERE verification='human_confirmed'",
      'Probleme nerezolvate':'SELECT count(*) AS n FROM Issues WHERE resolved=0',
      'Caractere extrase':'SELECT coalesce(sum(length(original_text)),0) AS n FROM TextSegments',
    };
    for (final entry in metrics.entries) {
      result[entry.key] = db.select(entry.value).single['n'] as int;
    }
    // Window functions union overlapping human-confirmed intervals before counting.
    final count = db.select('''WITH intervals AS (
      SELECT DISTINCT sp.segment_id,sp.start_offset AS a,sp.end_offset AS b FROM SpanParts sp
      WHERE EXISTS(SELECT 1 FROM Occurrences o WHERE o.span_id=sp.span_id AND o.verification='human_confirmed')
      OR EXISTS(SELECT 1 FROM RelationEvidence re JOIN ExplicitRelations er ON er.id=re.relation_id WHERE re.span_id=sp.span_id AND er.verification='human_confirmed')
    ), preceding AS (SELECT *,max(b) OVER(PARTITION BY segment_id ORDER BY a,b ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS previous_end FROM intervals)
    SELECT coalesce(sum(max(0,b-max(a,coalesce(previous_end,a)))),0) AS n FROM preceding''').single['n'] as int;
    result['Caractere acoperite de adnotări confirmate'] = count;
    result['Caractere fără adnotări confirmate'] = result['Caractere extrase']! - count;
    return result;
  }
}
