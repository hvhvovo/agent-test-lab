"""进程内串行微基准；不代表公网、模型或并发容量。"""
import json
import platform
import statistics
import tempfile
import time
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app
ROOT=Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(create_app(Path(tmp)/'bench.db')) as client:
            body={'jd':'Python SQL FastAPI RAG Agent','documents':[{'source':'demo','text':'使用 Python SQL 做数据处理。'}]}
            for _ in range(5):client.post('/api/reports',json=body)
            samples=[];errors=0
            for _ in range(100):
                start=time.perf_counter()
                response=client.post('/api/reports',json=body)
                samples.append((time.perf_counter()-start)*1000)
                errors+=response.status_code!=201
            result={'scope':'offline API via in-process TestClient; includes request validation, analysis, SQLite write and serialization',
                'requests':100,'warmup':5,'concurrency':1,'errors':errors,'error_rate':errors/100,
                'python':platform.python_version(),'platform':platform.system(),
                'mean_ms':round(statistics.mean(samples),3),'median_ms':round(statistics.median(samples),3),
                'p95_ms':round(sorted(samples)[94],3),'p99_ms':round(sorted(samples)[98],3),
                'max_ms':round(max(samples),3)}
            (ROOT/'reports').mkdir(exist_ok=True)
            (ROOT/'reports/benchmark.json').write_text(json.dumps(result,indent=2))
            print(json.dumps(result,indent=2))

if __name__=='__main__':main()
