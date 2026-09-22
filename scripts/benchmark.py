"""本地 TestClient 微基准；不是生产负载测试。"""
import json
import platform
import statistics
import tempfile
import time
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app

with tempfile.TemporaryDirectory() as tmp:
    with TestClient(create_app(Path(tmp)/'bench.db')) as client:
        body={'jd':'Python SQL FastAPI RAG','documents':[{'source':'demo','text':'使用 Python SQL 做数据处理。'}]}
        for _ in range(5): client.post('/api/reports',json=body)
        samples=[]
        for _ in range(100):
            start=time.perf_counter()
            response=client.post('/api/reports',json=body)
            assert response.status_code==201
            samples.append((time.perf_counter()-start)*1000)
        result={'scope':'offline API via in-process TestClient, sequential, SQLite write included',
                'requests':100,'warmup':5,'concurrency':1,'python':platform.python_version(),
                'platform':platform.system(),'median_ms':round(statistics.median(samples),3),
                'p95_ms':round(sorted(samples)[94],3),'max_ms':round(max(samples),3)}
        Path('reports').mkdir(exist_ok=True)
        Path('reports/benchmark.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(json.dumps(result,indent=2))
