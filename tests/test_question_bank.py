import pytest
from app.core import select_questions, extract_skills
from app.question_bank import QUESTION_BANK
from app.skills import ALIASES


def test_bank_has_unique_ids_and_actionable_rubrics():
    assert len({q['id'] for q in QUESTION_BANK}) == len(QUESTION_BANK)
    for q in QUESTION_BANK:
        assert len(q['follow_ups']) >= 2
        assert len(q['checkpoints']) >= 4
        assert q['pitfalls']
        assert set(q['skills']) <= ALIASES.keys()


@pytest.mark.parametrize('jd,expected',[
    ('digital design', []), ('MySQL', []), ('GITHUB', []),
    ('熟悉 git',['Git']), ('智能体',['Agent']),
    ('tool calling',['Function Calling']), ('接口自动化',['API Testing']),
])
def test_shared_matching_rules(jd,expected):
    assert extract_skills(jd) == expected
    for q in select_questions(jd):
        assert set(q['matched_skills']) <= set(expected)


def test_multi_label_dedup_and_limit():
    qs=select_questions('Agent Function Calling',limit=10)
    assert len({q['id'] for q in qs}) == len(qs)
    assert sum(q['id']=='agent_tool_001' for q in qs)==1
    assert len(select_questions('Agent',limit=3))==3


def test_filter_determinism_and_ownership():
    a=select_questions('Python RAG Agent',level='深入')
    assert a and all(q['level']=='深入' for q in a)
    assert a==select_questions('Python RAG Agent',level='深入')
    a[0]['checkpoints'].clear()
    assert select_questions('Python RAG Agent',level='深入')[0]['checkpoints']


def test_diverse_skill_coverage():
    qs=select_questions('SQL Python RAG Agent Git',limit=5)
    assert {'SQL','Python','RAG','Agent','Git'} <= {s for q in qs for s in q['matched_skills']}


@pytest.mark.parametrize('kwargs',[{'limit':0},{'limit':11},{'level':'专家'}])
def test_invalid_filter(kwargs):
    with pytest.raises(ValueError):select_questions('Python',**kwargs)
