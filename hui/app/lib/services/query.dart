import '../core/normalization.dart';

class Query {
  const Query({this.expression = '', this.mode = 'text', this.scope = 'passage',
    this.sourceId, this.editionId, this.author, this.contextId, this.nodeType,
    this.relationType, this.statuses = const ['human_confirmed'], this.yearStart,
    this.yearEnd, this.includeNegated = false, this.limit = 50, this.offset = 0});
  final String expression, mode, scope;
  final String? sourceId, editionId, author, contextId, nodeType, relationType;
  final List<String> statuses;
  final int? yearStart, yearEnd;
  final bool includeNegated;
  final int limit, offset;
}

class Expr {
  Expr(this.op, [this.term, this.left, this.right]);
  final String op;
  final String? term;
  final Expr? left, right;
}

Expr? parseQuery(String input) {
  if (input.length > 4000) throw const FormatException('Interogare prea lungă');
  final token = RegExp(r'\s*("(?:[^"\\]|\\.)*"|\(|\)|\+|\bAND\b|\bOR\b|\bNOT\b|[^\s()+"]+)');
  final tokens = <String>[];
  var position = 0;
  while (position < input.trimRight().length) {
    final match = token.matchAsPrefix(input, position);
    if (match == null) throw const FormatException('Interogare invalidă');
    tokens.add(match[1]!);
    position = match.end;
  }
  if (tokens.isEmpty) return null;
  if (tokens.length > 64) throw const FormatException('Maximum 64 de tokenuri');
  var cursor = 0;
  late Expr Function() disjunction;
  Expr atom() {
    if (cursor >= tokens.length) throw const FormatException('Lipsește termenul');
    var word = tokens[cursor++];
    if (word == 'NOT') return Expr('not', null, atom());
    if (word == '(') {
      final result = disjunction();
      if (cursor >= tokens.length || tokens[cursor++] != ')') {
        throw const FormatException('Paranteză neînchisă');
      }
      return result;
    }
    if ([')', 'AND', 'OR', '+'].contains(word)) {
      throw const FormatException('Lipsește un termen literal');
    }
    if (word.startsWith('"')) {
      word = word.substring(1, word.length-1).replaceAll(r'\"', '"').replaceAll(r'\\', r'\');
    }
    if (word.trim().isEmpty) throw const FormatException('Termen gol');
    return Expr('term', word);
  }
  Expr conjunction() {
    var result = atom();
    while (cursor < tokens.length && ![')', 'OR'].contains(tokens[cursor])) {
      if (['AND', '+'].contains(tokens[cursor])) cursor++;
      result = Expr('and', null, result, atom());
    }
    return result;
  }
  disjunction = () {
    var result = conjunction();
    while (cursor < tokens.length && tokens[cursor] == 'OR') {
      cursor++;
      result = Expr('or', null, result, conjunction());
    }
    return result;
  };
  final result = disjunction();
  if (cursor != tokens.length) throw const FormatException('Paranteză neașteptată');
  return result;
}

String compileExpr(Expr? expr, String Function(String) atom) {
  if (expr == null) return '1';
  if (expr.op == 'term') return atom(expr.term!);
  if (expr.op == 'not') return '(NOT ${compileExpr(expr.left, atom)})';
  return '(${compileExpr(expr.left, atom)} ${expr.op.toUpperCase()} ${compileExpr(expr.right, atom)})';
}

Query naturalQuery(String input) {
  final match = RegExp(r'^Unde apare (.+?) în legătură cu (.+?)\??$', caseSensitive: false).firstMatch(input.trim());
  if (match == null || match[1]!.contains('"') || match[2]!.contains('"')) {
    throw const FormatException('Întrebare nerecunoscută. Alege termenii și filtrele explicit.');
  }
  return Query(expression: '"${match[1]}" AND "${match[2]}"', mode: 'linked');
}

class SqlQuery {
  SqlQuery(this.sql, this.parameters);
  final String sql;
  final List<Object?> parameters;
}

SqlQuery buildQuery(Query q, TextNormalizer normalize) {
  const statuses = {'proposed', 'auto_validated', 'needs_review', 'human_confirmed', 'rejected'};
  if (!['text', 'index', 'linked'].contains(q.mode) ||
      !['passage', 'context', 'source'].contains(q.scope) ||
      q.statuses.isEmpty || !q.statuses.every(statuses.contains) ||
      q.limit < 1 || q.limit > 200 || q.offset < 0) {
    throw const FormatException('Filtre invalide');
  }
  final ast = parseQuery(q.expression), params = <Object?>[];
  final marks = List.filled(q.statuses.length, '?').join(',');
  final scope = {'passage':'ts.id=t.id', 'context':'ts.structure_id=t.structure_id',
    'source':'ee.source_id=e.source_id'}[q.scope]!;
  String nodeMatch(String term, String alias) {
    params.addAll([normalize(term), normalize(term)]);
    return "($alias.normalized_label=? OR EXISTS(SELECT 1 FROM NodeVariants nv WHERE nv.node_id=$alias.id AND nv.normalized_form=? AND nv.verification='human_confirmed'))";
  }
  String atom(String term) {
    if (q.mode == 'text') {
      params.add('"${term.replaceAll('"', '""')}"');
      return '''EXISTS(SELECT 1 FROM SegmentFTS JOIN TextSegments ts ON ts.rowid=SegmentFTS.rowid
        JOIN Pages pp ON pp.id=ts.page_id JOIN SourceEditions ee ON ee.id=pp.edition_id
        WHERE $scope AND SegmentFTS MATCH ?)''';
    }
    params.addAll([...q.statuses, ...q.statuses]);
    final matching = nodeMatch(term, 'n');
    return '''EXISTS(SELECT 1 FROM Occurrences o JOIN IndexNodes n ON n.id=o.node_id
      JOIN SpanParts sp ON sp.span_id=o.span_id JOIN TextSegments ts ON ts.id=sp.segment_id
      JOIN Pages pp ON pp.id=ts.page_id JOIN SourceEditions ee ON ee.id=pp.edition_id
      WHERE $scope AND o.verification IN ($marks) AND n.verification IN ($marks) AND $matching)''';
  }
  String expression;
  if (q.mode == 'linked') {
    params.addAll([...q.statuses, ...q.statuses, ...q.statuses]);
    final expr = compileExpr(ast, (term) => '(${nodeMatch(term, 'sn')} OR ${nodeMatch(term, 'onode')})');
    expression = '''EXISTS(SELECT 1 FROM ExplicitRelations er JOIN RelationEvidence re ON re.relation_id=er.id
      JOIN SpanParts sp ON sp.span_id=re.span_id JOIN TextSegments ts ON ts.id=sp.segment_id
      JOIN Pages pp ON pp.id=ts.page_id JOIN SourceEditions ee ON ee.id=pp.edition_id
      JOIN IndexNodes sn ON sn.id=er.subject_id JOIN IndexNodes onode ON onode.id=er.object_id
      WHERE $scope AND er.verification IN ($marks) AND sn.verification IN ($marks)
      AND onode.verification IN ($marks) AND $expr''';
    if (!q.includeNegated) expression += ' AND er.negated=0';
    if (q.relationType != null) {
      expression += ' AND er.predicate=?';
      params.add(q.relationType);
    }
    expression += ')';
  } else {
    expression = compileExpr(ast, atom);
  }
  final filters = [expression, "e.status='ready'"];
  for (final entry in {'s.id':q.sourceId, 'e.id':q.editionId, 't.structure_id':q.contextId}.entries) {
    if (entry.value != null) { filters.add('${entry.key}=?'); params.add(entry.value); }
  }
  if (q.author != null) {
    filters.add('EXISTS(SELECT 1 FROM SourceAuthors sa JOIN Authors a ON a.id=sa.author_id WHERE sa.source_id=s.id AND a.name=?)');
    params.add(q.author);
  }
  if (q.nodeType != null || q.yearStart != null || q.yearEnd != null) {
    final conditions = ['np.segment_id=t.id', "no.verification='human_confirmed'", "nn.verification='human_confirmed'"];
    if (q.nodeType != null) { conditions.add('nn.node_type=?'); params.add(q.nodeType); }
    if (q.yearStart != null) { conditions.add('coalesce(nn.year_end,nn.year_start)>=?'); params.add(q.yearStart); }
    if (q.yearEnd != null) { conditions.add('nn.year_start<=?'); params.add(q.yearEnd); }
    filters.add('EXISTS(SELECT 1 FROM Occurrences no JOIN IndexNodes nn ON nn.id=no.node_id JOIN SpanParts np ON np.span_id=no.span_id WHERE ${conditions.join(' AND ')})');
  }
  if (q.relationType != null && q.mode != 'linked') {
    filters.add("EXISTS(SELECT 1 FROM RelationEvidence re JOIN ExplicitRelations er ON er.id=re.relation_id JOIN SpanParts rp ON rp.span_id=re.span_id WHERE rp.segment_id=t.id AND er.predicate=? AND er.verification='human_confirmed'${q.includeNegated ? '' : ' AND er.negated=0'})");
    params.add(q.relationType);
  }
  params.addAll([q.limit, q.offset]);
  return SqlQuery('''SELECT t.id AS segment_id,t.original_text,t.structure_id,p.id AS page_id,p.pdf_page,p.printed_page,
    p.image_path,p.width,p.height,p.rotation,e.id AS edition_id,e.edition,e.original_path,e.sha256,
    s.id AS source_id,s.title,s.language,ds.title AS context_title,
    (SELECT group_concat(a.name, '; ') FROM SourceAuthors sa JOIN Authors a ON a.id=sa.author_id WHERE sa.source_id=s.id ORDER BY sa.position) AS authors
    FROM TextSegments t JOIN Pages p ON p.id=t.page_id JOIN SourceEditions e ON e.id=p.edition_id
    JOIN Sources s ON s.id=e.source_id LEFT JOIN DocumentStructures ds ON ds.id=t.structure_id
    WHERE ${filters.join(' AND ')} ORDER BY s.title COLLATE BINARY,e.sha256,p.pdf_page,t.reading_order,t.id LIMIT ? OFFSET ?''', params);
}
