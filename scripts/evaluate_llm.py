"""显式 --live 才产生模型调用；输出待人工评价的结果，不自动宣称质量正确率。"""
import argparse
import json
import time
from pathlib import Path
from app.core import Document
from app.llm import LLMProvider, ProviderError, generate_questions
ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description='真实模型的引用与经历前提检查；可能产生 API 费用')
    parser.add_argument('--live',action='store_true',help='确认调用已配置的真实模型服务')
    args=parser.parse_args()
    if not args.live:
        parser.error('请配置模型后显式传入 --live；默认不发起网络请求')
    results=[]
    for case in json.loads((ROOT/'evals/grounding.json').read_text()):
        started=time.perf_counter()
        try:
            qs,trace,tokens=generate_questions(case['jd'],[Document(source=case['id'],text=case['profile'])],LLMProvider())
            row={'status':'completed','questions':qs,'trace':trace,'tokens':tokens}
        except ProviderError as exc:
            row={'status':'failed','error':str(exc)}
        results.append({**case,**row,'duration_ms':round((time.perf_counter()-started)*1000,3),
                        'human_verdict':None,'review_notes':''})
    (ROOT/'reports').mkdir(exist_ok=True)
    output=ROOT/'reports/live-grounding.json'
    output.write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print('结果已保存至 reports/live-grounding.json；请按 criterion 人工判定，不等同自动质量评分。')

if __name__=='__main__':
    main()
