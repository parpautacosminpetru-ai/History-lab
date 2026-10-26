import 'package:flutter/material.dart';
import '../database/catalog.dart';
import '../widgets/navigation.dart';
import '../widgets/source_viewer.dart';
import '../services/query.dart';

class SourceScreen extends StatelessWidget {
  const SourceScreen({super.key,required this.catalog,required this.source,required this.trail});
  final Catalog catalog;
  final HuiRow source;
  final List<Crumb> trail;
  @override
  Widget build(BuildContext context) {
    final edition=source['id'] as String, pages=catalog.pages(edition),structures=catalog.structures(edition);
    return Scaffold(appBar:AppBar(title:Text(source['title'] as String)),body:Column(children:[
      TrailBar(trail:trail),
      Padding(padding:const EdgeInsets.all(12),child:Text('${source['authors']??''} • ${source['edition']} • ${source['language']} • ${source['sha256']}')),
      Expanded(child:ListView(children:[
        for(final structure in structures) ListTile(leading:Icon(structure['kind']=='chapter'?Icons.menu_book:Icons.account_tree_outlined),
          title:Text(structure['title'] as String),subtitle:Text('PDF ${structure['start_page']}–${structure['end_page']} • ${verificationLabel(structure['verification'])}'),
          onTap:()=>_openPage(context,edition,structure['start_page'] as int)),
        const Divider(),
        ...pages.map((page)=>ListTile(leading:const Icon(Icons.description_outlined),
          title:Text('PDF ${page['pdf_page']}${page['printed_page']==null?'':' • tipărită ${page['printed_page']}'}'),
          subtitle:Text('${page['extraction_method']} • ${page['transcription_verified']==1?'Transcriere confruntată':'Transcriere neconfirmată'}'),
          onTap:()=>_openPage(context,edition,page['pdf_page'] as int))),
      ])),
    ]));
  }
  void _openPage(BuildContext context,String edition,int number) {
    final hits=catalog.sourceResults(edition,number);
    final page=catalog.pages(edition).firstWhere((p)=>p['pdf_page']==number);
    final hit=hits.isNotEmpty?hits.first:<String,Object?>{
      ...page,'title':source['title'],'source_id':source['source_id'],'edition':source['edition'],
      'original_path':source['original_path'],'original_text':'','segment_id':null};
    pushResearch(context,trail,'PDF $number',(next)=>PassageScreen(catalog:catalog,hit:hit,trail:next));
  }
}

class PassageScreen extends StatefulWidget {
  const PassageScreen({super.key,required this.catalog,required this.hit,required this.trail,
    this.start,this.end,this.expression='',this.mode='text'});
  final Catalog catalog;
  final HuiRow hit;
  final List<Crumb> trail;
  final int? start,end;
  final String expression,mode;
  @override
  State<PassageScreen> createState()=>_PassageScreenState();
}

class _PassageScreenState extends State<PassageScreen> {
  late HuiRow hit=widget.hit;
  int? selectedStart,selectedEnd;
  Catalog get catalog=>widget.catalog;
  String? get segment=>hit['segment_id'] as String?;
  @override
  void initState(){super.initState();selectedStart=widget.start;selectedEnd=widget.end;}

  List<HuiRow> highlights() {
    if(segment==null)return [];
    if(selectedStart!=null && selectedEnd!=null)return catalog.boxes(segment!,selectedStart!,selectedEnd!);
    final ranges=<List<int>>[];
    if(widget.mode=='text' && widget.expression.isNotEmpty) {
      void visit(Expr? expr,{bool negative=false}) {
        if(expr==null)return;
        if(expr.op=='not'){visit(expr.left,negative:!negative);return;}
        if(expr.op=='term' && !negative) {
          final term='"${expr.term!.replaceAll('"','""')}"';
          final matches=catalog.db.select('SELECT highlight(SegmentFTS,0,char(1),char(2)) AS marked FROM SegmentFTS WHERE rowid=(SELECT rowid FROM TextSegments WHERE id=?) AND SegmentFTS MATCH ?',[segment,term]);
          if(matches.isNotEmpty) {
            var position=0,start=-1;
            for(final cp in (matches.single['marked'] as String).runes) {
              if(cp==1){start=position;}else if(cp==2){if(start>=0)ranges.add([start,position]);start=-1;}else{position++;}
            }
          }
        }
        visit(expr.left,negative:negative);visit(expr.right,negative:negative);
      }
      visit(parseQuery(widget.expression));
    } else {
      for(final a in catalog.annotations(segment!)) {
        if(a['verification']=='human_confirmed')ranges.add([a['start_offset'] as int,a['end_offset'] as int]);
      }
    }
    return [for(final range in ranges)...catalog.boxes(segment!,range[0],range[1])];
  }

  void move(int step) {
    final number=(hit['pdf_page'] as int)+step, edition=hit['edition_id'] as String;
    final pages=catalog.pages(edition).where((p)=>p['pdf_page']==number);
    if(pages.isEmpty)return;
    final matches=catalog.sourceResults(edition,number);
    setState((){hit=matches.isNotEmpty?matches.first:{...hit,...pages.first,'segment_id':null,'original_text':''};selectedStart=null;selectedEnd=null;});
  }

  @override
  Widget build(BuildContext context) {
    final annotations=segment==null?<HuiRow>[]:catalog.annotations(segment!);
    final relations=segment==null?<HuiRow>[]:catalog.relations(segment!);
    final boxes=highlights();
    final evidence=SingleChildScrollView(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
      Text('${hit['title']} / ${hit['context_title']??'Context documentar'}',style:Theme.of(context).textTheme.titleMedium),
      Text('PDF ${hit['pdf_page']} • tipărită ${hit['printed_page']??'neidentificată'} • ${hit['edition']}'),
      const SizedBox(height:12),
      const Text('TEXT EXTRAS ORIGINAL',style:TextStyle(fontWeight:FontWeight.bold)),
      SelectableText(hit['original_text'] as String? ?? ''),
      const Divider(),
      Text('Indici și apariții (${annotations.length})',style:Theme.of(context).textTheme.titleMedium),
      for(final a in annotations) ListTile(contentPadding:EdgeInsets.zero,title:Text(a['canonical_label'] as String),
        subtitle:Text('«${a['original_form']}»\n${verificationLabel(a['verification'])} • ${a['uncertainty']??''}'),
        leading:IconButton(tooltip:'Evidențiază apariția exactă',icon:const Icon(Icons.highlight),onPressed:()=>setState((){
          selectedStart=a['start_offset'] as int;selectedEnd=a['end_offset'] as int;})),
        onTap:()=>pushResearch(context,widget.trail,a['canonical_label'] as String,
          (next)=>NodeScreen(catalog:catalog,nodeId:a['node_id'] as String,trail:next))),
      const Divider(),
      Text('Relații explicite (${relations.length})',style:Theme.of(context).textTheme.titleMedium),
      for(final r in relations) Padding(padding:const EdgeInsets.symmetric(vertical:8),child:SelectableText(
        '${r['subject_label']} → ${r['predicate']} → ${r['object_label']}\n'
        'Conector: «${r['connector']}» • negație: ${r['negated']==1?'da':'nu'}\n'
        'Modalitate: ${r['modality']} • atribuire: ${r['attribution']} • timp verbal: ${r['tense']}\n${verificationLabel(r['verification'])}')),
      TextButton(onPressed:(){
        final source=catalog.library().firstWhere((s)=>s['id']==hit['edition_id']);
        pushResearch(context,widget.trail,'Sursă',(next)=>SourceScreen(catalog:catalog,source:source,trail:next));
      },child:const Text('Înapoi la structura sursei')),
    ]));
    final viewer=SourceViewer(key:ValueKey('${hit['edition_id']}/${hit['pdf_page']}'),
      pdfPath:catalog.asset(hit['original_path'] as String),
      imagePath:hit['image_path']==null?null:catalog.asset(hit['image_path'] as String),
      page:hit['pdf_page'] as int,pageWidth:(hit['width'] as num).toDouble(),
      pageHeight:(hit['height'] as num).toDouble(),boxes:boxes);
    return Scaffold(appBar:AppBar(title:Text('Pagina PDF ${hit['pdf_page']}'),actions:[
      IconButton(tooltip:'Pagina anterioară',onPressed:()=>move(-1),icon:const Icon(Icons.chevron_left)),
      IconButton(tooltip:'Pagina următoare',onPressed:()=>move(1),icon:const Icon(Icons.chevron_right)),
    ]),body:Column(children:[TrailBar(trail:widget.trail),Expanded(child:LayoutBuilder(builder:(context,constraints)=>
      constraints.maxWidth>=900?Row(children:[Expanded(flex:6,child:viewer),Expanded(flex:4,child:evidence)]):
        Column(children:[Expanded(child:viewer),Expanded(child:evidence)])))]));
  }
}

class NodeScreen extends StatelessWidget {
  const NodeScreen({super.key,required this.catalog,required this.nodeId,required this.trail});
  final Catalog catalog;
  final String nodeId;
  final List<Crumb> trail;
  @override
  Widget build(BuildContext context) {
    final node=catalog.db.select('SELECT * FROM IndexNodes WHERE id=?',[nodeId]).single;
    final occurrences=catalog.occurrences(nodeId);
    return Scaffold(appBar:AppBar(title:Text(node['canonical_label'] as String)),body:Column(children:[
      TrailBar(trail:trail),
      ListTile(title:Text('${node['node_type']} • ${node['language']} • ${node['disambiguation']}'),
        subtitle:SelectableText('Identitate: $nodeId\n${verificationLabel(node['verification'])}')),
      Expanded(child:ListView.builder(itemCount:occurrences.length,itemBuilder:(context,index){
        final item=occurrences[index];
        return ListTile(title:Text('${item['title']} / PDF ${item['pdf_page']}'),
          subtitle:Text('«${item['original_form']}» • ${verificationLabel(item['verification'])}'),
          trailing:const Icon(Icons.open_in_new),onTap:(){
            final hit=catalog.sourceResults(item['edition_id'] as String,item['pdf_page'] as int)
                .firstWhere((r)=>r['segment_id']==item['segment_id']);
            pushResearch(context,trail,'Apariție / PDF ${item['pdf_page']}',
              (next)=>PassageScreen(catalog:catalog,hit:hit,trail:next,start:item['start_offset'] as int,end:item['end_offset'] as int));
          });
      })),
    ]));
  }
}
