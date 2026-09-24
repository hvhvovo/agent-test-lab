import json
import httpx
import pytest
from app.llm import LLMProvider, ProviderError
from scripts import smoke_deepseek, evaluate_llm

@pytest.mark.parametrize('limit',[0,8193,True])
def test_invalid_output_limit(limit):
    with pytest.raises(ValueError): LLMProvider(max_tokens=limit)

@pytest.mark.parametrize('finish',['stop','length'])
def test_payload_limit_and_usage_on_truncation(monkeypatch,finish):
    for k,v in {'LLM_API_KEY':'secret-test-value','LLM_MODEL':'deepseek-flash','LLM_BASE_URL':'https://api.deepseek.com'}.items():
        monkeypatch.setenv(k,v)
    def handle(request):
        body=json.loads(request.content)
        assert body['thinking']=={'type':'disabled'} and body['max_tokens']==2000
        assert body['tool_choice']=='none'
        return httpx.Response(200,json={'choices':[{'message':{'content':'{}'},'finish_reason':finish}],
                                       'usage':{'prompt_tokens':30,'completion_tokens':10,'total_tokens':40,'secret':'excluded'}})
    provider=LLMProvider(httpx.MockTransport(handle),max_tokens=2000,thinking='disabled')
    if finish=='length':
        with pytest.raises(ProviderError,match='截断'): provider.complete([],allow_tools=False)
    else:
        provider.complete([],allow_tools=False)
    assert provider.usage_records==[{'prompt_tokens':30,'completion_tokens':10,'total_tokens':40}]

def test_smoke_restores_environment_and_limits(monkeypatch):
    import os,sys
    monkeypatch.setenv('LLM_API_KEY','old')
    monkeypatch.setattr(smoke_deepseek,'getpass',lambda _: 'new')
    def evaluate():
        assert os.environ['LLM_API_KEY']=='new'
        assert sys.argv[sys.argv.index('--limit')+1]=='1'
        assert '--disable-thinking' in sys.argv
        raise RuntimeError('simulated stop')
    monkeypatch.setattr(smoke_deepseek,'evaluate',evaluate)
    old_args=sys.argv[:]
    with pytest.raises(RuntimeError): smoke_deepseek.main()
    assert os.environ['LLM_API_KEY']=='old' and sys.argv==old_args

def test_limit_runs_one_case(monkeypatch,tmp_path):
    dataset=tmp_path/'cases.json'
    dataset.write_text(json.dumps([{'id':str(i),'profile':'Python','jd':'Python','criterion':'generic'} for i in range(2)]))
    for name in ('LLM_API_KEY','LLM_MODEL','LLM_BASE_URL'): monkeypatch.setenv(name,'test')
    monkeypatch.setattr('sys.argv',['evaluate','--live','--limit','1','--dataset',str(dataset),'--output',str(tmp_path/'out.json')])
    calls=[]
    def generate(*args,**kwargs):
        calls.append(1)
        return [{'question':'如何验证接口？','evidence_ids':[]}],[],0
    monkeypatch.setattr(evaluate_llm,'generate_questions',generate)
    evaluate_llm.main()
    result=json.loads((tmp_path/'out.json').read_text())
    assert len(calls)==1 and result['metadata']['case_ids']==['0']
    assert len(result['results'])==1
