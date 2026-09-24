"""固定主题路由：只使用主问题，不执行其中指令；歧义时不宣称保留主题。"""
import re
from app.question_bank import QUESTION_BY_ID

# topic: (固定关键词, 对应题库ID)
TOPICS = {
 'retrieval_quality': (('召回','检索效果','检索优化','检索质量','同义','rerank','recall'), 'rag_rank'),
 'chunking': (('切片','分块','chunk','overlap'), 'rag_chunk'),
 'grounding': (('编造','幻觉','经历前提','证据支持','grounding'), 'rag_grounding'),
 'prompt_injection': (('提示词注入','资料指令','prompt injection'), 'agent_injection'),
 'tool_budget': (('调用次数','工具次数','轮次','预算','budget'), 'agent_budget'),
 'tool_batch': (('批量','整批','两个工具','部分执行'), 'agent_batch'),
 'tool_arguments': (('工具参数','参数语义','工具选择'), 'agent_tool_001'),
 'idempotency': (('幂等','重复请求','重复报告','idempotency'), 'agent_retry'),
 'schema': (('schema','json','格式校验','输出结构'), 'llm_schema'),
 'judge': (('评分器','judge','评分一致'), 'llm_judge'),
 'regression': (('回归','模型升级','提示词版本'), 'llm_regression'),
 'timeouts': (('超时','429','限流','timeout'), 'llm_timeout'),
 'fixtures': (('fixture','测试隔离','临时数据库'), 'pytest_fixture'),
 'mocking': (('mock','模拟响应'), 'pytest_mock'),
 'pagination': (('分页','pagination'), 'api_pagination'),
 'authorization': (('越权','权限','跨用户','鉴权'), 'api_auth'),
 'transactions': (('事务','回滚','原子','transaction'), 'sql_atomic'),
 'sql_injection': (('sql注入','sql 注入','参数化sql'), 'sql_injection'),
 'database_lock': (('数据库锁','sqlite锁','锁竞争','database is locked'), 'sql_lock'),
 'async': (('异步','阻塞','async'), 'python_async'),
 'cleanup': (('资源释放','连接泄漏','文件句柄'), 'python_cleanup'),
 'latency': (('p95','p99','延迟','耗时','吞吐'), 'http_latency'),
 'git_merge': (('合并冲突','git冲突','merge conflict'), 'git_conflict'),
 'containers': (('docker','容器','镜像'), 'docker_data'),
 'ci': (('ci/cd','持续集成','流水线','github actions'), 'ci_gate'),
 'logs': (('日志定位','日志排查','linux日志'), 'linux_logs'),
 'mcp': (('mcp',), 'mcp_contract'),
}

RETRIEVAL_SCENARIO = {
 'question': '假设 RAG 检索经常遗漏相关资料，你会怎样构建标注集、定位召回不足的原因，并验证优化效果？',
 'follow_ups': ['怎样区分切片、查询表达和排序造成的遗漏？', '优化召回后，怎样检查延迟与无关片段是否增加？'],
 'checkpoints': ['固定资料、查询与相关片段标注', '比较 Recall@K、MRR 和无答案场景', '控制变量比较切片、别名与排序方案', '用未参与调参的数据验证，并记录延迟'],
}


def detect_topic(text):
    scores = {}
    for topic, (aliases, _) in TOPICS.items():
        # ASCII关键词使用边界，避免 mock 命中 smocking 等片段。
        scores[topic] = sum(bool(re.search(
            r'(?<![a-z0-9_])'+re.escape(word)+r'(?![a-z0-9_])' if word.isascii() else re.escape(word),
            text, re.I)) for word in aliases)
    best = max(scores.values(), default=0)
    winners = [key for key, value in scores.items() if value == best and best > 0]
    return winners[0] if len(winners) == 1 else None


def scenario_for(text):
    topic = detect_topic(text)
    if topic == 'retrieval_quality':
        return topic, RETRIEVAL_SCENARIO, 'retrieval_quality_fallback'
    if topic:
        qid = TOPICS[topic][1]
        return topic, QUESTION_BY_ID[qid], qid
    return None, {
        'question': '假设接到一项技术任务，但现有资料不足以确定具体场景。你会先澄清哪些目标、约束和验收条件，再设计验证方案？',
        'follow_ups': ['哪些信息缺失时不能作出结论？'],
        'checkpoints': ['明确需求', '列出未知信息', '确定可验证的验收条件'],
    }, 'clarify_unknown_topic'
