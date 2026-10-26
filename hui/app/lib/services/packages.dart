import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:archive/archive.dart';
import 'package:crypto/crypto.dart';
import 'package:path/path.dart' as p;
import 'package:sqlite3/sqlite3.dart';

String safePackagePath(String name) {
  if (!RegExp(r'^[A-Za-z0-9/_.-]+$').hasMatch(name) || name.startsWith('/') ||
      name.split('/').any((s) => s.isEmpty || s == '.' || s == '..') ||
      (name != 'catalog.sqlite' && name != 'manifest.json' &&
       !name.startsWith('originals/') && !name.startsWith('pages/'))) {
    throw const FormatException('Cale de arhivă nepermisă');
  }
  return name;
}

/// Inspect ZIP headers before decoding. Stored-only input bounds memory usage.
Set<String> checkZip(Uint8List bytes) {
  if (bytes.length > 256*1024*1024 || bytes.length < 22) {
    throw const FormatException('Pachet invalid sau mai mare de 256 MiB');
  }
  final view = ByteData.sublistView(bytes);
  int u16(int at) => view.getUint16(at, Endian.little);
  int u32(int at) => view.getUint32(at, Endian.little);
  var end = -1;
  for (var i=bytes.length-22; i>=0 && i>=bytes.length-65557; i--) {
    if (u32(i)==0x06054b50 && i+22+u16(i+20)==bytes.length) { end=i; break; }
  }
  if (end<0 || u16(end+4)!=0 || u16(end+6)!=0 || u16(end+8)!=u16(end+10) || u16(end+10)>50000) {
    throw const FormatException('ZIP multipart/ZIP64 neacceptat');
  }
  var offset = u32(end+16), total = 0;
  final centralEnd = offset+u32(end+12), names = <String>{}, portableNames=<String>{};
  if (centralEnd != end) throw const FormatException('Director ZIP invalid');
  for (var i=0; i<u16(end+10); i++) {
    if (offset+46>centralEnd || u32(offset)!=0x02014b50) throw const FormatException('Intrare ZIP invalidă');
    final flags=u16(offset+8), method=u16(offset+10), size=u32(offset+24);
    final nameLength=u16(offset+28), extra=u16(offset+30), comment=u16(offset+32);
    if (offset+46+nameLength+extra+comment>centralEnd || method!=0 || (flags & 9) != 0 || u32(offset+20)!=size) {
      throw const FormatException('HUI v1 cere fișiere ZIP stored, fără criptare');
    }
    final name=safePackagePath(utf8.decode(bytes.sublist(offset+46,offset+46+nameLength)));
    final mode = u32(offset+38)>>16, kind=mode & 0xf000;
    if (!names.add(name) || !portableNames.add(name.toLowerCase()) || ![0,0x8000].contains(kind)) throw const FormatException('Duplicat sau legătură simbolică');
    final local=u32(offset+42);
    if (local+30>u32(end+16) || u32(local)!=0x04034b50 || u16(local+6)!=flags || u16(local+8)!=method) {
      throw const FormatException('Antet ZIP local invalid');
    }
    final localName=u16(local+26), localExtra=u16(local+28), start=local+30+localName+localExtra;
    if (start+size>u32(end+16) || u32(local+18)!=size || u32(local+22)!=size ||
        utf8.decode(bytes.sublist(local+30,local+30+localName))!=name) {
      throw const FormatException('Date ZIP inconsistente');
    }
    total+=size;
    if (total>256*1024*1024 || (name=='manifest.json' && size>4*1024*1024)) {
      throw const FormatException('Arhivă prea mare');
    }
    offset+=46+nameLength+extra+comment;
  }
  if (offset!=centralEnd || !names.containsAll(['manifest.json','catalog.sqlite'])) {
    throw const FormatException('Fișiere obligatorii absente');
  }
  return names;
}

void validateCatalog(String path, String schema) {
  final db=sqlite3.open(path,mode:OpenMode.readOnly), reference=sqlite3.openInMemory();
  try {
    db.execute('PRAGMA trusted_schema=OFF');
    db.execute('PRAGMA query_only=ON');
    reference.execute(schema.replaceAll('\r\n','\n'));
    const sql="SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name";
    List<List<Object?>> fingerprint(Database d) => d.select(sql).map((row)=>row.values.toList()).toList();
    if (db.select('PRAGMA user_version').single.values.single!=1 ||
        jsonEncode(fingerprint(db))!=jsonEncode(fingerprint(reference))) {
      throw const FormatException('Schemă SQLite incompatibilă sau obiecte SQL necunoscute');
    }
    if (db.select('PRAGMA integrity_check').single.values.single!='ok' ||
        db.select('PRAGMA foreign_key_check').isNotEmpty || db.select('SELECT id FROM IndexVersions LIMIT 1').isEmpty) {
      throw const FormatException('Integritatea catalogului nu este validă');
    }
    if (db.select('''SELECT sp.span_id FROM SpanParts sp JOIN TextSegments t ON t.id=sp.segment_id
      JOIN Pages pg ON pg.id=t.page_id JOIN EvidenceSpans es ON es.id=sp.span_id
      WHERE sp.start_offset<0 OR sp.end_offset>length(t.original_text) OR sp.end_offset<=sp.start_offset OR es.edition_id!=pg.edition_id LIMIT 1''').isNotEmpty ||
        db.select("SELECT id FROM SourceEditions WHERE status!='ready' LIMIT 1").isNotEmpty) {
      throw const FormatException('Intervale sau documente incomplete');
    }
    const checks=[
      '''SELECT 1 FROM SpanParts WHERE typeof(start_offset)!='integer' OR typeof(end_offset)!='integer' LIMIT 1''',
      '''SELECT 1 FROM EvidenceSpans es WHERE NOT EXISTS(SELECT 1 FROM SpanParts sp WHERE sp.span_id=es.id) LIMIT 1''',
      '''SELECT 1 FROM TextSegments t JOIN Pages pg ON pg.id=t.page_id WHERE t.start_offset<0
        OR t.end_offset>length(pg.raw_text) OR t.end_offset<=t.start_offset
        OR t.original_text!=substr(pg.raw_text,t.start_offset+1,t.end_offset-t.start_offset) LIMIT 1''',
      '''SELECT 1 FROM TextBoxes b JOIN TextSegments t ON t.id=b.segment_id
        WHERE b.start_offset<0 OR b.end_offset>length(t.original_text) OR b.end_offset<=b.start_offset LIMIT 1''',
      '''SELECT 1 FROM RelationEvidence re JOIN ExplicitRelations er ON er.id=re.relation_id
        JOIN Occurrences so ON so.id=re.subject_occurrence_id JOIN Occurrences oo ON oo.id=re.object_occurrence_id
        WHERE so.node_id!=er.subject_id OR oo.node_id!=er.object_id LIMIT 1''',
      '''SELECT 1 FROM Occurrences o WHERE o.original_form!=(SELECT group_concat(piece,char(10)) FROM (
        SELECT substr(t.original_text,sp.start_offset+1,sp.end_offset-sp.start_offset) AS piece
        FROM SpanParts sp JOIN TextSegments t ON t.id=sp.segment_id WHERE sp.span_id=o.span_id ORDER BY sp.position)) LIMIT 1''',
      '''SELECT 1 FROM RelationEvidence re JOIN Occurrences o ON o.id=re.subject_occurrence_id OR o.id=re.object_occurrence_id
        JOIN SpanParts endpoint ON endpoint.span_id=o.span_id WHERE NOT EXISTS(
        SELECT 1 FROM SpanParts support WHERE support.span_id=re.span_id AND support.segment_id=endpoint.segment_id
        AND support.start_offset<=endpoint.start_offset AND support.end_offset>=endpoint.end_offset) LIMIT 1''',
      '''SELECT 1 FROM NodeVariants nv WHERE nv.justification_span_id IS NULL OR instr((SELECT group_concat(piece,char(10)) FROM (
        SELECT substr(t.original_text,sp.start_offset+1,sp.end_offset-sp.start_offset) AS piece
        FROM SpanParts sp JOIN TextSegments t ON t.id=sp.segment_id WHERE sp.span_id=nv.justification_span_id ORDER BY sp.position)),nv.original_form)=0 LIMIT 1''',
    ];
    for(final sql in checks) {
      if(db.select(sql).isNotEmpty)throw const FormatException('Dovezi, citate sau capete de relație inconsistente');
    }
    for (final row in db.select('SELECT original_path FROM SourceEditions')) { safePackagePath(row['original_path'] as String); }
    for (final row in db.select('SELECT image_path FROM Pages WHERE image_path IS NOT NULL')) { safePackagePath(row['image_path'] as String); }
  } finally { db.dispose(); reference.dispose(); }
}

class PackageStore {
  PackageStore(this.root, this.schema);
  final Directory root;
  final String schema;

  Future<Directory?> active() async {
    for (final name in ['active.json','active.backup.json']) {
      final file=File(p.join(root.path,name));
      if (!await file.exists()) continue;
      final data=jsonDecode(await file.readAsString()) as Map<String,dynamic>;
      final folder=data['folder'] as String;
      if (!RegExp(r'^index-[0-9]+$').hasMatch(folder)) throw const FormatException('Pointer invalid');
      final directory=Directory(p.join(root.path,folder));
      if (await File(p.join(directory.path,'catalog.sqlite')).exists()) {
        validateCatalog(p.join(directory.path,'catalog.sqlite'),schema);
        return directory;
      }
    }
    return null;
  }

  Future<Directory> importFile(File package) async {
    if (await package.length()>256*1024*1024) throw const FormatException('Limita Reader este 256 MiB per pachet');
    final bytes=await package.readAsBytes();
    final names=checkZip(bytes), archive=ZipDecoder().decodeBytes(bytes,verify:true);
    final manifestFile=archive.files.singleWhere((f)=>f.name=='manifest.json');
    final manifest=jsonDecode(utf8.decode(manifestFile.content as List<int>)) as Map<String,dynamic>;
    if (manifest['format']!='hui' || manifest['format_version']!=1 || manifest['schema_version']!=1 || manifest['includes_originals'] is! bool) {
      throw const FormatException('Versiune HUI incompatibilă');
    }
    final expected=manifest['files'] as Map<String,dynamic>;
    if (expected.length+1!=names.length || !expected.keys.every(names.contains) || !expected.containsKey('catalog.sqlite')) {
      throw const FormatException('Manifestul diferă de arhivă');
    }
    await root.create(recursive:true);
    final stage=await Directory(p.join(root.path,'.staging-${DateTime.now().microsecondsSinceEpoch}')).create();
    try {
      for (final file in archive.files) {
        if (file.name=='manifest.json') continue;
        final metadata=expected[file.name] as Map<String,dynamic>, data=file.content as List<int>;
        if (metadata['size']!=data.length || metadata['sha256']!=sha256.convert(data).toString()) {
          throw FormatException('Hash diferit: ${file.name}');
        }
        if (manifest['includes_originals']==false && (file.name.startsWith('pages/') || file.name.startsWith('originals/'))) {
          throw const FormatException('Documente nepermise într-un pachet doar cu index');
        }
        final target=File(p.joinAll([stage.path,...safePackagePath(file.name).split('/')]));
        await target.parent.create(recursive:true);
        await target.writeAsBytes(data,flush:true);
      }
      await File(p.join(stage.path,'manifest.json')).writeAsString(jsonEncode(manifest),flush:true);
      validateCatalog(p.join(stage.path,'catalog.sqlite'),schema);
      final db=sqlite3.open(p.join(stage.path,'catalog.sqlite'),mode:OpenMode.readOnly);
      try {
        if (manifest['index_version']!=db.select('SELECT max(id) AS n FROM IndexVersions').single['n']) {
          throw const FormatException('Versiunea indexului diferă de manifest');
        }
        if (manifest['includes_originals']==true) {
          for (final row in db.select('SELECT original_path,sha256 FROM SourceEditions')) {
            final original=File(p.joinAll([stage.path,...(row['original_path'] as String).split('/')]));
            if (!await original.exists() || sha256.convert(await original.readAsBytes()).toString()!=row['sha256']) {
              throw const FormatException('Identitatea PDF nu corespunde ediției');
            }
          }
          for (final row in db.select('SELECT image_path FROM Pages WHERE image_path IS NOT NULL')) {
            if (!names.contains(row['image_path'])) throw const FormatException('Imagine originală absentă');
          }
        }
      } finally { db.dispose(); }
      final folder='index-${DateTime.now().microsecondsSinceEpoch}';
      final installed=await stage.rename(p.join(root.path,folder));
      final next=File(p.join(root.path,'active.next.json'));
      await next.writeAsString(jsonEncode({'folder':folder}),flush:true);
      final active=File(p.join(root.path,'active.json')), backup=File(p.join(root.path,'active.backup.json'));
      if (await backup.exists()) await backup.delete();
      if (await active.exists()) await active.rename(backup.path);
      try { await next.rename(active.path); }
      catch (_) { if (await backup.exists()) await backup.copy(active.path); rethrow; }
      return installed;
    } finally { if (await stage.exists()) await stage.delete(recursive:true); }
  }
}
