import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hui_reader/database/catalog.dart';
import 'package:hui_reader/main.dart';
import 'package:hui_reader/services/packages.dart';
import 'package:hui_reader/widgets/source_viewer.dart';

void main() {
  testWidgets('Source → exact page → index → distinct occurrence → source navigation', (tester) async {
    late Directory temp;
    late Catalog catalog;
    final normalization=File('assets/normalization.json').readAsStringSync();
    await tester.runAsync(() async {
      temp=await Directory.systemTemp.createTemp('hui-widget-');
      final store=PackageStore(temp,File('assets/schema.sql').readAsStringSync());
      final root=await store.importFile(File('test/fixtures/demo.hui'));
      catalog=Catalog(root,normalization);
    });
    await tester.pumpWidget(HuiApp(initialCatalog:catalog,normalization:normalization));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Demonstrație originală 1'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('PDF 2'));
    await tester.pumpAndSettle();
    expect(find.text('Pagina PDF 2'),findsOneWidget);
    await tester.ensureVisible(find.text('domnie'));
    await tester.tap(find.text('domnie'));
    await tester.pumpAndSettle();
    expect(find.text('Demonstrație originală 1 / PDF 2'),findsOneWidget);
    expect(find.text('Demonstrație originală 2 / PDF 2'),findsOneWidget);
    await tester.tap(find.text('Demonstrație originală 1 / PDF 2'));
    await tester.pumpAndSettle();
    expect(tester.widget<SourceViewer>(find.byType(SourceViewer)).page,2);
    expect(tester.widget<SourceViewer>(find.byType(SourceViewer)).boxes,isNotEmpty);
    await tester.tap(find.widgetWithText(TextButton,'Bibliotecă').last);
    await tester.pumpAndSettle();
    expect(find.text('Demonstrație originală 1'),findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.runAsync(()=>temp.delete(recursive:true));
  },timeout:const Timeout(Duration(minutes:2)));
  testWidgets('Empty Reader contains no simulated results', (tester) async {
    await tester.pumpWidget(const HuiApp());
    expect(find.text('Sursele rămân punctul de plecare.'),findsOneWidget);
    expect(find.text('Demonstrație originală 1'),findsNothing);
  });
}
