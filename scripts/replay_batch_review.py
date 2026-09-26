"""离线核对已标注重点题；不访问模型，不改写真实报告。"""
import argparse
import hashlib
import json
from pathlib import Path
from app.core import Document, chunks
from app.grounding import apply_guard, GUARD_VERSION


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    args=parser.parse_args()
    labels=json.loads((Path(__file__).resolve().parents[1]/'evals/batch_review_v1.json').read_text())
    content=args.report.read_bytes()
    if hashlib.sha256(content).hexdigest()!=labels['report_sha256']:
        parser.error('报告与标注版本不一致；不按相同题号套用其他报告')
    data=json.loads(content)
    reviewed=[]
    total=0
    new_changed=0
    for row in data['results']:
        if row['status']!='completed': continue
        retrieved={cid for t in row['trace'] for cid in t['result_ids']}
        evidence={c['id']:c['text'] for c in chunks([Document(source=row['id'],text=row['profile'])])
                  if c['id'] in retrieved}
        new=apply_guard(row['raw'],evidence,row['jd'])
        total+=len(row['raw'])
        new_changed+=sum(q not in new for q in row['raw'])
        for label in labels['labels']:
            if (label['case_id'],label['repeat'])!=(row['id'],row['repeat']): continue
            q=row['raw'][label['question_number']-1]
            old_action='keep' if q in row['guarded'] else 'change'
            new_action='keep' if q in new else 'change'
            reviewed.append({**label,'old_action':old_action,'new_action':new_action,
                             'matched':new_action==label['expected']})
    print(json.dumps({'scope':labels['scope'],'guard_version':GUARD_VERSION,
        'replayed_questions':total,'new_changed_questions':new_changed,
        'reviewed_questions':len(reviewed),'matched_labels':sum(r['matched'] for r in reviewed),
        'results':reviewed},ensure_ascii=False,indent=2))


if __name__=='__main__': main()
