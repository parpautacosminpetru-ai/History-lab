import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:hui_reader/database/catalog.dart';
import 'package:hui_reader/services/packages.dart';
import 'package:hui_reader/services/query.dart';

class NoNetwork extends HttpOverrides {
  @override
  HttpClient createHttpClient(SecurityContext? context) => throw StateError('Reader attempted network access');
}

void main() {
  late Directory temporary;
  late PackageStore store;
  final schema=File('assets/schema.sql').readAsStringSync();
  final normalization=File('assets/normalization.json').readAsStringSync();
  setUp(() async { temporary=await Directory.systemTemp.createTemp('hui-test-');store=PackageStore(temporary,schema); });
  tearDown(() async {await temporary.delete(recursive:true);});
  test('Python-exported package imports and deterministic queries match Python',() async {
    final directory=await store.importFile(File('test/fixtures/demo.hui'));
    final catalog=Catalog(directory,normalization);
    try {
      final vectors=jsonDecode(File('test/fixtures/queries.json').readAsStringSync()) as List;
      for(final vector in vectors) {
        final q=vector['query'] as Map<String,dynamic>;
        final query=Query(expression:q['expression'],mode:q['mode'],scope:q['scope'],
          sourceId:q['source_id'],editionId:q['edition_id'],author:q['author'],contextId:q['context_id'],
          nodeType:q['node_type'],relationType:q['relation_type'],statuses:(q['statuses'] as List).cast<String>(),
          yearStart:q['year_start'],yearEnd:q['year_end'],includeNegated:q['include_negated'],limit:q['limit'],offset:q['offset']);
        final expected=vector['segment_ids'];
        expect((await catalog.search(query)).map((r)=>r['segment_id']).toList(),expected,reason:'$q');
      }
      expect(catalog.db.select('PRAGMA query_only').single.values.single,1);
      final baseline=await catalog.search(const Query(expression:'domnie'));
      await HttpOverrides.runZoned(() async {
        expect(await catalog.search(const Query(expression:'domnie')),baseline);
      },createHttpClient:(_)=>throw StateError('Network is disabled'));
      expect(catalog.coverage()['Pagini procesate'],6);
      expect(catalog.coverage()['Caractere acoperite de adnotări confirmate'],18);
    } finally {catalog.close();}
  });
  test('Tampering fails without replacing the active catalog and update retains backup',() async {
    final first=await store.importFile(File('test/fixtures/demo.hui'));
    final bytes=await File('test/fixtures/demo.hui').readAsBytes();
    final header=ByteData.sublistView(bytes);
    final start=30+header.getUint16(26,Endian.little)+header.getUint16(28,Endian.little);
    bytes[start+100]^=1;
    final bad=File('${temporary.path}/corrupt.hui');await bad.writeAsBytes(bytes);
    await expectLater(store.importFile(bad),throwsA(anything));
    expect((await store.active())!.path,first.path);
    final second=await store.importFile(File('test/fixtures/demo.hui'));
    expect(second.path,isNot(first.path));
    expect(await File('${temporary.path}/active.backup.json').exists(),true);
  });
  test('Traversal and malformed ZIP are rejected',(){
    for(final path in ['../escape','/etc/passwd','C:/escape','pages\\escape','pages/../escape','pages//escape']) {
      expect(()=>safePackagePath(path),throwsFormatException);
    }
    expect(()=>checkZip(Uint8List(22)),throwsFormatException);
  });
}
