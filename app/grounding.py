"""保守降级：可疑资料不用于经历追问；这是词法防线，不是语义证明。"""
import re
from copy import deepcopy
from app.topics import scenario_for

GUARD_VERSION = 'topic-fallback-v2'
RISK_PATTERNS = {
    'negation': r'尚未|未做|没做|未使用|没有.*经验|未进行|不会|从未|\b(?:never|not|no experience|haven.t)\b',
    'plan': r'计划|打算|准备学习|希望学习|\b(?:plan|planning|intend|will learn)\b',
    'ownership': r'团队|同学|同事|他人|\b(?:team|colleague|teammate)\b',
    'instruction': r'忽略.*(?:要求|指令)|称我|伪造|\bignore.*instructions\b',
}


def apply_guard(questions, evidence, jd):
    """同一原始输出做前后对照；只信任本次工具实际返回的片段。"""
    output = []
    for original in questions:
        q = deepcopy(original)
        ids = q.get('evidence_ids', [])
        reasons = []
        if not ids:
            # 通用知识问题不要求引用；只拦截明显的个人经历前提。
            wording = '\n'.join([q['question'], *q.get('follow_ups', []), *q.get('checkpoints', [])])
            if re.search(r'你(?:在|的|曾|已|负责)|您(?:在|的|曾)|your\s+(?:project|experience)|you\s+(?:built|implemented)', wording, re.I):
                reasons.append('no_evidence')
        elif any(cid not in evidence for cid in ids):
            reasons.append('unknown_evidence')
        else:
            text = '\n'.join(evidence[cid] for cid in ids)
            reasons = [name for name, pattern in RISK_PATTERNS.items()
                       if re.search(pattern, text, re.I)]
        if reasons:
            topic, seed, template_id = scenario_for(original['question'])
            q = {key: deepcopy(seed.get(key, [])) for key in
                 ('question', 'follow_ups', 'checkpoints')}
            q['question'] = '假设场景（不代表你的经历）：' + q['question']
            q.update(evidence_ids=[], grounding_guard={'version': GUARD_VERSION,
                     'action': 'scenario_fallback', 'reasons': reasons,
                     'topic': topic, 'topic_status': 'matched' if topic else 'unclassified',
                     'template_id': template_id})
        output.append(q)
    # 多题降级可能指向同一道种子题，去重而不伪造题目数量。
    return list({q['question']: q for q in output}.values())
