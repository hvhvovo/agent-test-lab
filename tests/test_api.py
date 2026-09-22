import sqlite3
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.llm import ProviderError

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path/'test.sqlite3')) as c:
        yield c

def test_health_and_home(client):
    assert client.get('/health').json()['status']=='ok'
    assert 'Agent Test Lab' in client.get('/').text
    assert client.get('/openapi.json').status_code==200

def test_create_read_persist(tmp_path):
    path=tmp_path/'test.sqlite3'
    with TestClient(create_app(path)) as c:
        response=c.post('/api/reports',json={'jd':'Python SQL','documents':[{'source':'demo','text':'我用 Python 处理图像'}]})
        assert response.status_code==201
        report=response.json()
        assert report['unverified_skills']==['SQL']
        assert report['id']==1 and report['total_tokens']==0
        assert float(response.headers['X-Process-Time-Ms'])>=0
        assert len(response.headers['X-Request-ID'])==32
        assert c.get('/api/reports/1').json()==report
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM reports').fetchone()[0]==1
    with TestClient(create_app(path)) as c:
        assert c.get('/api/reports').json()[0]['jd']=='Python SQL'

@pytest.mark.parametrize('body',[{}, {'jd':''}, {'jd':' '}, {'jd':None}, {'jd':12}, {'jd':'x'*10001}, {'jd':'Python','mode':'bad'}])
def test_invalid_api(client,body):
    assert client.post('/api/reports',json=body).status_code==422
    assert client.get('/api/reports').json()==[]

def test_history_pagination_and_missing(client):
    for text in ['Python','SQL','Git']:
        assert client.post('/api/reports',json={'jd':text}).status_code==201
    assert client.get('/api/reports?limit=1&offset=1').json()[0]['jd']=='SQL'
    assert client.get('/api/reports/999').status_code==404
    assert client.get('/api/reports?limit=0').status_code==422
    assert client.get('/api/reports?offset=-1').status_code==422

def test_sql_content_is_data(client):
    value="Python '; DROP TABLE reports; --"
    assert client.post('/api/reports',json={'jd':value}).status_code==201
    assert client.get('/api/reports').json()[0]['jd']==value

def test_provider_failure_not_saved(tmp_path):
    provider=Mock(); provider.complete.side_effect=ProviderError('模型请求失败')
    with TestClient(create_app(tmp_path/'db',provider)) as c:
        assert c.post('/api/reports',json={'jd':'Python','mode':'llm'}).status_code==502
        assert c.get('/api/reports').json()==[]

def test_llm_success_api(tmp_path):
    provider=Mock()
    provider.complete.return_value=({'content':'{"questions":[{"question":"如何验证结果？","evidence_ids":[]}]}'},{'total_tokens':20})
    with TestClient(create_app(tmp_path/'db',provider)) as c:
        r=c.post('/api/reports',json={'jd':'Python','mode':'llm'}).json()
        assert r['mode']=='llm' and r['total_tokens']==20
        assert '未调用大模型' not in ''.join(r['limitations'])
