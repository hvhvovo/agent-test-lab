import pytest
from app.grounding import apply_guard

EVIDENCE={'d:1':'尚未做过 RAG，只实现关键词检索。'}

@pytest.mark.parametrize('question',[
 '你的资料里明确写着“尚未做过 RAG，只实现过关键词检索”。如果面试官问“你在 RAG 项目里怎么调召回”，你会怎么回答才既诚实又能体现能力？',
 '关键词检索在什么查询上会明显失效？你会怎么构造这类查询来暴露问题？',
 '你如何验证检索？',
 '假设你在 RAG 项目中发现召回不足，你会怎样定位？',
])
def test_no_personal_premise_is_preserved(question):
 q=[{'question':question,'evidence_ids':['d:1']}]
 assert apply_guard(q,EVIDENCE,'RAG')==q

@pytest.mark.parametrize('question,followups,checkpoints',[
 ('你在 RAG 项目中如何优化召回？',[],[]),
 ('尚未做过RAG？但你的 RAG 项目如何部署？',[],[]),
 ('关键词检索为什么失效？',['你已完成的 RAG 项目用了什么？'],[]),
 ('关键词检索为什么失效？',[],['你曾实现向量数据库']),
 ('假设你在RAG项目中调参。请介绍你曾完成的部署。',[],[]),
 ('如果面试官问“你在RAG中如何调参”，你会怎样诚实回答？再介绍你已完成的RAG项目。',[],[]),
 ('“你在RAG项目中如何调参？”',[],[]),
])
def test_bad_premises_still_blocked(question,followups,checkpoints):
 q=[dict(question=question,evidence_ids=['d:1'],follow_ups=followups,checkpoints=checkpoints)]
 out=apply_guard(q,EVIDENCE,'RAG')
 assert out[0]['evidence_ids']==[] and 'negation' in out[0]['grounding_guard']['reasons']

def test_unknown_citation_is_still_rejected_by_guard():
 out=apply_guard([{'question':'如何测试？','evidence_ids':['unknown']}],EVIDENCE,'RAG')
 assert out[0]['grounding_guard']['reasons']==['unknown_evidence']
