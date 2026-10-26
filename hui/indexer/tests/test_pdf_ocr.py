from pathlib import Path
import shutil

from PIL import Image
from pypdf import PdfReader,PdfWriter
import pypdfium2 as pdfium
import pytest
from reportlab.pdfgen import canvas

from hui_indexer.demo import make_pdf
from hui_indexer.db import connect
from hui_indexer.ingestion import import_pdf,extract_digital
from hui_indexer.search import Query,search
from hui_indexer.semantics import create_node,annotate,provenance


@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_actual_pdf_rotation_crop_and_highlight_pixels(tmp_path,rotation):
    original=tmp_path/'original.pdf';make_pdf(original,[['domnie and exact provenance']])
    source=PdfReader(original);page=source.pages[0]
    page.cropbox.lower_left=(10,10);page.cropbox.upper_right=(580,830)
    page.rotate(rotation)
    rotated=tmp_path/'rotated.pdf';writer=PdfWriter();writer.add_page(page)
    with rotated.open('wb') as target:writer.write(target)
    workspace=tmp_path/'workspace';db=connect(workspace/'catalog.sqlite')
    try:
        import_pdf(db,workspace,rotated,title='Rotated test',language='en')
        segment=db.execute('SELECT * FROM TextSegments').fetchone()
        start=segment['original_text'].index('domnie')
        node=create_node(db,'domnie','concept')
        occurrence=annotate(db,node,[{'segment_id':segment['id'],'start':start,'end':start+6}])
        trace=provenance(db,occurrence)['parts'][0]
        assert trace['rotation']==rotation
        image=Image.open(workspace/trace['image_path']).convert('L')
        hits=0
        for box in trace['boxes']:
            rect=(int(box['x0']*image.width),int(box['y0']*image.height),
                  max(int(box['x0']*image.width)+1,int(box['x1']*image.width)),
                  max(int(box['y0']*image.height)+1,int(box['y1']*image.height)))
            hits+=image.crop(rect).getextrema()[0]<150
        assert hits>=5
    finally:db.close()


def test_unicode_supplementary_codepoints_and_diacritics(tmp_path):
    original=tmp_path/'unicode.pdf';make_pdf(original,[['A😀B țară École Straße']])
    document=pdfium.PdfDocument(original)
    try:
        page=document[0]
        try:
            text,boxes=extract_digital(page)
            assert 'A😀B țară École Straße' in text
            for start,end,*_ in boxes:assert 0<=start<end<=len(text)
            assert any(text[start:end]=='B' for start,end,*_ in boxes)
        finally:page.close()
    finally:document.close()


@pytest.mark.skipif(not shutil.which('tesseract'),reason='Local Tesseract executable is not installed')
def test_real_scanned_pdf_ocr_and_coordinates(tmp_path):
    digital=tmp_path/'digital.pdf';make_pdf(digital,[['A local OCR test with exact page coordinates.']])
    document=pdfium.PdfDocument(digital);page=document[0];bitmap=page.render(scale=2)
    raster=tmp_path/'raster.png';bitmap.to_pil().save(raster)
    bitmap.close();page.close();document.close()
    scanned=tmp_path/'scan.pdf';pdf=canvas.Canvas(str(scanned),pagesize=(595,842));pdf.drawImage(str(raster),0,0,595,842);pdf.showPage();pdf.save()
    workspace=tmp_path/'workspace';db=connect(workspace/'catalog.sqlite')
    try:
        import_pdf(db,workspace,scanned,title='Scan original de test',language='en',ocr_language='eng')
        found=search(db,Query('coordinates'))
        assert len(found)==1 and found[0]['pdf_page']==1
        page=db.execute('SELECT * FROM Pages').fetchone()
        assert page['extraction_method']=='tesseract' and 0<=page['ocr_confidence']<=1
        assert page['transcription_verified']==0
        assert db.execute('SELECT count(*) FROM TextBoxes').fetchone()[0]>4
    finally:db.close()
