"""python -m scripts.evaluate；固定语料对比旧词项基线与二值 BM25。"""
import json
from pathlib import Path
from statistics import mean
from app.core import Document, chunks, terms, search_profile

ROOT = Path(__file__).resolve().parents[1]


def baseline(query, documents, k):
    q = terms(query)
    hits = [{**c, 'score': len(q & terms(c['text'])) / max(1, len(q))} for c in chunks(documents)]
    return sorted((h for h in hits if h['score'] > 0), key=lambda h: (-h['score'], h['id']))[:k]


def metrics(expected, actual):
    expected = set(expected)
    actual = list(dict.fromkeys(actual))
    if not expected:
        return {'recall': None, 'reciprocal_rank': None, 'empty_correct': not actual}
    return {'recall': len(expected & set(actual)) / len(expected),
            'reciprocal_rank': next((1/i for i,x in enumerate(actual,1) if x in expected),0),
            'empty_correct': None}


def evaluate(dataset):
    docs = [Document(**d) for d in dataset['documents']]
    ids = {c['id'] for c in chunks(docs)}
    if len({c['id'] for c in dataset['cases']}) != len(dataset['cases']):
        raise ValueError('duplicate evaluation case')
    rows = []
    for c in dataset['cases']:
        if not set(c['relevant_ids']) <= ids:
            raise ValueError('unknown labeled chunk')
        for name, fn in [('overlap_baseline', baseline), ('binary_bm25_aliases', search_profile)]:
            for k in [1,3,5]:
                actual = [h['id'] for h in fn(c['query'], docs, k)]
                rows.append({'case_id':c['id'],'split':c['split'],'query':c['query'],
                             'strategy':name,'k':k,'expected':c['relevant_ids'],'actual':actual,
                             **metrics(c['relevant_ids'],actual)})
    summaries=[]
    for sp in ['dev','holdout']:
        for name in ['overlap_baseline','binary_bm25_aliases']:
            for k in [1,3,5]:
                group=[r for r in rows if r['split']==sp and r['strategy']==name and r['k']==k]
                positive=[r for r in group if r['recall'] is not None]
                empty=[r for r in group if r['empty_correct'] is not None]
                summaries.append({'split':sp,'strategy':name,'k':k,'cases':len(group),
                    'answerable_cases':len(positive),'no_answer_cases':len(empty),
                    'macro_recall':round(mean(r['recall'] for r in positive),4),
                    'mrr':round(mean(r['reciprocal_rank'] for r in positive),4),
                    'no_answer_accuracy':round(mean(r['empty_correct'] for r in empty),4)})
    return {'dataset_version':dataset['version'],'scope':dataset['scope'],'case_count':len(dataset['cases']),
            'metric_unit':'chunk ID; macro average over answerable queries; no-answer cases reported separately',
            'summary':summaries,'details':rows}


if __name__ == '__main__':
    result=evaluate(json.loads((ROOT/'evals/retrieval.json').read_text()))
    (ROOT/'reports').mkdir(exist_ok=True)
    (ROOT/'reports/evaluation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result['summary'],ensure_ascii=False,indent=2))
