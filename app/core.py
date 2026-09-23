"""可独立测试的规则提取、词项检索和证据匹配。无需网络。"""
import re
from app.question_bank import QUESTION_BANK
from pydantic import BaseModel, ConfigDict, Field, field_validator

SKILLS = ["Python", "SQL", "FastAPI", "Git", "RAG", "pytest", "Docker", "Linux", "SQLite", "MCP", "C++","Agent", "Function Calling"]

class Document(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    source: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=20000)

class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    jd: str = Field(min_length=1, max_length=10000)
    documents: list[Document] = Field(default_factory=list, max_length=20)
    mode: str = "offline"

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


def extract_skills(jd: str, skills: list[str] | None = None) -> list[str]:
    """按名单顺序去重；ASCII 词边界避免 Git 匹配 digital。不是语义理解。"""
    if not isinstance(jd, str):
        raise TypeError("jd must be a string")
    vocabulary = SKILLS if skills is None else skills
    result, seen = [], set()
    for skill in vocabulary:
        if not isinstance(skill, str) or not skill.strip():
            raise ValueError("skills must contain non-blank strings")
        skill = skill.strip()
        pattern = r"(?<![A-Za-z0-9_])" + re.escape(skill) + r"(?![A-Za-z0-9_])"
        if skill.casefold() not in seen and re.search(pattern, jd, re.IGNORECASE):
            result.append(skill)
            seen.add(skill.casefold())
    return result


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
    q = terms(query)
    ranked = []
    for chunk in chunks(documents):
        score = len(q & terms(chunk["text"])) / max(1, len(q))
        if score > 0:
            ranked.append({**chunk, "score": round(score, 4)})
    return sorted(ranked, key=lambda c: (-c["score"], c["id"]))[:top_k]

def select_questions(jd):
    selected = []

    for item in QUESTION_BANK:
        for skill in item["skills"]:
            if skill.lower() in jd.lower():
                selected.append({
                    "question": item["question"],
                    "evidence_ids": []
                })
                break

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
    questions = select_questions(request.jd)

    if not questions:
        questions = [{
            "question": "请描述一个你实际完成的项目及验证方法。",
            "evidence_ids": []
        }]
    return {"jd": request.jd, "mode": "offline", "required_skills": required,
            "evidence": evidence, "mentioned_skills": found, "unverified_skills": gaps,
            "mention_coverage": len(found)/len(required) if required else None,
            "questions": questions, "tool_trace": [],
            "limitations": ["关键词提及不证明能力；否定句也可能命中。",
                            "未检出只代表当前资料没有证据，不能断言用户不会。",
                            "离线模式是规则工作流，未调用大模型。"]}
