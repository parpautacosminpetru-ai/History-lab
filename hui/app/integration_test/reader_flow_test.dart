import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:path_provider/path_provider.dart';
import 'package:pdfrx/pdfrx.dart';
import 'package:hui_reader/database/catalog.dart';
import 'package:hui_reader/main.dart';
import 'package:hui_reader/services/packages.dart';
import 'package:hui_reader/services/query.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('Import real .hui and search offline on the target device',(tester) async {
    final support=await getApplicationSupportDirectory();
    final temp=await Directory('${support.path}/integration-test').create(recursive:true);
    final bytes=await rootBundle.load('test/fixtures/demo.hui');
    final package=await File('${temp.path}/demo.hui').writeAsBytes(bytes.buffer.asUint8List());
    final schema=await rootBundle.loadString('assets/schema.sql');
    final normalization=await rootBundle.loadString('assets/normalization.json');
    final root=await PackageStore(Directory('${temp.path}/collection'),schema).importFile(package);
    final catalog=Catalog(root,normalization);
    final baseline=await catalog.search(const Query(expression:'domnie'));
    expect(baseline.length,3);
    expect(await catalog.search(const Query(expression:'domnie')),baseline);
    await tester.pumpWidget(HuiApp(initialCatalog:catalog,normalization:normalization));
    await tester.pumpAndSettle();
    expect(find.text('Demonstrație originală 1'),findsOneWidget);
    await tester.tap(find.text('Demonstrație originală 1'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('PDF 2'));
    await tester.pumpAndSettle();
    expect(find.text('Pagina PDF 2'),findsOneWidget);
    await tester.tap(find.text('Deschide PDF-ul original'));
    await tester.pumpAndSettle();
    expect(find.byType(PdfViewer),findsOneWidget);
    final viewer=tester.widget<PdfViewer>(find.byType(PdfViewer));
    expect(viewer.controller!.isReady,true);
    expect(viewer.controller!.pageNumber,2);
  });
}
