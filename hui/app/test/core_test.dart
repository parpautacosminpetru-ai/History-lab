import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hui_reader/core/normalization.dart';
import 'package:hui_reader/services/query.dart';
import 'package:hui_reader/widgets/source_viewer.dart';

void main() {
  final normalize=TextNormalizer.fromJson(File('assets/normalization.json').readAsStringSync());
  test('Unicode normalization is shared and source offsets remain code points',(){
    expect(normalize('ÎN ȚARĂ Straße ÉCOLE'),'in tara strasse ecole');
    expect(toCodePointOffset('A😀B',3),2);
    expect(toUtf16Offset('A😀B',2),3);
  });
  test('Boolean grammar, literal SQL parameters and constrained natural language',(){
    final sql=buildQuery(const Query(expression:'"domnie\'; DROP TABLE Sources;--"'),normalize);
    expect(sql.sql, isNot(contains('DROP TABLE')));
    expect(sql.parameters.first, contains('DROP TABLE'));
    expect(()=>parseQuery('X AND'), throwsFormatException);
    expect(()=>parseQuery('X OR (Y'), throwsFormatException);
    expect(naturalQuery('Unde apare Carol cel Mare în legătură cu Aachen?').mode,'linked');
    expect(()=>naturalQuery('Explică istoria'),throwsFormatException);
  });
  test('Normalized boxes follow page position and scale',(){
    final box=<String,Object?>{'x0':.1,'y0':.2,'x1':.4,'y1':.3};
    expect(normalizedBox(box,const Rect.fromLTWH(10,20,200,400)),const Rect.fromLTRB(30,100,90,140));
    expect(normalizedBox(box,const Rect.fromLTWH(0,0,1000,2000)),const Rect.fromLTRB(100,400,400,600));
  });
  test('Reader contains no inference provider or network client',(){
    for(final source in Directory('lib').listSync(recursive:true).whereType<File>().where((f)=>f.path.endsWith('.dart'))) {
      expect(RegExp(r'HttpClient\(|Socket\.connect|WebSocket\.connect|api\.openai|HUI_API_KEY|hui_indexer').hasMatch(source.readAsStringSync()),false,reason:source.path);
    }
  });
}
