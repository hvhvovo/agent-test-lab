import json
from unittest.mock import Mock
import httpx
import pytest
from app.core import Document
from app.llm import LLMProvider, ProviderError, generate_questions


def call(name='search_profile', args=None):
    return {'tool_calls':[{'id':'call-1','type':'function','function':{
        'name':name,'arguments':json.dumps(args if args is not None else {'query':'Python','top_k':1})}}]}

def answer(ids=None):
    return {'content':json.dumps({'questions':[{'question':'请解释 Python 项目的测试方法','evidence_ids':ids or []}]})}

def test_tool_call_then_grounded_answer():
    provider=Mock()
    provider.complete.side_effect=[(call(),{'total_tokens':10}),(answer(['demo:1']),{'total_tokens':20})]
    qs,trace,tokens=generate_questions('Python',[Document(source='demo',text='Python 项目使用 pytest')],provider)
    assert qs[0]['evidence_ids']==['demo:1'] and tokens==30
    assert trace[0]['result_ids']==['demo:1']
    messages=provider.complete.call_args.args[0]
    assert messages[-1]['role']=='tool'
    assert 'Python 项目' in messages[-1]['content']

@pytest.mark.parametrize('message',[
    {'content':'not json'}, answer(['fabricated:99']),
    {'content':'{"questions":[]}'}, call('delete_file'),
    call(args={'query':'Python','top_k':100}), call(args={'query':''}),
    {'tool_calls':[{'id':'x'}]},
])
def test_bad_model_outputs(message):
    provider=Mock();provider.complete.return_value=(message,{})
    with pytest.raises(ProviderError): generate_questions('Python',[],provider)

def test_tool_budget():
    provider = Mock()
    provider.complete.return_value = (call(), {})

    with pytest.raises(ProviderError, match="工具调用次数超限"):
        generate_questions("Python", [], provider)

    assert provider.complete.call_count == 5

def test_no_hit_can_only_use_empty_citations():
    provider=Mock();provider.complete.side_effect=[(call(),{}),(answer(),{})]
    qs,trace,_=generate_questions('Python',[],provider)
    assert trace[0]['result_ids']==[] and qs[0]['evidence_ids']==[]

@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv('LLM_BASE_URL','https://provider.example/v1')
    monkeypatch.setenv('LLM_API_KEY','dummy-test-key')
    monkeypatch.setenv('LLM_MODEL','test-model')

def test_http_contract(configured):
    def handle(request):
        assert str(request.url)=='https://provider.example/v1/chat/completions'
        assert request.headers['authorization']=='Bearer dummy-test-key'
        body=json.loads(request.content)
        assert body['tools'][0]['function']['name']=='search_profile'
        return httpx.Response(200,json={'choices':[{'message':answer()}],'usage':{'total_tokens':3}})
    message,usage=LLMProvider(httpx.MockTransport(handle)).complete([])
    assert usage['total_tokens']==3

@pytest.mark.parametrize('kind',['timeout','status','invalid'])
def test_http_errors(configured,kind):
    def handle(request):
        if kind=='timeout': raise httpx.ReadTimeout('secret response',request=request)
        if kind=='status': return httpx.Response(429,text='secret response')
        return httpx.Response(200,json={})
    with pytest.raises(ProviderError) as e: LLMProvider(httpx.MockTransport(handle)).complete([])
    assert 'secret' not in str(e.value)

def test_missing_config(monkeypatch):
    monkeypatch.delenv('LLM_API_KEY',raising=False)
    with pytest.raises(ProviderError,match='配置'): LLMProvider().complete([])

def test_insecure_endpoint(configured,monkeypatch):
    monkeypatch.setenv('LLM_BASE_URL','http://provider.example/v1')
    with pytest.raises(ProviderError,match='HTTPS'): LLMProvider().complete([])
