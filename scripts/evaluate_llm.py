"""真实调用与人工评分分离；同一模型输出做防线前后配对比较。"""
import argparse
import hashlib
import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from app.core import Document, chunks
from app.grounding import apply_guard, GUARD_VERSION
from app.llm import LLMProvider, ProviderError, generate_questions
ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(rows):
    completed = [r for r in rows if r['status'] == 'completed']
    result = {'attempts': len(rows), 'completed': len(completed),
              'request_failure_rate': (len(rows)-len(completed))/len(rows) if rows else None,
              'mean_attempt_ms': mean(r['duration_ms'] for r in rows) if rows else None,
              'reported_tokens_completed_only': sum(r.get('tokens', 0) for r in completed)}
    for variant in ('raw', 'guarded'):
        reviewed = [r for r in completed if type(r.get('review', {}).get(variant)) is bool]
        result[variant] = {'reviewed': len(reviewed), 'pending': len(completed)-len(reviewed),
                           'pass_rate_reviewed_only': mean(r['review'][variant] for r in reviewed) if reviewed else None}
    result['fallback_fraction_completed'] = (mean(any('grounding_guard' in q for q in r['guarded'])
                                                 for r in completed) if completed else None)
    topic_reviewed = [r for r in completed if type(r.get('topic_preserved')) is bool]
    result['topic_preservation'] = {
        'reviewed': len(topic_reviewed), 'pending': len(completed)-len(topic_reviewed),
        'pass_rate_reviewed_only': mean(r['topic_preserved'] for r in topic_reviewed) if topic_reviewed else None,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description='真实模型配对评测；--live 会产生 API 费用')
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--dataset', type=Path, default=ROOT/'evals/grounding.json')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--summarize', type=Path, help='只汇总人工填写的 review.raw/guarded 布尔值，不请求模型')
    args = parser.parse_args()
    if args.summarize:
        data = json.loads(args.summarize.read_text(encoding='utf-8'))
        print(json.dumps(summarize(data['results']), ensure_ascii=False, indent=2)); return
    if not args.live:
        parser.error('默认不请求网络。配置模型后使用 --live；评分后使用 --summarize 文件')
    if not 1 <= args.repeat <= 10:
        parser.error('--repeat 必须为1至10')
    if any(not os.getenv(k) for k in ('LLM_API_KEY', 'LLM_MODEL', 'LLM_BASE_URL')):
        parser.error('缺少模型环境变量；密钥只留在本机')
    cases = json.loads(args.dataset.read_text(encoding='utf-8'))
    if not cases or len({c['id'] for c in cases}) != len(cases):
        parser.error('数据集为空或样例ID重复')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = args.output or ROOT/'reports'/f'live-grounding-{stamp}.json'
    if output.exists():
        parser.error('输出文件已存在，请使用新文件名')
    metadata = {'started_utc': stamp, 'model': os.environ['LLM_MODEL'], 'python': platform.python_version(),
                'dataset_sha256': digest(args.dataset), 'llm_code_sha256': digest(ROOT/'app/llm.py'),
                'topics_sha256': digest(ROOT/'app/topics.py'),
                'question_bank_sha256': digest(ROOT/'app/question_bank.py'),
                'guard_version': GUARD_VERSION, 'guard_sha256': digest(ROOT/'app/grounding.py'),
                'repeat': args.repeat, 'temperature': 0,
                'scope': '同一模型原始输出的配对后处理；人工评分，不是独立模型A/B测试',
                'cost': None, 'cost_note': '供应商账单另行核对；失败请求可能已计费，token不等于费用'}
    rows = []
    output.parent.mkdir(parents=True, exist_ok=True)
    # 先独占创建，之后每次调用落盘；中断时已完成结果仍可阅读。
    with output.open('x', encoding='utf-8') as f:
        json.dump({'metadata': metadata, 'results': rows}, f, ensure_ascii=False)
    for repeat in range(args.repeat):
        for case in cases:
            started = time.perf_counter()
            docs = [Document(source=case['id'], text=case['profile'])]
            row = {**case, 'repeat': repeat+1, 'review': {'raw': None, 'guarded': None}, 'topic_preserved': None, 'review_notes': ''}
            try:
                qs, trace, tokens = generate_questions(case['jd'], docs, LLMProvider(), guard=False)
                retrieved = {cid for t in trace for cid in t['result_ids']}
                evidence = {c['id']: c['text'] for c in chunks(docs) if c['id'] in retrieved}
                row.update(status='completed', raw=qs, guarded=apply_guard(qs, evidence, case['jd']),
                           trace=trace, tokens=tokens)
            except ProviderError as exc:
                row.update(status='failed', error=str(exc))
            row['duration_ms'] = round((time.perf_counter()-started)*1000, 3)
            rows.append(row)
            payload = {'metadata': metadata, 'summary': summarize(rows), 'results': rows}
            temporary = output.with_suffix('.tmp')
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(output)
            print(f"{len(rows)}/{len(cases)*args.repeat}: {case['id']} {row['status']}")
    print(f'结果：{output}。按 criterion 填写 review 的 true/false；空值不算通过。')


if __name__ == '__main__':
    main()
