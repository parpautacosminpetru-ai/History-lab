from pathlib import Path


def test_reader_and_indexer_share_the_exact_schema_and_unicode_table():
    root=Path(__file__).resolve().parents[2]
    source=root/'indexer/src/hui_indexer'
    canonical=(source/'migrations/001_initial.sql').read_bytes()
    assert (root/'schemas/index_schema.sql').read_bytes()==canonical
    assert (root/'app/assets/schema.sql').read_bytes()==canonical
    assert (root/'app/assets/normalization.json').read_bytes()==(source/'assets/normalization.json').read_bytes()
