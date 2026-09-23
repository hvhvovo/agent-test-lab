from unittest.mock import Mock

from app.llm import generate_questions


def test_final_answer_after_four_tool_calls():
    provider = Mock()
    responses = []

    # 模拟模型连续四次请求调用工具
    for index in range(4):
        message = {
            "tool_calls": [
                {
                    "id": f"call-{index}",
                    "type": "function",
                    "function": {
                        "name": "search_profile",
                        "arguments": '{"query": "Python", "top_k": 1}'
                    }
                }
            ]
        }
        responses.append((message, {}))

    # 第五次模型响应：不再调用工具，直接给出答案
    final_message = {
        "content": (
            '{"questions": ['
            '{"question": "如何测试 Python 接口？", "evidence_ids": []}'
            ']}'
        )
    }
    responses.append((final_message, {}))

    provider.complete.side_effect = responses

    questions, trace, tokens = generate_questions(
        "熟悉 Python",
        [],
        provider
    )

    assert len(trace) == 4
    assert provider.complete.call_count == 5
    assert questions[0]["question"] == "如何测试 Python 接口？"
    
import pytest
from unittest.mock import patch
from app.llm import ProviderError


def test_fifth_tool_call_is_blocked():
    provider = Mock()

    # 模拟模型一直要求调用工具
    provider.complete.return_value = (
        {
            "tool_calls": [{
                "id": "repeated-call",
                "type": "function",
                "function": {
                    "name": "search_profile",
                    "arguments": '{"query": "Python", "top_k": 1}'
                }
            }]
        },
        {}
    )

    with patch("app.llm.search_profile", return_value=[]) as search:
        with pytest.raises(ProviderError, match="工具调用次数超限"):
            generate_questions("熟悉 Python", [], provider)

        assert search.call_count == 4
        assert provider.complete.call_count == 5
    
