from pathlib import Path
import pytest

from hui_indexer.db import connect
from hui_indexer.demo import make_pdf, TEXTS
from hui_indexer.ingestion import import_pdf


@pytest.fixture
def corpus(tmp_path):
    workspace = tmp_path/'workspace'
    db = connect(workspace/'catalog.sqlite')
    pdf = tmp_path/'original.pdf'
    make_pdf(pdf,[['Préface introductive originale.'],TEXTS[0]])
    edition = import_pdf(db,workspace,pdf,title='Sursă de test',authors=['Autor de test'],language='ro')
    segment = db.execute('SELECT t.* FROM TextSegments t JOIN Pages p ON p.id=t.page_id WHERE p.edition_id=? AND p.pdf_page=2',(edition,)).fetchone()
    yield db,workspace,pdf,edition,dict(segment)
    db.close()


def part(segment, literal, nth=0):
    text = segment['original_text']
    start = -1
    for _ in range(nth+1):
        start = text.index(literal,start+1)
    return {'segment_id':segment['id'],'start':start,'end':start+len(literal)}
