"""Reproducible SQLite benchmark. Synthetic database, not PDF extraction timing."""
from pathlib import Path
import argparse
import json
import platform
import statistics
import tempfile
import time

from hui_indexer.db import connect,normalize,transaction
from hui_indexer.search import Query,search,build_sql


def run(segments=10000,iterations=30):
    with tempfile.TemporaryDirectory(prefix='hui-benchmark-') as temp:
        db=connect(Path(temp)/'catalog.sqlite')
        try:
            started=time.perf_counter()
            with transaction(db):
                db.execute("INSERT INTO Sources(id,title,language) VALUES('source','Synthetic benchmark','ro')")
                db.execute("INSERT INTO SourceEditions(id,source_id,edition,original_path,sha256,page_count,processing_version,status) VALUES('edition','source','synthetic','originals/benchmark.pdf',?,?,'benchmark','ready')",('0'*64,segments))
                for index in range(segments):
                    text=f'Document demonstrativ {index}. '+('domnie' if index%10==0 else 'alt termen')
                    db.execute("INSERT INTO Pages(id,edition_id,pdf_page,width,height,rotation,raw_text,normalized_text,extraction_method) VALUES(?,'edition',?,595,842,0,?,?,'synthetic')",(str(index),index+1,text,normalize(text)))
                    db.execute('INSERT INTO TextSegments VALUES(?,?,NULL,?,0,?,?,?)',(str(index),str(index),index,len(text),text,normalize(text)))
            ingest_seconds=time.perf_counter()-started
            query=Query('domnie',limit=50)
            timings=[]
            for _ in range(iterations):
                start=time.perf_counter();result=search(db,query);timings.append((time.perf_counter()-start)*1000)
                assert len(result)==min(50,(segments+9)//10)
            sql,params=build_sql(query)
            return {'platform':platform.platform(),'python':platform.python_version(),
                    'sqlite':db.execute('SELECT sqlite_version()').fetchone()[0],
                    'synthetic_segments':segments,'matching_segments':(segments+9)//10,'iterations':iterations,
                    'database_size_bytes':(Path(temp)/'catalog.sqlite').stat().st_size,
                    'synthetic_load_seconds':round(ingest_seconds,4),
                    'query_median_ms':round(statistics.median(timings),4),
                    'query_p95_ms':round(sorted(timings)[min(len(timings)-1,int(.95*len(timings)))],4),
                    'query_plan':[list(row) for row in db.execute('EXPLAIN QUERY PLAN '+sql,params)],
                    'scope':'SQLite textual page-segment search only; no OCR, UI or collection-scale guarantee'}
        finally:db.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--segments',type=int,default=10000);parser.add_argument('--iterations',type=int,default=30)
    args=parser.parse_args()
    if args.segments<1 or args.iterations<1:parser.error('positive sizes required')
    print(json.dumps(run(args.segments,args.iterations),indent=2))
