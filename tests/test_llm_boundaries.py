from unittest.mock import Mock, patch
import httpx
import pytest
from app.llm import generate_questions, LLMProvider, ProviderError


def tool(cid='a',name='search_profile',args='{"query":"Python"}'):
    return {'id':cid,'type':'function','function':{'name':name,'arguments':args}}


@pytest.mark.parametrize('bad',[
    tool('b','delete_file'),tool('b',args='{"query":"   "}'),
    tool('b',args='{"query":"Python","top_k":99}'),tool('a'),
    {'id':'b','type':'other','function':{'name':'search_profile','arguments':'{}'}},None,
])
def test_invalid_batch_executes_nothing(bad):
    provider=Mock()
    provider.complete.return_value=({'tool_calls':[tool(),bad]}, {})
    with patch('app.llm.search_profile',return_value=[]) as search:
        with pytest.raises(ProviderError):generate_questions('Python',[],provider)
        search.assert_not_called()


def test_multi_call_budget_and_final_round():
    provider=Mock()
    provider.complete.side_effect=[({'tool_calls':[tool(str(i)) for i in range(4)]},{}),
        ({'content':'{"questions":[{"question":"如何测试？","evidence_ids":[]}]}'},{})]
    with patch('app.llm.search_profile',return_value=[]) as search:
        qs,trace,_=generate_questions('Python',[],provider)
    assert qs and len(trace)==search.call_count==4
    assert provider.complete.call_args.kwargs['allow_tools'] is False


def test_over_budget_batch_executes_nothing():
    provider=Mock()
    provider.complete.return_value=({'tool_calls':[tool(str(i)) for i in range(5)]},{})
    with patch('app.llm.search_profile',return_value=[]) as search:
        with pytest.raises(ProviderError,match='次数超限'):generate_questions('Python',[],provider)
        search.assert_not_called()


@pytest.mark.parametrize('message,usage',[(None,{}),({},[]),({'tool_calls':{}},{}),({'tool_calls':''},{}),
    ({'content':'{"questions":[{"question":"   ","evidence_ids":[]}]}'},{}),
    ({'content':'{"questions":[{"question":"重复","evidence_ids":[]},{"question":"重复","evidence_ids":[]}]}'},{})])
def test_malformed_response(message,usage):
    provider=Mock();provider.complete.return_value=(message,usage)
    with pytest.raises(ProviderError):generate_questions('Python',[],provider)


def test_provider_closing_request_disables_tools(monkeypatch):
    monkeypatch.setenv('LLM_BASE_URL','https://example.test/v1')
    monkeypatch.setenv('LLM_MODEL','mock')
    monkeypatch.setenv('LLM_API_KEY','dummy-test-key')
    def handle(r):
        import json
        assert json.loads(r.content)['tool_choice']=='none'
        return httpx.Response(200,json={'choices':[{'message':{'content':'{}'}}]})
    LLMProvider(httpx.MockTransport(handle)).complete([],allow_tools=False)
