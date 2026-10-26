"""Generate entirely original synthetic documents, never commercial books."""
from pathlib import Path
import argparse

TEXTS = [
    ['CAPITOLUL I — Document demonstrativ',
     'Acesta este un document original de test, fără afirmații istorice.',
     'Tema domnie este un termen de test. X nu a provocat Y.',
     'Autorul presupune că X ar fi provocat Y.'],
    ['Chapitre I — Document de démonstration',
     'Ceci est un texte de test original, sans affirmation historique.',
     'Le terme « domnie » apparaît ici. Une institution de test.'],
    ['Kapitel I — Testdokument',
     'Dies ist ein eigener Testtext ohne historische Behauptung.',
     'Das Wort domnie steht hier. Eine Testinstitution.'],
]


def make_pdf(path: Path, pages: list[list[str]]):
    from importlib.resources import files
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    font = files('hui_indexer').joinpath('assets/DejaVuSans.ttf')
    if 'HUIFixture' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('HUIFixture',str(font)))
    path.parent.mkdir(parents=True,exist_ok=True)
    document = canvas.Canvas(str(path),pagesize=(595,842),invariant=1)
    for lines in pages:
        document.setFont('HUIFixture',12)
        y = 780
        for line in lines:
            document.drawString(45,y,line)
            y -= 30
        document.showPage()
    document.save()
    if any(ord(char)>0xffff for lines in pages for line in lines for char in line):
        # ReportLab 4's five-digit ToUnicode entries are not valid UTF-16BE.
        # Repair only our synthetic fixture producer, never an imported original.
        import re
        from pypdf import PdfReader,PdfWriter
        from pypdf.generic import NameObject,DecodedStreamObject
        reader=PdfReader(path)
        for page in reader.pages:
            for reference in page['/Resources']['/Font'].values():
                font_object=reference.get_object()
                if '/ToUnicode' not in font_object:continue
                data=font_object['/ToUnicode'].get_data()
                fixed=re.sub(rb'<([0-9A-Fa-f]{5,6})>',lambda m:b'<'+chr(int(m[1],16)).encode('utf-16-be').hex().upper().encode()+b'>',data)
                stream=DecodedStreamObject();stream.set_data(fixed)
                font_object[NameObject('/ToUnicode')]=stream
        writer=PdfWriter();writer.append_pages_from_reader(reader)
        temporary=path.with_suffix('.fixed.pdf')
        with temporary.open('wb') as target:writer.write(target)
        temporary.replace(path)


def generate(output: Path):
    from .db import connect
    from .ingestion import import_pdf
    from .semantics import create_node,annotate,review,publish,relation
    from .packages import export_package
    output = Path(output)
    workspace = output/'workspace'
    db = connect(workspace/'catalog.sqlite')
    try:
        canonical = create_node(db,'domnie','concept','ro',disambiguation='Indice demonstrativ fictiv')
        decisions = [{'type':'node','id':canonical,'status':'human_confirmed'}]
        for i,(lines,language) in enumerate(zip(TEXTS,['ro','fr','de']),1):
            pdf = output/f'demo-{language}.pdf'
            make_pdf(pdf,[['Document demonstrativ HUI — numai date sintetice.'],lines])
            edition = import_pdf(db,workspace,pdf,title=f'Demonstrație originală {i}',authors=['HUI — fixture original'],language=language)
            segment = db.execute('SELECT t.* FROM TextSegments t JOIN Pages p ON p.id=t.page_id WHERE p.edition_id=? AND p.pdf_page=2',(edition,)).fetchone()
            start = segment['original_text'].index('domnie')
            occurrence = annotate(db,canonical,[{'segment_id':segment['id'],'start':start,'end':start+6}],language=language)
            decisions.append({'type':'occurrence','id':occurrence,'status':'human_confirmed'})
            if language=='ro':
                node_x=create_node(db,'X','concept','ro',disambiguation='Subiect fictiv de test')
                node_y=create_node(db,'Y','concept','ro',disambiguation='Obiect fictiv de test')
                decisions.extend([{'type':'node','id':node_x,'status':'human_confirmed'},
                                  {'type':'node','id':node_y,'status':'human_confirmed'}])
                for sentence,negated,modality,attribution in [
                    ('X nu a provocat Y.',True,'assertive',''),
                    ('Autorul presupune că X ar fi provocat Y.',False,'conditional','Autorul presupune')]:
                    start=segment['original_text'].index(sentence)
                    endpoints=[]
                    for label,node in [('X',node_x),('Y',node_y)]:
                        position=start+sentence.index(label)
                        endpoint=annotate(db,node,[{'segment_id':segment['id'],'start':position,'end':position+1}])
                        endpoints.append(endpoint)
                        decisions.append({'type':'occurrence','id':endpoint,'status':'human_confirmed'})
                    rid=relation(db,endpoints[0],'causality',endpoints[1],
                                 [{'segment_id':segment['id'],'start':start,'end':start+len(sentence)}],
                                 connector='provocat',negated=negated,modality=modality,attribution=attribution)
                    decisions.append({'type':'relation','id':rid,'status':'human_confirmed'})
        # Synthetic fixture approvals describe test data, not a historical verification.
        review(db,decisions,reviewer='Generator de fixture: validare sintetică')
        publish(db,'Documente demonstrative originale; nu conțin date istorice')
        export_package(db,workspace,output/'demo.hui',include_originals=True,rights_confirmed=True)
    finally:
        db.close()
    return output/'demo.hui'


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    print(generate(parser.parse_args().output))
