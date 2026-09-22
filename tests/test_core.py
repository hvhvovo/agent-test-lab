import pytest
from pydantic import ValidationError
from app.core import AnalysisRequest, Document, extract_skills, search_profile, analyze

@pytest.mark.parametrize('jd,skills,expected', [
    ('熟悉 python 和 Git', ['Python','SQL','Git'], ['Python','Git']),
    ('沟通能力', ['Python'], []), ('', ['Python'], []),
    ('Python', [], []), ('PYTHON', ['Python','python'], ['Python']),
    ('digital MySQL', ['Git','SQL'], []),
    ('使用C++和Python', ['C++','Python'], ['C++','Python']),
    ('Git Python Git', ['Python','Git'], ['Python','Git']),
    ('Python\nSQL', ['Python','SQL'], ['Python','SQL']),
])
def test_extract(jd, skills, expected):
    assert extract_skills(jd, skills) == expected

@pytest.mark.parametrize('value',[None, 123, []])
def test_invalid_jd_type(value):
    with pytest.raises(TypeError): extract_skills(value)

@pytest.mark.parametrize('skills',[[''], [' '], [None]])
def test_invalid_skill(skills):
    with pytest.raises(ValueError): extract_skills('Python', skills)

def test_retrieval_ranking_and_no_hits():
    docs = [Document(source='cv',text='Python 图像处理'), Document(source='db',text='SQL 数据库')]
    assert search_profile('Python 图像',docs)[0]['source'] == 'cv'
    assert search_profile('Kubernetes',docs) == []

def test_chunk_long_document_and_evidence():
    docs=[Document(source='long',text='甲'*700+' Python 项目')]
    r=analyze(AnalysisRequest(jd='Python SQL',documents=docs))
    assert r['mentioned_skills']==['Python']
    assert r['unverified_skills']==['SQL']
    assert r['mention_coverage']==0.5
    assert 'Python' in r['evidence'][0]['citations'][0]['text']
    assert r['evidence'][1]['citations']==[]

def test_no_skills_no_division_by_zero():
    assert analyze(AnalysisRequest(jd='沟通能力'))['mention_coverage'] is None

def test_missing_evidence_is_not_a_claim_of_inability():
    r=analyze(AnalysisRequest(jd='Python'))
    assert r['unverified_skills']==['Python']
    assert r['questions'][0]['evidence_ids']==[]

@pytest.mark.parametrize('kwargs',[
    {'jd':'   '}, {'jd':'x'*10001}, {'jd':'Python','extra':1},
    {'jd':'Python','mode':'magic'}, {'jd':'Python','documents':[{'source':'x','text':'   '}]},
    {'jd':'Python','documents':[{'source':'x','text':'a'},{'source':'x','text':'b'}]},
])
def test_request_validation(kwargs):
    with pytest.raises(ValidationError): AnalysisRequest(**kwargs)

def test_negation_is_documented_limitation():
    # 锁定当前 baseline 行为，不把它描述成已解决的语义理解。
    assert extract_skills('不要求 Python', ['Python']) == ['Python']
