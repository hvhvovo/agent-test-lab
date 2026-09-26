import json
import pytest
import httpx
from app.grounding import apply_guard
from app.llm import LLMProvider, ProviderError

@pytest.mark.parametrize('prompt', [
 '假设你 Mock 了依赖，测试全绿但联调失败。你的 Mock 测试证明了什么？',
 '假设有同步调用，你把路由改成 async def 后变慢。如何验证你的判断？',
 '假设压测变慢。请描述你的排查路径并验证你的假设。',
 '你如何保证压测可复现？数据量如何影响你的结论？',
 '假设你负责选测试框架。你会如何改变最初的选择？',
])
def test_generic_possessives_do_not_imply_past(prompt):
 q=[{'question':prompt,'evidence_ids':[]}]
 assert apply_guard(q,{},'pytest')==q

@pytest.mark.parametrize('prompt', [
 '请结合一个你实际处理过的性能问题介绍取舍。',
 '请给出你实际用过的工具。',
 '请举一个你通过性能测试发现并解决的问题，你做了哪些改动？',
 '假设要做压测。请介绍你实际处理过的生产问题。',
])
def test_past_claims_require_evidence(prompt):
 out=apply_guard([{'question':prompt,'evidence_ids':[]}],{},'性能测试')
 assert 'no_evidence' in out[0]['grounding_guard']['reasons']

@pytest.mark.parametrize('prompt', [
 '你负责 pytest 接口测试，同学负责部署。当服务失败时，请描述你的排查顺序。',
 '部署由同学负责。当对方改了镜像导致你的测试失败时，你怎样定位？',
])
def test_supported_role_and_conditional_context(prompt):
 q=[{'question':prompt,'evidence_ids':['d:1']}]
 assert apply_guard(q,{'d:1':'团队同学部署服务，我负责 pytest 接口测试。'},'pytest')==q

@pytest.mark.parametrize('profile,prompt,reason', [
 ('共有57项测试通过，未进行并发压测。','已有57项功能测试如何改造成压测？','unsupported_test_type'),
 ('共有57项测试通过，未进行并发压测。','在只有功能测试通过的情况下，如何说明性能风险？','unsupported_test_type'),
 ('只实现过关键词检索。','请介绍你真正做过的关键词检索评测。','unsupported_evaluation_experience'),
])
def test_attributes_cannot_be_added(profile,prompt,reason):
 out=apply_guard([{'question':prompt,'evidence_ids':['d:1']}],{'d:1':profile},'测试')
 assert reason in out[0]['grounding_guard']['reasons']

@pytest.mark.parametrize('profile,prompt', [
 ('共有57项功能测试通过。','已有57项功能测试如何改造成压测？'),
 ('共有57项测试通过。','假设其中包含功能测试，你会如何改造？'),
 ('我做过关键词检索评测。','请介绍你真正做过的关键词检索评测。'),
])
def test_supported_or_conditional_attributes_kept(profile,prompt):
 q=[{'question':prompt,'evidence_ids':['d:1']}]
 assert apply_guard(q,{'d:1':profile},'测试')==q

@pytest.mark.parametrize('kind,code', [('connect','transport_error'),('json','response_json'),('shape','response_shape')])
def test_provider_diagnostics_hide_response_and_secret(monkeypatch,kind,code):
 monkeypatch.setenv('LLM_API_KEY','secret-marker')
 monkeypatch.setenv('LLM_MODEL','test')
 monkeypatch.setenv('LLM_BASE_URL','https://example.test')
 def handler(request):
  if kind=='connect': raise httpx.ConnectError('secret-marker',request=request)
  if kind=='json': return httpx.Response(200,text='secret-marker')
  return httpx.Response(200,json={'private':'secret-marker'})
 with pytest.raises(ProviderError) as exc:
  LLMProvider(transport=httpx.MockTransport(handler)).complete([])
 assert exc.value.code==code
 assert 'exception_type' in exc.value.details
 assert 'secret-marker' not in str(exc.value)+json.dumps(exc.value.details)


def test_bad_followup_does_not_replace_good_main_question():
 q=[{'question':'怎样定位连接池瓶颈？','evidence_ids':[],
     'follow_ups':['请介绍你实际处理过的问题。','如何观察连接数？']}]
 result=apply_guard(q,{},'性能测试')[0]
 assert result['question']==q[0]['question']
 assert result['follow_ups'][1]=='如何观察连接数？'
 assert '实际处理过' not in result['follow_ups'][0]
 assert result['grounding_guard']['action']=='field_repair'
