"""离线重放已保存的真实模型输出；不调用模型、不改写原始报告。"""
import argparse
import json
from pathlib import Path
from app.core import Document, chunks
from app.grounding import apply_guard, GUARD_VERSION


def replay(data):
    rows=[]
    for case in data['results']:
        if case.get('status')!='completed':
            continue
        retrieved={cid for call in case.get('trace',[]) for cid in call['result_ids']}
        evidence={c['id']:c['text'] for c in chunks([Document(source=case['id'],text=case['profile'])])
                  if c['id'] in retrieved}
        new=apply_guard(case['raw'], evidence, case['jd'])
        rows.append({'case_id':case['id'],'raw_questions':len(case['raw']),
            'old_fallbacks':sum('grounding_guard' in q for q in case['guarded']),
            'new_fallbacks':sum('grounding_guard' in q for q in new),
            'all_original_questions_preserved':new==case['raw'], 'new_questions':new})
    return {'scope':'离线重放，不是新一次真实模型调用；不自动判定语义正确率',
            'guard_version':GUARD_VERSION,'results':rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    args=parser.parse_args()
    print(json.dumps(replay(json.loads(args.report.read_text(encoding='utf-8-sig'))),ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
