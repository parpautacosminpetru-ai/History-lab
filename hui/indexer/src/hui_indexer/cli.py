from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .coverage import coverage
from .db import connect
from .ingestion import import_pdf, correct_structure
from .packages import export_package, import_package
from .search import Query, search, natural_query
from .semantics import create_node, annotate, relation, review, publish, provenance, validate, add_variant


def main(argv=None):
    parser = argparse.ArgumentParser(description='HUI — indexare locală și acces determinist la surse')
    parser.add_argument('--workspace',type=Path,default=Path('hui-workspace'))
    commands = parser.add_subparsers(dest='command',required=True)
    ingest = commands.add_parser('ingest')
    ingest.add_argument('pdf',type=Path,nargs='+')
    ingest.add_argument('--title')
    ingest.add_argument('--author',action='append',default=[])
    ingest.add_argument('--language',default='und')
    ingest.add_argument('--edition',default='Ediție nespecificată')
    ingest.add_argument('--bibliographic-id')
    ingest.add_argument('--year',type=int)
    ingest.add_argument('--ocr-language')
    node = commands.add_parser('node')
    node.add_argument('label')
    node.add_argument('--type',default='concept')
    node.add_argument('--language',default='und')
    node.add_argument('--disambiguation',default='')
    for name in ('annotate','relation','variant','review','structure'):
        command = commands.add_parser(name)
        command.add_argument('json_file',type=Path)
        if name=='review':
            command.add_argument('--reviewer',required=True)
            command.add_argument('--note',default='')
    query = commands.add_parser('search')
    query.add_argument('expression',nargs='?',default='')
    query.add_argument('--mode',choices=['text','index','linked'],default='text')
    query.add_argument('--scope',choices=['passage','context','source'],default='passage')
    query.add_argument('--source-id')
    query.add_argument('--author')
    query.add_argument('--node-type')
    query.add_argument('--relation-type')
    query.add_argument('--context-id')
    query.add_argument('--year-start',type=int)
    query.add_argument('--year-end',type=int)
    query.add_argument('--include-negated',action='store_true')
    query.add_argument('--limit',type=int,default=50)
    query.add_argument('--offset',type=int,default=0)
    query.add_argument('--natural',action='store_true')
    listing = commands.add_parser('list')
    listing.add_argument('entity',choices=['library','segments','nodes','structures','pending','occurrences'])
    listing.add_argument('--node-id')
    listing.add_argument('--offset',type=int,default=0)
    prov = commands.add_parser('provenance')
    prov.add_argument('occurrence_id')
    commands.add_parser('coverage')
    commands.add_parser('validate')
    commands.add_parser('gui')
    pub = commands.add_parser('publish')
    pub.add_argument('--description',default='Publicare manuală')
    export = commands.add_parser('export')
    export.add_argument('output',type=Path)
    export.add_argument('--include-originals',action='store_true')
    export.add_argument('--rights-confirmed',action='store_true')
    imp = commands.add_parser('import')
    imp.add_argument('package',type=Path)
    ai = commands.add_parser('propose')
    ai.add_argument('segment_id')
    ai.add_argument('--endpoint',required=True)
    ai.add_argument('--model',required=True)
    ai.add_argument('--allow-ai',action='store_true')
    ai.add_argument('--external',action='store_true')
    ai.add_argument('--allow-external',action='store_true')
    args = parser.parse_args(argv)
    if args.command=='import':
        result = import_package(args.package,args.workspace)
    else:
        db = connect(args.workspace/'catalog.sqlite')
        try:
            if args.command=='ingest':
                result = [import_pdf(db,args.workspace,pdf,title=args.title or pdf.stem,authors=args.author,
                                     language=args.language,edition=args.edition,bibliographic_id=args.bibliographic_id,
                                     year=args.year,ocr_language=args.ocr_language) for pdf in args.pdf]
            elif args.command=='node':
                result = create_node(db,args.label,args.type,args.language,disambiguation=args.disambiguation)
            elif args.command in ('annotate','relation','variant','review','structure'):
                data = json.loads(args.json_file.read_text(encoding='utf-8'))
                if args.command=='review':
                    result = review(db,data,reviewer=args.reviewer,note=args.note)
                else:
                    result = {'annotate':annotate,'relation':relation,'variant':add_variant,
                              'structure':correct_structure}[args.command](db,**data)
            elif args.command=='search':
                query = natural_query(args.expression) if args.natural else Query(
                    expression=args.expression,mode=args.mode,scope=args.scope,source_id=args.source_id,
                    author=args.author,node_type=args.node_type,relation_type=args.relation_type,
                    context_id=args.context_id,year_start=args.year_start,year_end=args.year_end,
                    include_negated=args.include_negated,limit=args.limit,offset=args.offset)
                result = search(db,query)
            elif args.command=='list':
                queries = {
                    'library':'SELECT e.*,s.title,s.language FROM SourceEditions e JOIN Sources s ON s.id=e.source_id ORDER BY s.title,e.id',
                    'segments':'SELECT t.*,p.pdf_page,p.edition_id FROM TextSegments t JOIN Pages p ON p.id=t.page_id ORDER BY p.edition_id,p.pdf_page',
                    'nodes':'SELECT * FROM IndexNodes ORDER BY canonical_label,id',
                    'structures':'SELECT * FROM DocumentStructures ORDER BY edition_id,start_page,start_offset',
                    'pending':"SELECT 'node' AS type,id,canonical_label AS label,verification FROM IndexNodes WHERE verification IN ('proposed','auto_validated','needs_review') UNION ALL SELECT 'occurrence',id,original_form,verification FROM Occurrences WHERE verification IN ('proposed','auto_validated','needs_review') UNION ALL SELECT 'relation',id,predicate,verification FROM ExplicitRelations WHERE verification IN ('proposed','auto_validated','needs_review')",
                    'occurrences':'SELECT * FROM Occurrences WHERE (? IS NULL OR node_id=?) ORDER BY id',
                }
                bindings = [args.node_id,args.node_id] if args.entity=='occurrences' else []
                result = [dict(r) for r in db.execute(queries[args.entity]+' LIMIT 200 OFFSET ?',[*bindings,max(0,args.offset)])]
            elif args.command=='provenance':
                result = provenance(db,args.occurrence_id)
            elif args.command=='coverage':
                result = coverage(db)
            elif args.command=='validate':
                result = validate(db)
                if result:
                    raise ValueError('; '.join(result))
            elif args.command=='publish':
                result = publish(db,args.description)
            elif args.command=='export':
                result = export_package(db,args.workspace,args.output,include_originals=args.include_originals,
                                        rights_confirmed=args.rights_confirmed)
            elif args.command=='propose':
                from .providers import OpenAICompatibleProvider, propose_segment
                provider = OpenAICompatibleProvider(args.endpoint,args.model,external=args.external)
                result = propose_segment(db,args.segment_id,provider,allow_ai=args.allow_ai,allow_external=args.allow_external)
            elif args.command=='gui':
                from .workbench import run
                run(db,args.workspace)
                result = None
            else:
                raise ValueError('Unknown command')
        finally:
            db.close()
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':
    try:
        sys.exit(main())
    except (ValueError,RuntimeError,OSError) as error:
        print(str(error),file=sys.stderr)
        sys.exit(1)
