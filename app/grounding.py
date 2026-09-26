"""保守降级：可疑资料不用于经历追问；这是词法防线，不是语义证明。"""
import re
from copy import deepcopy
from app.topics import scenario_for

GUARD_VERSION = 'premise-scope-v4'
RISK_PATTERNS = {
    'negation': r'尚未|未做|没做|未使用|没有.*经验|未进行|不会|从未|\b(?:never|not|no experience|haven.t)\b',
    'plan': r'计划|打算|准备学习|希望学习|\b(?:plan|planning|intend|will learn)\b',
    'ownership': r'团队|同学|同事|他人|\b(?:team|colleague|teammate)\b',
    'instruction': r'忽略.*(?:要求|指令)|称我|伪造|\bignore.*instructions\b',
}


def has_personal_premise(question):
    """有限的词法检查；引语豁免只覆盖明确的诚实应答教学场景。"""
    fields = [question['question'], *question.get('follow_ups', []),
              *question.get('checkpoints', [])]
    for text in fields:
        # 引语只有在明确的面试官提问场景中才移除；其后的陈述继续检查。
        text = re.sub(r'如果面试官问[“「][^”」]*[”」](?=[，,]?你会)', '面试情境', text)
        # 以句号/分号为边界处理条件语境，避免豁免随后真实经历陈述。
        for sentence in re.split(r'[。！？!?；;\n]', text):
            hypothetical = bool(re.match(r'\s*(?:假设|如果|若)', sentence))
            # 即使在假设句中，显式“曾/已经/做过”等过去经历仍不豁免。
            if re.search(r'(?:你|您)(?:曾|已|做过|完成过)|(?:你|您)(?:此前|过去|之前)(?:做过|完成过)', sentence):
                return True
            if hypothetical:
                continue
            if re.search(
                r'你(?:在|负责)|您(?:在|负责)|你[的](?!资料|问题|回答)|'
                r'您[的](?!资料|问题|回答)|your\s+(?:project|experience)|'
                r'you\s+(?:built|implemented)', sentence, re.I):
                return True
    return False


def apply_guard(questions, evidence, jd):
    """同一原始输出做前后对照；只信任本次工具实际返回的片段。"""
    output = []
    for original in questions:
        q = deepcopy(original)
        ids = q.get('evidence_ids', [])
        reasons = []
        if not ids:
            if has_personal_premise(q):
                reasons.append('no_evidence')
        elif any(cid not in evidence for cid in ids):
            reasons.append('unknown_evidence')
        else:
            text = '\n'.join(evidence[cid] for cid in ids)
            reasons = [name for name, pattern in RISK_PATTERNS.items()
                       if re.search(pattern, text, re.I)
                       and (name == 'instruction' or has_personal_premise(q))]
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
