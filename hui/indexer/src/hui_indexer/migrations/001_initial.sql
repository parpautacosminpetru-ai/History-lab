CREATE TABLE Sources (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, work_type TEXT NOT NULL DEFAULT 'book',
 publisher TEXT, publication_year INTEGER, language TEXT NOT NULL DEFAULT 'und',
 bibliographic_id TEXT, metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE Authors (id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE SourceAuthors (
 source_id TEXT NOT NULL REFERENCES Sources(id), author_id TEXT NOT NULL REFERENCES Authors(id),
 position INTEGER NOT NULL, PRIMARY KEY(source_id,author_id)
);
CREATE TABLE SourceEditions (
 id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES Sources(id), edition TEXT NOT NULL,
 original_path TEXT NOT NULL, sha256 TEXT NOT NULL UNIQUE CHECK(length(sha256)=64),
 page_count INTEGER NOT NULL CHECK(page_count>0), processing_version TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'imported', document_kind TEXT NOT NULL DEFAULT 'unknown',
 language_hint TEXT NOT NULL DEFAULT 'und', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE Pages (
 id TEXT PRIMARY KEY, edition_id TEXT NOT NULL REFERENCES SourceEditions(id),
 pdf_page INTEGER NOT NULL CHECK(pdf_page>0), printed_page TEXT,
 width REAL NOT NULL CHECK(width>0), height REAL NOT NULL CHECK(height>0),
 rotation INTEGER NOT NULL CHECK(rotation IN (0,90,180,270)), image_path TEXT,
 raw_text TEXT NOT NULL, normalized_text TEXT NOT NULL, extraction_method TEXT NOT NULL,
 ocr_confidence REAL, transcription_verified INTEGER NOT NULL DEFAULT 0 CHECK(transcription_verified IN (0,1)),
 reading_order_uncertain INTEGER NOT NULL DEFAULT 0 CHECK(reading_order_uncertain IN (0,1)),
 UNIQUE(edition_id,pdf_page)
);
CREATE TABLE DocumentStructures (
 id TEXT PRIMARY KEY, edition_id TEXT NOT NULL REFERENCES SourceEditions(id),
 parent_id TEXT REFERENCES DocumentStructures(id), kind TEXT NOT NULL, title TEXT NOT NULL,
 start_page INTEGER NOT NULL, end_page INTEGER NOT NULL CHECK(end_page>=start_page),
 start_offset INTEGER NOT NULL DEFAULT 0, end_offset INTEGER,
 method TEXT NOT NULL, verification TEXT NOT NULL DEFAULT 'needs_review'
);
CREATE TABLE TextSegments (
 id TEXT PRIMARY KEY, page_id TEXT NOT NULL REFERENCES Pages(id),
 structure_id TEXT REFERENCES DocumentStructures(id), reading_order INTEGER NOT NULL,
 start_offset INTEGER NOT NULL CHECK(start_offset>=0), end_offset INTEGER NOT NULL CHECK(end_offset>start_offset),
 original_text TEXT NOT NULL, normalized_text TEXT NOT NULL, UNIQUE(page_id,reading_order)
);
CREATE TABLE TextBoxes (
 segment_id TEXT NOT NULL REFERENCES TextSegments(id), start_offset INTEGER NOT NULL,
 end_offset INTEGER NOT NULL CHECK(end_offset>start_offset),
 x0 REAL NOT NULL CHECK(x0>=0 AND x0<=1), y0 REAL NOT NULL CHECK(y0>=0 AND y0<=1),
 x1 REAL NOT NULL CHECK(x1>=x0 AND x1<=1), y1 REAL NOT NULL CHECK(y1>=y0 AND y1<=1),
 confidence REAL, PRIMARY KEY(segment_id,start_offset,end_offset)
);
CREATE TABLE IndexNodes (
 id TEXT PRIMARY KEY, canonical_label TEXT NOT NULL, normalized_label TEXT NOT NULL,
 node_type TEXT NOT NULL, language TEXT NOT NULL, disambiguation TEXT NOT NULL DEFAULT '',
 verification TEXT NOT NULL CHECK(verification IN ('proposed','auto_validated','needs_review','human_confirmed','rejected')),
 year_start INTEGER, year_end INTEGER CHECK(year_end>=year_start), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE NodeVariants (
 id TEXT PRIMARY KEY, node_id TEXT NOT NULL REFERENCES IndexNodes(id), original_form TEXT NOT NULL,
 normalized_form TEXT NOT NULL, language TEXT NOT NULL, justification_span_id TEXT REFERENCES EvidenceSpans(id),
 verification TEXT NOT NULL CHECK(verification IN ('proposed','auto_validated','needs_review','human_confirmed','rejected')),
 UNIQUE(node_id,original_form,language)
);
CREATE TABLE EvidenceSpans (
 id TEXT PRIMARY KEY, edition_id TEXT NOT NULL REFERENCES SourceEditions(id),
 method TEXT NOT NULL, verification TEXT NOT NULL CHECK(verification IN ('proposed','auto_validated','needs_review','human_confirmed','rejected')),
 uncertainty TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE SpanParts (
 span_id TEXT NOT NULL REFERENCES EvidenceSpans(id), position INTEGER NOT NULL,
 segment_id TEXT NOT NULL REFERENCES TextSegments(id), start_offset INTEGER NOT NULL CHECK(start_offset>=0),
 end_offset INTEGER NOT NULL CHECK(end_offset>start_offset),
 PRIMARY KEY(span_id,position), UNIQUE(span_id,segment_id,start_offset,end_offset)
);
CREATE TABLE Occurrences (
 id TEXT PRIMARY KEY, node_id TEXT NOT NULL REFERENCES IndexNodes(id), span_id TEXT NOT NULL REFERENCES EvidenceSpans(id),
 original_form TEXT NOT NULL, language TEXT NOT NULL, method TEXT NOT NULL,
 verification TEXT NOT NULL CHECK(verification IN ('proposed','auto_validated','needs_review','human_confirmed','rejected')),
 UNIQUE(node_id,span_id)
);
CREATE TABLE ExplicitRelations (
 id TEXT PRIMARY KEY, subject_id TEXT NOT NULL REFERENCES IndexNodes(id), predicate TEXT NOT NULL,
 object_id TEXT NOT NULL REFERENCES IndexNodes(id), connector TEXT NOT NULL DEFAULT '',
 negated INTEGER NOT NULL CHECK(negated IN (0,1)), modality TEXT NOT NULL,
 attribution TEXT NOT NULL, tense TEXT NOT NULL DEFAULT '', qualifiers_json TEXT NOT NULL DEFAULT '{}',
 verification TEXT NOT NULL CHECK(verification IN ('proposed','auto_validated','needs_review','human_confirmed','rejected'))
);
CREATE TABLE RelationEvidence (
 relation_id TEXT NOT NULL REFERENCES ExplicitRelations(id), span_id TEXT NOT NULL REFERENCES EvidenceSpans(id),
 subject_occurrence_id TEXT NOT NULL REFERENCES Occurrences(id), object_occurrence_id TEXT NOT NULL REFERENCES Occurrences(id),
 PRIMARY KEY(relation_id,span_id)
);
CREATE TABLE ReviewLog (
 id INTEGER PRIMARY KEY, target_type TEXT NOT NULL, target_id TEXT NOT NULL,
 previous_status TEXT NOT NULL, new_status TEXT NOT NULL, reviewer TEXT NOT NULL,
 note TEXT NOT NULL, reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE ProcessingJobs (
 edition_id TEXT NOT NULL REFERENCES SourceEditions(id), stage TEXT NOT NULL,
 status TEXT NOT NULL, last_page INTEGER NOT NULL DEFAULT 0, error TEXT,
 PRIMARY KEY(edition_id,stage)
);
CREATE TABLE Issues (
 id TEXT PRIMARY KEY, edition_id TEXT NOT NULL REFERENCES SourceEditions(id),
 page_id TEXT REFERENCES Pages(id), category TEXT NOT NULL, detail TEXT NOT NULL,
 resolved INTEGER NOT NULL DEFAULT 0 CHECK(resolved IN (0,1))
);
CREATE TABLE IndexVersions (
 id INTEGER PRIMARY KEY, published_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 description TEXT NOT NULL, schema_version INTEGER NOT NULL
);
CREATE VIRTUAL TABLE SegmentFTS USING fts5(original_text, content='TextSegments', content_rowid='rowid', tokenize='unicode61 remove_diacritics 2');
CREATE TRIGGER segments_fts_insert AFTER INSERT ON TextSegments BEGIN
 INSERT INTO SegmentFTS(rowid,original_text) VALUES(new.rowid,new.original_text);
END;
CREATE TRIGGER segments_no_update BEFORE UPDATE ON TextSegments BEGIN
 SELECT RAISE(ABORT,'Source segments are immutable');
END;
CREATE TRIGGER segments_no_delete BEFORE DELETE ON TextSegments BEGIN
 SELECT RAISE(ABORT,'Source segments are immutable');
END;
CREATE TRIGGER page_text_no_update BEFORE UPDATE OF raw_text,normalized_text,width,height,rotation,edition_id,pdf_page ON Pages BEGIN
 SELECT RAISE(ABORT,'Source text and geometry are immutable');
END;
CREATE TRIGGER segment_matches_page BEFORE INSERT ON TextSegments BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM Pages p WHERE p.id=new.page_id
 AND new.end_offset<=length(p.raw_text)
 AND new.original_text=substr(p.raw_text,new.start_offset+1,new.end_offset-new.start_offset))
 THEN RAISE(ABORT,'Segment does not match source page') END;
END;
CREATE TRIGGER valid_span_part BEFORE INSERT ON SpanParts BEGIN
 SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM TextSegments t JOIN Pages p ON p.id=t.page_id
 JOIN EvidenceSpans e ON e.id=new.span_id WHERE t.id=new.segment_id
 AND e.edition_id=p.edition_id AND new.end_offset<=length(t.original_text))
 THEN RAISE(ABORT,'Evidence outside source text or edition') END;
END;
CREATE INDEX idx_pages_edition ON Pages(edition_id,pdf_page);
CREATE INDEX idx_segments_page ON TextSegments(page_id,reading_order);
CREATE INDEX idx_structure_parent ON DocumentStructures(parent_id);
CREATE INDEX idx_nodes_label ON IndexNodes(normalized_label,node_type);
CREATE INDEX idx_variants_label ON NodeVariants(normalized_form,verification);
CREATE INDEX idx_occurrences_node ON Occurrences(node_id,verification,span_id);
CREATE INDEX idx_occurrences_span ON Occurrences(span_id);
CREATE INDEX idx_parts_segment ON SpanParts(segment_id,start_offset,end_offset);
CREATE INDEX idx_rel_subject ON ExplicitRelations(subject_id,predicate,verification);
CREATE INDEX idx_rel_object ON ExplicitRelations(object_id,predicate,verification);
CREATE INDEX idx_rel_evidence_span ON RelationEvidence(span_id);
CREATE INDEX idx_boxes_range ON TextBoxes(segment_id,start_offset,end_offset);
PRAGMA user_version=1;
