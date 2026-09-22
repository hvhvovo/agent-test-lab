"""小型人工标注 smoke 集，不能代表真实求职数据表现。"""
import json
from pathlib import Path
from app.core import extract_skills, Document, search_profile
cases=[('熟悉 Python 和 Git',['Python','Git']),('python SQL',['Python','SQL']),
       ('使用 FastAPI',['FastAPI']),('digital design',[]),('MySQL',[]),
       ('RAG + pytest',['RAG','pytest']),('沟通能力',[]),('Docker/Linux',['Docker','Linux'])]
correct=sum(extract_skills(jd)==expected for jd,expected in cases)
docs=[Document(source='cv',text='Python 图像处理'),Document(source='db',text='SQL 数据库查询'),Document(source='web',text='FastAPI 接口服务')]
retrieval=[('Python','cv'),('SQL','db'),('FastAPI','web')]
hits=sum(search_profile(q,docs,1)[0]['source']==source for q,source in retrieval)
result={'extraction_cases':len(cases),'exact_match':correct/len(cases),
        'retrieval_cases':len(retrieval),'hit_at_1':hits/len(retrieval),
        'scope':'handwritten smoke examples; no live LLM quality evaluation',
        'known_counterexample':{'input':'不要求 Python','actual':extract_skills('不要求 Python'),'desired_semantic_required_skills':[]}}
Path('reports').mkdir(exist_ok=True)
Path('reports/evaluation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
