import pytest
from app.topics import detect_topic, scenario_for, TOPICS
from app.question_bank import QUESTION_BY_ID
from app.grounding import apply_guard

@pytest.mark.parametrize('question,topic', [
 ('你在 RAG 项目中如何优化召回？','retrieval_quality'),
 ('如何评估 Recall@3？','retrieval_quality'),
 ('你如何设计工具调用次数预算？','tool_budget'),
 ('你如何解决 SQLite 的事务回滚？','transactions'),
 ('你如何定位数据库锁竞争？','database_lock'),
 ('你如何处理模型超时和429？','timeouts'),
 ('你如何设计分页？','pagination'),
 ('你如何验证切片和overlap？','chunking'),
 ('你如何配置 Docker 镜像？','containers'),
 ('你如何验证提示词注入？','prompt_injection'),
 ('你如何改进评分器？','judge'),
 ('你如何降低P95延迟？','latency'),
])
def test_topic_preserved_on_fallback(question, topic):
    out=apply_guard([{'question':question,'evidence_ids':['d:1']}],{'d:1':'尚未做过这些项目'},'无关的 Python 岗位')
    assert out[0]['grounding_guard']['topic']==topic
    assert out[0]['grounding_guard']['topic_status']=='matched'
    assert out[0]['evidence_ids']==[]
    assert out[0]['question'].startswith('假设场景')

def test_recall_does_not_turn_into_injection():
    q=[{'question':'你在RAG项目中如何优化召回？','evidence_ids':['d:1'],
        'follow_ups':['请讲你已完成的项目'], 'checkpoints':['你已经完成RAG']}]
    out=apply_guard(q,{'d:1':'尚未做过RAG'},'Agent RAG Security')
    assert '召回' in out[0]['question'] and '注入' not in out[0]['question']
    assert '你已完成' not in str(out) and q[0]['evidence_ids']==['d:1']

@pytest.mark.parametrize('text',['你如何做量子纠错？','你如何处理分页与事务？','smocking'])
def test_unknown_ambiguous_and_word_boundaries(text):
    assert detect_topic(text) is None
    topic, seed, _=scenario_for(text)
    assert topic is None and '澄清' in seed['question']

def test_duplicate_fallbacks_do_not_inflate_count():
    qs=[{'question':text,'evidence_ids':[]} for text in ['你的召回怎么优化？','你曾如何改进召回？']]
    out=apply_guard(qs,{},'RAG')
    assert len(out)==1

def test_all_topics_have_valid_templates():
    assert all(qid in QUESTION_BY_ID for _,qid in TOPICS.values())
