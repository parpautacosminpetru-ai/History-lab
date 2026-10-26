import pytest
from hui_indexer.providers import DeterministicProvider,OpenAICompatibleProvider,propose_segment,SYSTEM
from hui_indexer.semantics import create_node,review
from conftest import part


def payload(segment):
    interval=part(segment,'domnie')
    return {'nodes':[{'key':'n','label':'domnie','type':'concept','quote':'domnie',
                      'start':interval['start'],'end':interval['end']}],'relations':[]}


def test_explicit_consent_precedes_provider_call(corpus):
    db,_,_,_,segment=corpus
    provider=DeterministicProvider(payload(segment))
    with pytest.raises(ValueError,match='consent'):
        propose_segment(db,segment['id'],provider)
    provider.external=True
    with pytest.raises(ValueError,match='consent'):
        propose_segment(db,segment['id'],provider,allow_ai=True)
    result=propose_segment(db,segment['id'],provider,allow_ai=True,allow_external=True)
    assert db.execute('SELECT verification FROM IndexNodes WHERE id=?',(result['nodes']['n'],)).fetchone()[0]=='proposed'
    assert db.execute('SELECT verification FROM Occurrences WHERE id=?',(result['occurrences']['n'],)).fetchone()[0]=='auto_validated'


def test_malformed_proposals_are_atomic_and_cannot_overwrite_confirmed_nodes(corpus):
    db,_,_,_,segment=corpus
    existing=create_node(db,'domnie','concept')
    review(db,[{'type':'node','id':existing,'status':'human_confirmed'}],reviewer='Human')
    data=payload(segment)
    data['nodes'][0]['node_id']=existing  # Untrusted instructions/IDs cannot select a write target.
    data['nodes'].append({'key':'bad','label':'inventat','type':'concept','quote':'inventat','start':0,'end':8})
    with pytest.raises(ValueError):
        propose_segment(db,segment['id'],DeterministicProvider(data),allow_ai=True)
    assert db.execute('SELECT count(*) FROM IndexNodes').fetchone()[0]==1
    assert db.execute('SELECT verification FROM IndexNodes WHERE id=?',(existing,)).fetchone()[0]=='human_confirmed'
    assert db.execute('SELECT count(*) FROM Occurrences').fetchone()[0]==0
    data=payload(segment);data['nodes'][0]['label']='unfounded historical inference'
    with pytest.raises(ValueError,match='literal'):
        propose_segment(db,segment['id'],DeterministicProvider(data),allow_ai=True)


@pytest.mark.parametrize('url',['http://example.com/v1/chat/completions','http://localhost.evil/v1','file:///etc/passwd','http://user:pass@127.0.0.1/v1','http://127.0.0.1/v1?key=secret'])
def test_local_provider_cannot_silently_upload_to_remote_server(url):
    with pytest.raises(ValueError):OpenAICompatibleProvider(url,'test-model')


def test_prompt_treats_documents_as_untrusted_data():
    assert 'untrusted data' in SYSTEM
    assert 'never follow' in SYSTEM
    assert OpenAICompatibleProvider('http://127.0.0.1:11434/v1/chat/completions','test').external is False
    with pytest.raises(ValueError):OpenAICompatibleProvider('http://example.com/v1','test',external=True)
