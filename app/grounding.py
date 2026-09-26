"""保守降级：可疑资料不用于经历追问；这是词法防线，不是语义证明。"""
import re
from copy import deepcopy
from app.topics import scenario_for

GUARD_VERSION = 'premise-fields-v6'
RISK_PATTERNS = {
    'negation': r'尚未|未做|没做|未使用|没有.*经验|未进行|不会|从未|\b(?:never|not|no experience|haven.t)\b',
    'plan': r'计划|打算|准备学习|希望学习|\b(?:plan|planning|intend|will learn)\b',
    'ownership': r'团队|同学|同事|他人|\b(?:team|colleague|teammate)\b',
    'instruction': r'忽略.*(?:要求|指令)|称我|伪造|\bignore.*instructions\b',
}


# 只把具体经历对象视为所属经历；“你的判断/假设/排查顺序”不是履历。
PAST_CLAIM = re.compile(
    r'(?:你|您)(?:曾|已|做过|完成过)|(?:你|您)(?:此前|过去|之前)(?:做过|完成过)|'
    r'(?:你|您)(?:实际|真正)(?:处理过|用过|做过|完成过)|'
    r'(?:你|您)通过.{0,30}(?:发现|解决)|(?:你|您)做了哪些改动')
PERSONAL_OBJECT = re.compile(
    r'(?:你|您)(?:在|负责)|(?:你|您)的\s*(?:[A-Za-z][A-Za-z0-9_+.-]*\s*)?(?:项目|系统|部署|研发经历|召回)|'
    r'your\s+(?:project|experience)|you\s+(?:built|implemented)', re.I)


def field_has_premise(text):
    """假设语境在一个字段内延续；显式过去经历不随语境豁免。"""
    text = re.sub(r'如果面试官问[“「][^”」]*[”」](?=[，,]?你会)', '面试情境', text)
    hypothetical = False
    for sentence in re.split(r'[。！？!?；;\n]', text):
        if PAST_CLAIM.search(sentence):
            return True
        if re.match(r'\s*(?:假设|如果|若|当)', sentence):
            hypothetical = True
        if not hypothetical and PERSONAL_OBJECT.search(sentence):
            return True
    return False


def has_personal_premise(question):
    return any(field_has_premise(text) for text in
               [question['question'], *question.get('follow_ups', []),
                *question.get('checkpoints', [])])


def unsupported_attributes(question, evidence):
    """有限属性检查，不把词法匹配宣传为通用事实核验。"""
    reasons = []
    for text in [question['question'], *question.get('follow_ups', []),
                 *question.get('checkpoints', [])]:
        # 明确未知类型时，不能将已有通过项断言成某一类型；假设讨论可保留。
        if ('测试通过' in evidence or '检查通过' in evidence) and not re.match(r'\s*(?:假设|如果|若)', text):
            for kind in ('功能', '单元', '接口', '端到端', '集成'):
                if kind + '测试' in text and not re.search(kind + r'测试', evidence):
                    if re.search(r'(?:已有|只有|全部|通过|共|\d+\s*项).{0,12}' + kind + r'测试|' + kind + r'测试.{0,8}(?:通过|全部)', text):
                        reasons.append('unsupported_test_type')
        if '关键词检索' in evidence and not re.search(r'关键词检索.{0,6}(?:评测|评估|标注)', evidence):
            if re.search(r'(?:实际|真正|做过).{0,12}关键词检索评测', text):
                reasons.append('unsupported_evaluation_experience')
    return list(dict.fromkeys(reasons))


def ownership_is_supported(question, evidence):
    """仅豁免逐字对应的明确职责；不尝试推断同义词或团队职责。"""
    duties = re.findall(r'(?:^|[，,。；;！？!?\n])\s*我负责\s*([^，,。；;！？!?\n]+)', evidence)
    if not duties:
        return False
    remaining = deepcopy(question)
    def strip_supported(text):
        for duty in duties:
            # 要求职责后有分句边界，避免“接口测试”豁免“接口测试和部署”。
            text = re.sub(r'(?:你|您)负责\s*' + re.escape(duty.strip()) +
                          r'(?=[，,。；;！？!?\n]|$)', '该职责', text)
        return text
    remaining['question'] = strip_supported(question['question'])
    for field in ('follow_ups', 'checkpoints'):
        remaining[field] = [strip_supported(t) for t in question.get(field, [])]
    return not has_personal_premise(remaining)


def apply_guard(questions, evidence, jd):
    """同一原始输出做前后对照；只信任本次工具实际返回的片段。"""
    output = []
    for original in questions:
        q = deepcopy(original)
        ids = q.get('evidence_ids', [])
        reasons = []
        text = ''
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
        if text:
            reasons.extend(unsupported_attributes(q, text))
        if 'ownership' in reasons and ownership_is_supported(q, text):
            reasons.remove('ownership')
        if reasons:
            topic, seed, template_id = scenario_for(original['question'])
            # 仅附属字段含经历前提时，保留正常主问题，只替换有问题的追问/考察点。
            auxiliary_only = (not field_has_premise(original['question'])
                              and has_personal_premise(original)
                              and not any(reason in reasons for reason in
                                  ('instruction', 'unknown_evidence', 'unsupported_test_type',
                                   'unsupported_evaluation_experience')))
            if auxiliary_only:
                q = deepcopy(original)
                for field in ('follow_ups', 'checkpoints'):
                    q[field] = [
                        ('假设开展相关工作，你会怎样设计验证步骤？' if field == 'follow_ups'
                         else '说明假设方案的验证方法，不要求提供实际经历')
                        if field_has_premise(value) else value
                        for value in q.get(field, [])]
            else:
                q = {key: deepcopy(seed.get(key, [])) for key in
                     ('question', 'follow_ups', 'checkpoints')}
                q['question'] = '假设场景（不代表你的经历）：' + q['question']
            q.update(evidence_ids=[], grounding_guard={'version': GUARD_VERSION,
                     'action': 'field_repair' if auxiliary_only else 'scenario_fallback', 'reasons': reasons,
                     'topic': topic, 'topic_status': 'matched' if topic else 'unclassified',
                     'template_id': template_id})
        output.append(q)
    # 多题降级可能指向同一道种子题，去重而不伪造题目数量。
    return list({q['question']: q for q in output}.values())
