import 'dart:io';
import 'package:flutter/material.dart';
import 'package:pdfrx/pdfrx.dart';
import '../database/catalog.dart';

Rect normalizedBox(HuiRow box, Rect pageRect) => Rect.fromLTRB(
  pageRect.left+(box['x0'] as num).toDouble()*pageRect.width,
  pageRect.top+(box['y0'] as num).toDouble()*pageRect.height,
  pageRect.left+(box['x1'] as num).toDouble()*pageRect.width,
  pageRect.top+(box['y1'] as num).toDouble()*pageRect.height);

class HighlightPainter extends CustomPainter {
  HighlightPainter(this.boxes);
  final List<HuiRow> boxes;
  @override
  void paint(Canvas canvas,Size size) {
    final paint=Paint()..color=const Color(0x66F3BE32);
    for(final box in boxes) { canvas.drawRect(normalizedBox(box,Offset.zero & size),paint); }
  }
  @override
  bool shouldRepaint(HighlightPainter oldDelegate) => oldDelegate.boxes!=boxes;
}

class SourceViewer extends StatefulWidget {
  const SourceViewer({super.key,required this.pdfPath,required this.imagePath,
    required this.page,required this.pageWidth,required this.pageHeight,required this.boxes});
  final String pdfPath;
  final String? imagePath;
  final int page;
  final double pageWidth,pageHeight;
  final List<HuiRow> boxes;
  @override
  State<SourceViewer> createState()=>_SourceViewerState();
}

class _SourceViewerState extends State<SourceViewer> {
  bool raster=true;
  int turns=0;
  final zoom=TransformationController();
  final pdf=PdfViewerController();
  @override
  void dispose() { zoom.dispose(); super.dispose(); }
  @override
  void didUpdateWidget(covariant SourceViewer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.page!=widget.page && pdf.isReady) pdf.goToPage(pageNumber:widget.page);
  }
  @override
  Widget build(BuildContext context) {
    final hasImage=widget.imagePath!=null && File(widget.imagePath!).existsSync();
    final hasPdf=File(widget.pdfPath).existsSync();
    if (!hasImage && !hasPdf) {
      return const Center(child:Padding(padding:EdgeInsets.all(24),child:Text(
        'Pachetul conține numai indexul. Accesul la scanări necesită PDF-ul ediției cu hash-ul corespunzător.')));
    }
    final showRaster=hasImage && (raster || !hasPdf);
    return Column(children:[
      Wrap(spacing:8,children:[
        if(hasImage && hasPdf) TextButton.icon(onPressed:()=>setState(()=>raster=!raster),
          icon:Icon(showRaster?Icons.picture_as_pdf:Icons.image_outlined),
          label:Text(showRaster?'Deschide PDF-ul original':'Imaginea originală a paginii')),
        IconButton(tooltip:'Mărește',icon:const Icon(Icons.zoom_in),onPressed:(){
          if(showRaster) { zoom.value=zoom.value.clone()..scale(1.25); }
          else if(pdf.isReady) { pdf.zoomUp(); }
        }),
        IconButton(tooltip:'Micșorează',icon:const Icon(Icons.zoom_out),onPressed:(){
          if(showRaster) { zoom.value=zoom.value.clone()..scale(.8); }
          else if(pdf.isReady) { pdf.zoomDown(); }
        }),
        if(showRaster) IconButton(tooltip:'Rotește imaginea și evidențierea împreună',icon:const Icon(Icons.rotate_right),
          onPressed:()=>setState(()=>turns=(turns+1)%4)),
        TextButton(onPressed:(){zoom.value=Matrix4.identity();if(pdf.isReady)pdf.goToPage(pageNumber:widget.page);},child:const Text('Încadrează pagina')),
      ]),
      Expanded(child:showRaster?LayoutBuilder(builder:(context,constraints){
        final fitWidth=constraints.maxWidth;
        final fitHeight=fitWidth*widget.pageHeight/widget.pageWidth;
        return InteractiveViewer(transformationController:zoom,minScale:.3,maxScale:8,
          constrained:false,child:RotatedBox(quarterTurns:turns,child:SizedBox(width:fitWidth,height:fitHeight,
            child:Stack(fit:StackFit.expand,children:[
              Image.file(File(widget.imagePath!),fit:BoxFit.fill),
              IgnorePointer(child:CustomPaint(painter:HighlightPainter(widget.boxes))),
            ]))));
      }):PdfViewer.file(widget.pdfPath,controller:pdf,initialPageNumber:widget.page,
        params:PdfViewerParams(maxScale:8,enableKeyboardNavigation:true,pagePaintCallbacks:[
          (canvas,pageRect,page){
            if(page.pageNumber!=widget.page)return;
            for(final box in widget.boxes) {
              canvas.drawRect(normalizedBox(box,pageRect),Paint()..color=const Color(0x66F3BE32));
            }
          }
        ]))),
    ]);
  }
}
