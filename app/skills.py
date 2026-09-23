"""技能提取与选题共用词表和匹配规则。仅做提及识别，不推断掌握程度。"""
import re

ALIASES = {
    'Python': [], 'SQL': [], 'FastAPI': ['fast api'], 'Git': [],
    'RAG': ['检索增强生成', 'retrieval augmented generation'],
    'pytest': [], 'Docker': [], 'Linux': [], 'SQLite': [], 'MCP': [],
    'C++': [], 'Agent': ['智能体'],
    'Function Calling': ['tool calling', 'tool_calling', '工具调用', '函数调用'],
    'LLM': ['大模型', '大语言模型'], 'Pydantic': [],
    'API Testing': ['接口测试', '接口自动化', 'api testing'],
    'AI Testing': ['AI 测试', 'AI测试', '模型评测'],
    'Security': ['安全测试', '提示注入', '越权'],
    'HTTP': ['HTTPS'], 'CI/CD': ['持续集成', 'GitHub Actions'],
}
SKILLS = list(ALIASES)


def extract_skills(jd: str, skills: list[str] | None = None) -> list[str]:
    if not isinstance(jd, str):
        raise TypeError('jd must be a string')
    result, seen = [], set()
    for skill in SKILLS if skills is None else skills:
        if not isinstance(skill, str) or not skill.strip():
            raise ValueError('skills must contain non-blank strings')
        skill = skill.strip()
        canonical = next((k for k in ALIASES if k.casefold() == skill.casefold()), skill)
        variants = [canonical, *ALIASES.get(canonical, [])]
        for variant in variants:
            pattern = r'(?<![A-Za-z0-9_])' + re.escape(variant) + r'(?![A-Za-z0-9_])'
            if re.search(pattern, jd, re.IGNORECASE):
                if skill.casefold() not in seen:
                    result.append(skill)
                    seen.add(skill.casefold())
                break
    return result
