import 'dart:io';
import 'dart:isolate';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';
import 'database/catalog.dart';
import 'services/packages.dart';
import 'services/query.dart';
import 'screens/research.dart';
import 'widgets/navigation.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final directory=await getApplicationSupportDirectory();
  final schema=await rootBundle.loadString('assets/schema.sql');
  final normalization=await rootBundle.loadString('assets/normalization.json');
  final store=PackageStore(Directory('${directory.path}/collections'),schema);
  Catalog? catalog;
  String? error;
  try { final active=await store.active();if(active!=null)catalog=Catalog(active,normalization); }
  catch(e) { error='Catalogul anterior nu a putut fi deschis: $e'; }
  runApp(HuiApp(store:store,normalization:normalization,initialCatalog:catalog,initialError:error));
}

class HuiApp extends StatelessWidget {
  const HuiApp({super.key,this.store,this.normalization='',this.initialCatalog,this.initialError});
  final PackageStore? store;
  final String normalization;
  final Catalog? initialCatalog;
  final String? initialError;
  @override
  Widget build(BuildContext context)=>MaterialApp(debugShowCheckedModeBanner:false,
    title:'HUI — Historical Universal Index',
    theme:ThemeData(useMaterial3:true,colorScheme:ColorScheme.fromSeed(seedColor:const Color(0xFF235B60)),
      scaffoldBackgroundColor:const Color(0xFFF5F5F0),
      appBarTheme:const AppBarTheme(backgroundColor:Color(0xFFF5F5F0))),
    home:ReaderHome(store:store,normalization:normalization,initialCatalog:initialCatalog,initialError:initialError));
}

class ReaderHome extends StatefulWidget {
  const ReaderHome({super.key,this.store,required this.normalization,this.initialCatalog,this.initialError});
  final PackageStore? store;
  final String normalization;
  final Catalog? initialCatalog;
  final String? initialError;
  @override
  State<ReaderHome> createState()=>_ReaderHomeState();
}

class _ReaderHomeState extends State<ReaderHome> {
  late Catalog? catalog=widget.initialCatalog;
  late String? error=widget.initialError;
  int destination=0;
  bool busy=false;
  @override
  void dispose(){catalog?.close();super.dispose();}
  Future<void> importCollection() async {
    final store=widget.store;
    if(store==null)return;
    final selected=await FilePicker.platform.pickFiles(type:FileType.custom,allowedExtensions:['hui']);
    if(selected==null || selected.files.single.path==null || !mounted)return;
    setState(()=>busy=true);
    final path=selected.files.single.path!, root=store.root.path, schema=store.schema;
    try {
      final installed=await Isolate.run(() async => (await PackageStore(Directory(root),schema).importFile(File(path))).path);
      final next=Catalog(Directory(installed),widget.normalization);
      if(!mounted){next.close();return;}
      setState((){catalog?.close();catalog=next;error=null;destination=0;});
    } catch(e) { if(mounted)setState(()=>error='Import nereușit. Catalogul anterior este păstrat. $e'); }
    finally { if(mounted)setState(()=>busy=false); }
  }
  @override
  Widget build(BuildContext context) {
    const titles=['Bibliotecă','Căutare universală','Coordonate','Acoperire'];
    const icons=[Icons.local_library_outlined,Icons.search,Icons.table_chart_outlined,Icons.fact_check_outlined];
    final current=catalog;
    final body=current==null?const Center(child:Padding(padding:EdgeInsets.all(32),child:Column(mainAxisSize:MainAxisSize.min,children:[
      Icon(Icons.local_library_outlined,size:64,color:Color(0xFF235B60)),SizedBox(height:16),
      Text('Sursele rămân punctul de plecare.',style:TextStyle(fontSize:24)),SizedBox(height:12),
      Text('Importă un pachet .hui publicat de Indexer. Căutarea, navigarea și consultarea paginilor funcționează local.\nBaza pornește goală; nu sunt afișate date simulate.',textAlign:TextAlign.center),
    ]))):switch(destination){
      0=>LibraryView(catalog:current),
      1=>SearchView(key:ValueKey(current.root.path),catalog:current),
      2=>CoordinatesView(catalog:current),
      _=>CoverageView(catalog:current),
    };
    return LayoutBuilder(builder:(context,constraints){
      final wide=constraints.maxWidth>=850;
      return Scaffold(appBar:AppBar(title:Text('HUI / ${titles[destination]}'),actions:[
        if(busy)const Padding(padding:EdgeInsets.all(16),child:SizedBox(width:20,height:20,child:CircularProgressIndicator(strokeWidth:2))),
        TextButton.icon(onPressed:busy || widget.store==null?null:importCollection,icon:const Icon(Icons.file_open_outlined),label:const Text('Importă .hui')),
      ]),body:Column(children:[
        if(error!=null)MaterialBanner(content:Text(error!),actions:[TextButton(onPressed:()=>setState(()=>error=null),child:const Text('Închide'))]),
        Expanded(child:Row(children:[
          if(wide)NavigationRail(selectedIndex:destination,onDestinationSelected:(v)=>setState(()=>destination=v),labelType:NavigationRailLabelType.all,
            destinations:[for(var i=0;i<titles.length;i++)NavigationRailDestination(icon:Icon(icons[i]),label:Text(titles[i]))]),
          Expanded(child:body),
        ])),
        if(!wide)NavigationBar(selectedIndex:destination,onDestinationSelected:(v)=>setState(()=>destination=v),
          destinations:[for(var i=0;i<titles.length;i++)NavigationDestination(icon:Icon(icons[i]),label:titles[i])]),
      ]));
    });
  }
}

class LibraryView extends StatelessWidget {
  const LibraryView({super.key,required this.catalog});
  final Catalog catalog;
  @override
  Widget build(BuildContext context) {
    final sources=catalog.library();
    return ListView.builder(padding:const EdgeInsets.all(20),itemCount:sources.length+1,itemBuilder:(context,index){
      if(index==0)return Padding(padding:const EdgeInsets.only(bottom:20),child:Text(
        '${sources.length} ediții • index local\nAI indexează. Baza conservă. Istoricul interpretează.',style:Theme.of(context).textTheme.titleMedium));
      final source=sources[index-1];
      return Card(child:ListTile(contentPadding:const EdgeInsets.all(20),leading:const Icon(Icons.menu_book,size:36),
        title:Text(source['title'] as String),subtitle:Text('${source['authors']??'Autor neprecizat'}\n'
          '${source['edition']} • ${source['language']} • ${source['page_count']} pagini\n'
          'Procesare: ${source['status']} (${source['processed_pages']} pagini) • '
          '${source['occurrence_count']} apariții / ${source['confirmed_count']} confirmate uman'),isThreeLine:true,
        trailing:const Icon(Icons.chevron_right),onTap:()=>pushResearch(context,const [Crumb('Bibliotecă','/')],source['title'] as String,
          (trail)=>SourceScreen(catalog:catalog,source:source,trail:trail))));
    });
  }
}

class SearchView extends StatefulWidget {
  const SearchView({super.key,required this.catalog});
  final Catalog catalog;
  @override
  State<SearchView> createState()=>_SearchViewState();
}

class _SearchViewState extends State<SearchView> {
  final text=TextEditingController(),author=TextEditingController(),relation=TextEditingController(),
    yearStart=TextEditingController(),yearEnd=TextEditingController();
  String mode='text',scope='passage';
  String? sourceId,nodeType,error;
  bool allStatuses=false,negative=false,busy=false,searched=false;
  List<HuiRow> results=[];
  Query? lastQuery;
  int request=0;
  @override
  void dispose(){for(final c in [text,author,relation,yearStart,yearEnd]){c.dispose();}super.dispose();}
  Future<void> run({bool more=false}) async {
    final token=++request;
    setState(()=>busy=true);
    try {
      var expression=text.text.trim(),selectedMode=mode;
      if(expression.toLowerCase().startsWith('unde ')) {
        final parsed=naturalQuery(expression);expression=parsed.expression;selectedMode=parsed.mode;
      } else if(expression.endsWith('?')) {
        throw const FormatException('Întrebare nerecunoscută. Alege termenii și filtrele.');
      }
      final q=Query(expression:expression,mode:selectedMode,scope:scope,sourceId:sourceId,
        author:author.text.isEmpty?null:author.text,nodeType:nodeType,
        relationType:relation.text.isEmpty?null:relation.text,
        yearStart:yearStart.text.isEmpty?null:int.parse(yearStart.text),yearEnd:yearEnd.text.isEmpty?null:int.parse(yearEnd.text),
        includeNegated:negative,statuses:allStatuses?const ['proposed','auto_validated','needs_review','human_confirmed']:const ['human_confirmed'],
        offset:more?results.length:0);
      final found=await widget.catalog.search(q);
      if(!mounted || token!=request)return;
      setState((){results=more?[...results,...found]:found;lastQuery=q;error=null;searched=true;});
    } catch(e){if(mounted && token==request)setState(()=>error='$e');}
    finally{if(mounted && token==request)setState(()=>busy=false);}
  }
  @override
  Widget build(BuildContext context) {
    final sources={for(final s in widget.catalog.library())s['source_id'] as String:s['title'] as String};
    return Column(children:[
      Padding(padding:const EdgeInsets.all(16),child:Column(children:[
        TextField(controller:text,onSubmitted:(_)=>run(),decoration:InputDecoration(labelText:'Termeni, indici sau întrebare recunoscută',
          hintText:'domnie AND Moldova • „...” pentru o expresie exactă',border:const OutlineInputBorder(),
          suffixIcon:IconButton(onPressed:busy?null:()=>run(),icon:const Icon(Icons.search),tooltip:'Caută'))),
        const SizedBox(height:8),
        Wrap(spacing:16,runSpacing:8,crossAxisAlignment:WrapCrossAlignment.center,children:[
          DropdownButton<String>(value:mode,items:const [DropdownMenuItem(value:'text',child:Text('Text original')),
            DropdownMenuItem(value:'index',child:Text('Indici documentați')),DropdownMenuItem(value:'linked',child:Text('Relații explicite'))],onChanged:(v)=>setState(()=>mode=v!)),
          DropdownButton<String>(value:scope,items:const [DropdownMenuItem(value:'passage',child:Text('Același segment de pagină')),
            DropdownMenuItem(value:'context',child:Text('Același context')),DropdownMenuItem(value:'source',child:Text('Aceeași sursă'))],onChanged:(v)=>setState(()=>scope=v!)),
          DropdownButton<String?>(value:sourceId,hint:const Text('Toate sursele'),items:[const DropdownMenuItem<String?>(value:null,child:Text('Toate sursele')),
            ...sources.entries.map((e)=>DropdownMenuItem<String?>(value:e.key,child:SizedBox(width:160,child:Text(e.value,overflow:TextOverflow.ellipsis))))],onChanged:(v)=>setState(()=>sourceId=v)),
          DropdownButton<String?>(value:nodeType,hint:const Text('Toate tipurile'),items:[const DropdownMenuItem<String?>(value:null,child:Text('Toate tipurile')),
            for(final type in ['person','institution','region','locality','event','period','year','concept','theme'])DropdownMenuItem<String?>(value:type,child:Text(type))],onChanged:(v)=>setState(()=>nodeType=v)),
        ]),
        ExpansionTile(title:const Text('Autor, cronologie, relație și verificare'),children:[
          Wrap(spacing:12,runSpacing:8,children:[
            SizedBox(width:180,child:TextField(controller:author,decoration:const InputDecoration(labelText:'Autor (nume exact)'))),
            SizedBox(width:150,child:TextField(controller:relation,decoration:const InputDecoration(labelText:'Tip relație exact'))),
            SizedBox(width:110,child:TextField(controller:yearStart,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'An de la'))),
            SizedBox(width:110,child:TextField(controller:yearEnd,keyboardType:TextInputType.number,decoration:const InputDecoration(labelText:'An până la'))),
          ]),
          CheckboxListTile(title:const Text('Include propunerile etichetate ca neverificate'),value:allStatuses,onChanged:(v)=>setState(()=>allStatuses=v!)),
          CheckboxListTile(title:const Text('Include relațiile negate'),value:negative,onChanged:(v)=>setState(()=>negative=v!)),
        ]),
        if(error!=null)Text(error!,style:TextStyle(color:Theme.of(context).colorScheme.error)),
        if(busy)const LinearProgressIndicator(),
      ])),
      const Padding(padding:EdgeInsets.symmetric(horizontal:16),child:Text(
        'Coapariția textuală nu dovedește o relație. Absența rezultatelor nu dovedește absența informației într-o sursă neacoperită.')),
      Expanded(child:ListView.builder(padding:const EdgeInsets.all(16),itemCount:results.length+1,itemBuilder:(context,index){
        if(index==results.length)return searched?Padding(padding:const EdgeInsets.all(16),child:Column(children:[
          Text('${results.length} rezultate încărcate'),if(results.isNotEmpty && results.length%50==0)TextButton(onPressed:busy?null:()=>run(more:true),child:const Text('Încarcă următoarele 50')),
        ])):const SizedBox.shrink();
        final hit=results[index], annotations=widget.catalog.annotations(hit['segment_id'] as String),relations=widget.catalog.relations(hit['segment_id'] as String);
        return Card(child:ExpansionTile(title:Text('${hit['title']} / PDF ${hit['pdf_page']}'),
          subtitle:Text('${hit['authors']??''} • ${hit['context_title']??'Fără structură confirmată'}\n'
            'Indici: ${annotations.map((a)=>a['canonical_label']).take(5).join(', ')} • ${relations.length} relații explicite'),
          children:[Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
            SelectableText(hit['original_text'] as String),
            Wrap(spacing:8,children:annotations.take(20).map((a)=>ActionChip(label:Text('${a['canonical_label']} • ${verificationLabel(a['verification'])}'),
              onPressed:()=>pushResearch(context,const [Crumb('Căutare','/')],a['canonical_label'] as String,
                (trail)=>NodeScreen(catalog:widget.catalog,nodeId:a['node_id'] as String,trail:trail)))).toList()),
            for(final r in relations) Text('${r['subject_label']} → ${r['predicate']} → ${r['object_label']} • '
              '${r['negated']==1?'NEGAT • ':''}${r['modality']} • ${r['attribution']} • ${verificationLabel(r['verification'])}'),
            FilledButton.icon(onPressed:()=>pushResearch(context,const [Crumb('Căutare','/')],'PDF ${hit['pdf_page']}',
              (trail)=>PassageScreen(catalog:widget.catalog,hit:hit,trail:trail,expression:lastQuery?.expression??'',mode:lastQuery?.mode??'text')),
              icon:const Icon(Icons.open_in_new),label:const Text('Deschide pagina și evidențiază pasajul')),
          ]))]));
      })),
    ]);
  }
}

class CoordinatesView extends StatefulWidget {
  const CoordinatesView({super.key,required this.catalog});
  final Catalog catalog;
  @override
  State<CoordinatesView> createState()=>_CoordinatesViewState();
}
class _CoordinatesViewState extends State<CoordinatesView> {
  String rowType='person',columnType='locality';
  @override
  Widget build(BuildContext context) {
    final cells=widget.catalog.matrix(rowType,columnType);
    return Column(children:[
      Padding(padding:const EdgeInsets.all(16),child:Wrap(spacing:20,children:[
        for(final rowAxis in [true,false])DropdownButton<String>(value:rowAxis?rowType:columnType,
          items:[for(final t in ['person','locality','region','institution','period','year','concept','theme','event'])DropdownMenuItem(value:t,child:Text('${rowAxis?'Rând':'Coloană'}: $t'))],
          onChanged:(v)=>setState((){if(rowAxis){rowType=v!;}else{columnType=v!;}})),
      ])),
      const Padding(padding:EdgeInsets.all(16),child:Text('Matrice rară: numai perechi cu relații explicite confirmate, nenegate. Numărul reprezintă afirmații indexate, nu certitudini istorice. Selectarea deschide proveniențele indicelui. Maximum 200 de perechi.')),
      Expanded(child:SingleChildScrollView(child:SingleChildScrollView(scrollDirection:Axis.horizontal,child:DataTable(
        columns:const [DataColumn(label:Text('Indice / axă rând')),DataColumn(label:Text('Indice / axă coloană')),DataColumn(label:Text('Afirmații'))],
        rows:cells.map((cell)=>DataRow(cells:[
          DataCell(Text(cell['row_label'] as String),onTap:()=>pushResearch(context,const [Crumb('Coordonate','/')],cell['row_label'] as String,
            (trail)=>NodeScreen(catalog:widget.catalog,nodeId:cell['row_id'] as String,trail:trail))),
          DataCell(Text(cell['column_label'] as String),onTap:()=>pushResearch(context,const [Crumb('Coordonate','/')],cell['column_label'] as String,
            (trail)=>NodeScreen(catalog:widget.catalog,nodeId:cell['column_id'] as String,trail:trail))),
          DataCell(Text('${cell['assertions']}')),
        ])).toList())))),
    ]);
  }
}

class CoverageView extends StatelessWidget {
  const CoverageView({super.key,required this.catalog});
  final Catalog catalog;
  @override
  Widget build(BuildContext context)=>ListView(padding:const EdgeInsets.all(24),children:[
    Text('Acoperire măsurată',style:Theme.of(context).textTheme.headlineSmall),
    const Padding(padding:EdgeInsets.symmetric(vertical:16),child:Text(
      'Exhaustivitatea semantică nu este măsurată. Caracterele acoperite de o adnotare confirmată nu înseamnă că toate sensurile explicite ale pasajului au fost verificate.')),
    for(final metric in catalog.coverage().entries)Card(child:ListTile(title:Text(metric.key),trailing:Text('${metric.value}',style:Theme.of(context).textTheme.titleLarge))),
    const Padding(padding:EdgeInsets.only(top:20),child:Text('Revizuirea și corectarea adnotărilor se fac în atelierul Indexer pe Windows. Reader consultă instantaneul importat și păstrează starea fiecărei propuneri.')),
  ]);
}
