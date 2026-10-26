"""Regenerate the original demo package and cross-language query golden vectors."""
from dataclasses import asdict
from pathlib import Path
import json
import shutil
import tempfile

from hui_indexer.demo import generate
from hui_indexer.db import connect
from hui_indexer.search import Query,search

root=Path(__file__).resolve().parents[1]
output=root/'app/test/fixtures'
output.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='hui-fixture-') as temp:
    generate(Path(temp))
    db=connect(Path(temp)/'workspace/catalog.sqlite',readonly=True)
    try:
        queries=[Query('domnie'),Query('domnie',mode='index'),Query('absent OR domnie'),
                 Query('domnie AND NOT absent'),Query('"CAPITOLUL I"',scope='source'),
                 Query('X AND Y',mode='linked'),Query('X AND Y',mode='linked',include_negated=True),
                 Query('domnie',author='HUI — fixture original'),Query('domnie',node_type='concept'),
                 Query('domnie',limit=1,offset=1),Query('domnie',year_start=1000),Query('NOT domnie')]
        vectors=[{'query':asdict(q),'segment_ids':[r['segment_id'] for r in search(db,q)]} for q in queries]
        (output/'queries.json').write_text(json.dumps(vectors,ensure_ascii=False,indent=2),encoding='utf-8')
        shutil.copyfile(Path(temp)/'demo.hui',output/'demo.hui')
    finally:db.close()
schema=(root/'indexer/src/hui_indexer/migrations/001_initial.sql').read_text()
for path in (root/'schemas/index_schema.sql',root/'app/assets/schema.sql'):path.write_text(schema)
shutil.copyfile(root/'indexer/src/hui_indexer/assets/normalization.json',root/'app/assets/normalization.json')
print(output)
