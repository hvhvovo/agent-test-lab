"""不请求真实模型；重放“引用合法但经历前提错误”的可控故障。"""
import json
from unittest.mock import Mock
from app.core import Document
from app.llm import generate_questions


def provider():
    p = Mock()
    p.complete.side_effect = [({'tool_calls': [{'id': 'c1', 'type': 'function', 'function': {
        'name': 'search_profile', 'arguments': json.dumps({'query': 'RAG'})}}]}, {}),
        ({'content': json.dumps({'questions': [{'question': '你在 RAG 项目中如何优化召回？',
                                                'evidence_ids': ['demo:1']}]})}, {})]
    return p


if __name__ == '__main__':
    docs = [Document(source='demo', text='尚未做过 RAG，只学习过概念。')]
    for guard in (False, True):
        questions, trace, _ = generate_questions('RAG', docs, provider(), guard=guard)
        print(json.dumps({'guard_enabled': guard, 'questions': questions, 'trace': trace}, ensure_ascii=False, indent=2))
