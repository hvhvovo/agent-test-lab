import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import create_app


def test_practice_upsert_and_restart(tmp_path):
    path=tmp_path/'reports.db'
    with TestClient(create_app(path)) as c:
        report=c.post('/api/reports',json={'jd':'RAG Agent','question_count':3,'level':'深入'}).json()
        assert len(report['questions'])==3
        body={'answer':'先拆分检索与生成，记录证据，再用固定样例验证。','covered_points':[0], 'confidence':'部分掌握','notes':'补充无答案样例'}
        url=f"/api/reports/{report['id']}/answers/0"
        assert c.put(url,json=body).status_code==200
        body['notes']='已复习'
        assert c.put(url,json=body).status_code==200
    with TestClient(create_app(path)) as c:
        data=c.get(f"/api/reports/{report['id']}/answers").json()
        assert len(data)==1 and data[0]['notes']=='已复习'
        assert data[0]['assessment_type']=='self_review'
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM practice').fetchone()[0]==1


@pytest.mark.parametrize('body',[
    {'answer':' '},{'answer':None},{'answer':'x'*10001},
    {'answer':'ok','covered_points':[999]}, {'answer':'ok','covered_points':[-1]},
    {'answer':'ok','covered_points':[0,0]}, {'answer':'ok','confidence':'自动满分'},
])
def test_invalid_practice_does_not_write(tmp_path,body):
    with TestClient(create_app(tmp_path/'db')) as c:
        c.post('/api/reports',json={'jd':'Python'})
        assert c.put('/api/reports/1/answers/0',json=body).status_code==422
        assert c.get('/api/reports/1/answers').json()==[]


def test_missing_report_question_and_filters(tmp_path):
    with TestClient(create_app(tmp_path/'db')) as c:
        assert c.get('/api/reports/9/answers').status_code==404
        assert c.put('/api/reports/9/answers/0',json={'answer':'x'}).status_code==404
        c.post('/api/reports',json={'jd':'Python'})
        assert c.put('/api/reports/1/answers/-1',json={'answer':'x'}).status_code==404
        assert c.put('/api/reports/1/answers/99',json={'answer':'x'}).status_code==404
        qs=c.get('/api/questions?skill=RAG&level=深入').json()
        assert qs and all('RAG' in q['skills'] and q['level']=='深入' for q in qs)
        assert c.get('/api/questions?level=bad').status_code==422
        assert c.get('/api/questions?skill=digital').json()==[]


def test_no_match_fallback_is_explicit(tmp_path):
    with TestClient(create_app(tmp_path/'db')) as c:
        r=c.post('/api/reports',json={'jd':'舞蹈'}).json()
        assert r['question_selection']['matched']==0
        assert r['questions'][0]['kind']=='fallback'
