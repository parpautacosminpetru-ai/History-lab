"""Regression tests for identity merging, paginated evidence, and local-only surface."""
from test_professional import setup_env


def test_paginated_search_keeps_every_source_passage():
    tmp, client = setup_env()
    try:
        blocks = [f'În anul 1475, documentul menționează Moldova în pasajul {i}.' for i in range(20)]
        u=client.post('/api/sources/upload',files={'files':('lots.txt',('\n\n'.join(blocks)).encode('utf-8'),'text/plain')})
        assert u.status_code==200
        assert client.post('/api/index/run').status_code==200
        allids=[]
        offset=0
        for step in range(10):
            page=client.get('/api/query',params={'q':'Moldova','limit':4,'offset':offset}).json()
            assert page['total']==20,page
            allids.extend(hit['id'] for hit in page['hits'])
            if not page['has_more']:
                assert page['next_offset'] is None
                break
            offset=page['next_offset']
        assert len(allids)==20 and len(set(allids))==20
        assert client.get('/api/query',params={'q':'Moldova','offset':-1}).status_code==422
    finally: tmp.cleanup()


def test_merge_verified_identities_preserves_claims_and_evidence():
    tmp, client=setup_env()
    try:
        txt=('În anul 1475, în Moldova, Ștefan cel Mare și Ștefan Vodă au încheiat un tratat cu Polonia.')
        u=client.post('/api/sources/upload',files={'files':('text.txt',txt.encode('utf-8'),'text/plain')})
        assert u.status_code==200
        assert client.post('/api/index/run').status_code==200
        candidate=client.post('/api/entities',json={'name':'Ștefan Vodă','kind':'persoană'}).json()['id']
        people={x['name']:x['id'] for x in client.get('/api/entities').json()['entities']}
        target=people['Ștefan cel Mare']
        assert target!=candidate
        pid=client.get('/api/query',params={'q':'tratat'}).json()['hits'][0]['id']
        for subject,theme in ((target,'diplomație'),(candidate,'frontieră')):
            r=client.post('/api/claims',json={'passage_id':pid,'subject_id':subject,'predicate':'au încheiat',
                  'theme':theme,'object_id':people['Polonia'],'place_id':people['Moldova']})
            assert r.status_code==200,r.text
        assert len(client.get('/api/claims').json()['claims'])==2
        merged=client.post(f'/api/entities/{target}/merge',json={'source_id':candidate,'confirmation':True})
        assert merged.status_code==200,merged.text
        claims=client.get('/api/claims').json()['claims']
        assert len(claims)==1 and claims[0]['subject_id']==target,claims
        assert 'frontieră' in claims[0]['themes'] and 'diplomație' in claims[0]['themes']
        assert len(client.get(f"/api/claims/{claims[0]['id']}/evidence").json()['passages'])==1
        assert client.get(f'/api/entity/{candidate}').status_code==404
    finally:tmp.cleanup()


def test_restrict_non_local_hostname():
    tmp,client=setup_env()
    try:
        assert client.get('/api/health').status_code==200
        assert client.get('/api/health',headers={'Host':'not-your-local-machine.invalid'}).status_code==400
    finally:tmp.cleanup()
