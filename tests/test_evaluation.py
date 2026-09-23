import json
from pathlib import Path
import pytest
from scripts.evaluate import metrics, evaluate
from app.core import search_profile, Document


def test_metrics_are_recall_not_precision_and_dedup():
    assert metrics(['a','b','c','d'],['a','a','b','c','x'])['recall']==.75
    assert metrics(['b'],['a','b'])['reciprocal_rank']==.5
    assert metrics([],[])['empty_correct'] is True
    assert metrics([],['wrong'])['empty_correct'] is False
    assert metrics([],[])['recall'] is None


def test_dataset_references_and_splits():
    dataset=json.loads((Path(__file__).parents[1]/'evals/retrieval.json').read_text())
    result=evaluate(dataset)
    assert result['case_count']==30
    assert len(result['details'])==180
    assert all(0<=s['macro_recall']<=1 for s in result['summary'])


def test_alias_retrieval_and_empty_query():
    docs=[Document(source='tool',text='Function Calling 参数验证'),Document(source='cv',text='图像处理')]
    assert search_profile('工具调用',docs)[0]['source']=='tool'
    assert search_profile('',docs)==[]
    assert search_profile('Python',[])==[]


@pytest.mark.parametrize('k',[0,11,-1])
def test_invalid_retrieval_k(k):
    with pytest.raises(ValueError):search_profile('x',[],k)
