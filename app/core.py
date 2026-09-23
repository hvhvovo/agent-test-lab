"""可独立测试的规则提取、词项检索和证据匹配。无需网络。"""
import re
import math
from collections import Counter
from typing import Literal
from copy import deepcopy
from app.skills import SKILLS, extract_skills
from app.question_bank import QUESTION_BANK
from pydantic import BaseModel, ConfigDict, Field, field_validator

class Document(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=20000)

class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    jd: str = Field(min_length=1, max_length=10000)
    documents: list[Document] = Field(default_factory=list, max_length=20)
    mode: str = "offline"
    question_count: int = Field(default=5, ge=1, le=10)
    level: Literal["全部", "中等", "深入"] = "全部"

    @field_validator("mode")
    @classmethod
    def valid_mode(cls, value):
        if value not in ("offline", "llm"):
            raise ValueError("mode must be offline or llm")
        return value

    @field_validator("documents")
    @classmethod
    def unique_sources(cls, value):
        names = [d.source for d in value]
        if len(names) != len(set(names)):
            raise ValueError("document sources must be unique")
        return value


def chunks(documents: list[Document]) -> list[dict]:
    output = []
    for doc in documents:
        for index, start in enumerate(range(0, len(doc.text), 400)):
            output.append({"id": f"{doc.source}:{index + 1}", "source": doc.source,
                           "text": doc.text[start:start + 500]})
    return output


def terms(text: str) -> set[str]:
    # 英文词项 + 中文二元组；这是词项检索 baseline，不是 embedding。
    english = re.findall(r"[a-z0-9_+#]+", text.casefold())
    chinese = re.findall(r"[\u4e00-\u9fff]+", text)
    return set(english + [s[i:i+2] for s in chinese for i in range(max(1, len(s)-1))])


def search_profile(query: str, documents: list[Document], top_k: int = 3) -> list[dict]:
    """二值词项 BM25：英文 token、中文二元组，并扩展已知技能别名。"""
    if not 1 <= top_k <= 10:
        raise ValueError("top_k must be between 1 and 10")
    corpus = chunks(documents)
    if not corpus:
        return []
    q = terms(query) | {"skill:" + s for s in extract_skills(query)}
    tokens = [terms(c["text"]) | {"skill:" + s for s in extract_skills(c["text"])} for c in corpus]
    df = Counter(t for ts in tokens for t in ts)
    avg_len = sum(map(len, tokens)) / len(tokens) or 1
    ranked = []
    for chunk, ts in zip(corpus, tokens):
        score = sum(math.log(1 + (len(corpus) - df[t] + .5) / (df[t] + .5)) * 2.2 /
                    (1 + 1.2 * (.25 + .75 * len(ts) / avg_len)) for t in q & ts)
        if score > 0:
            ranked.append({**chunk, "score": round(score, 6)})
    return sorted(ranked, key=lambda c: (-c["score"], c["id"]))[:top_k]


def select_questions(jd, limit=5, level="全部"):
    """确定性选题；优先覆盖未出现过的岗位技能与类别，再按匹配数排序。"""
    if not 1 <= limit <= 10:
        raise ValueError("limit must be between 1 and 10")
    if level not in ("全部", "中等", "深入"):
        raise ValueError("unknown level")
    candidates = []
    for item in QUESTION_BANK:
        matched = extract_skills(jd, item["skills"])
        if matched and (level == "全部" or item["level"] == level):
            candidates.append({**deepcopy(item), "matched_skills": matched, "evidence_ids": []})
    selected, covered, categories = [], set(), set()
    while candidates and len(selected) < limit:
        candidates.sort(key=lambda q: (-(len(set(q["matched_skills"]) - covered)),
                         -(q["category"] not in categories), -len(q["matched_skills"]), q["id"]))
        item = candidates.pop(0)
        selected.append(item)
        covered.update(item["matched_skills"])
        categories.add(item["category"])
    return selected


def analyze(request: AnalysisRequest) -> dict:
    required = extract_skills(request.jd)
    evidence = []
    for skill in required:
        hits = [c for c in chunks(request.documents) if extract_skills(c["text"], [skill])]
        evidence.append({"skill": skill, "status": "mentioned" if hits else "not_found",
                         "citations": [{"id": c["id"], "source": c["source"], "text": c["text"]}
                                       for c in hits[:3]]})
    found = [e["skill"] for e in evidence if e["status"] == "mentioned"]
    gaps = [e["skill"] for e in evidence if e["status"] == "not_found"]
    questions = select_questions(request.jd, request.question_count, request.level)

    if not questions:
        questions = [{
            "id": "general_failure",
            "kind": "fallback", "category": "项目复盘", "level": "中等",
            "question": "选一个你实际排查过的失败：输入和预期是什么？你依据哪些日志或测试定位原因，又怎样证明修改没有破坏原功能？",
            "follow_ups": ["如果问题不能稳定复现，你会补哪些观测信息？"],
            "checkpoints": ["区分现象和原因", "提供复现条件、修复和回归证据"],
            "pitfalls": ["只描述最终成功，不解释定位过程"],
            "evidence_ids": []
        }]
    return {"jd": request.jd, "mode": "offline", "required_skills": required,
            "evidence": evidence, "mentioned_skills": found, "unverified_skills": gaps,
            "mention_coverage": len(found)/len(required) if required else None,
            "questions": questions, "tool_trace": [],
            "question_selection": {"requested": request.question_count, "matched": sum(q.get("kind") != "fallback" for q in questions)},
            "evidence_chunks": chunks(request.documents),
            "limitations": ["关键词提及不证明能力；否定句也可能命中。",
                            "未检出只代表当前资料没有证据，不能断言用户不会。",
                            "离线模式是规则工作流，未调用大模型。"]}
