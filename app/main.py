import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from app.core import AnalysisRequest, analyze
from app.llm import LLMProvider, ProviderError, generate_questions
from app.storage import Store
from app.question_bank import QUESTION_BANK
from app.practice import PracticeRequest
from app.skills import extract_skills

logger = logging.getLogger('uvicorn.error')
ROOT = Path(__file__).resolve().parents[1]


def create_app(db_path=None, provider=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.store = Store(db_path or os.getenv('APP_DB_PATH', str(ROOT / 'data' / 'reports.sqlite3')))
        yield

    app = FastAPI(title='Agent Test Lab', version='0.2.0', lifespan=lifespan,
                  description='岗位分析、场景面试与复盘。本地单用户使用。')
    app.state.provider = provider or LLMProvider()

    @app.middleware('http')
    async def timing(request, call_next):
        started = time.perf_counter()
        request_id = uuid.uuid4().hex
        response = await call_next(request)
        elapsed = (time.perf_counter() - started) * 1000
        response.headers['X-Request-ID'] = request_id
        response.headers['X-Process-Time-Ms'] = f'{elapsed:.3f}'
        logger.info('request_id=%s method=%s path=%s status=%s elapsed_ms=%.3f',
                    request_id, request.method, request.url.path, response.status_code, elapsed)
        return response

    @app.get('/', include_in_schema=False)
    def home():
        return FileResponse(ROOT / 'app' / 'index.html')

    @app.get('/health')
    def health():
        return {'status': 'ok', 'version': '0.2.0'}

    @app.post('/api/reports', status_code=201)
    def make_report(payload: AnalysisRequest):
        started = time.perf_counter()
        report = analyze(payload)
        report['total_tokens'] = 0
        if payload.mode == 'llm':
            try:
                questions, trace, tokens = generate_questions(payload.jd, payload.documents, app.state.provider)
            except ProviderError as exc:
                raise HTTPException(502, str(exc)) from exc
            report.update(mode='llm', questions=questions, tool_trace=trace, total_tokens=tokens)
            report['question_selection'] = {'requested': 5, 'matched': len(questions)}
            report['limitations'][-1] = 'LLM仅增强面试题；引用存在性校验不等于事实真实性校验。'
        report['duration_ms'] = round((time.perf_counter() - started) * 1000, 3)
        return app.state.store.add(report)

    @app.get('/api/reports')
    def history(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
        return app.state.store.list(limit, offset)

    @app.get('/api/reports/{report_id}')
    def detail(report_id: int):
        report = app.state.store.get(report_id)
        if report is None:
            raise HTTPException(404, '报告不存在')
        return report

    @app.get('/api/questions')
    def questions(skill: str = Query('', max_length=100), level: str = Query('全部', pattern='^(全部|中等|深入)$')):
        return [q for q in QUESTION_BANK if (not skill or extract_skills(skill, q['skills']))
                and (level == '全部' or q['level'] == level)]

    @app.put('/api/reports/{report_id}/answers/{question_index}')
    def save_answer(report_id: int, question_index: int, payload: PracticeRequest):
        report = app.state.store.get(report_id)
        if report is None or not 0 <= question_index < len(report['questions']):
            raise HTTPException(404, '报告或题目不存在')
        points = report['questions'][question_index].get('checkpoints', [])
        if len(set(payload.covered_points)) != len(payload.covered_points) or any(
                i < 0 or i >= len(points) for i in payload.covered_points):
            raise HTTPException(422, '自评要点序号无效或重复')
        record = {**payload.model_dump(), 'updated_at': datetime.now(timezone.utc).isoformat(),
                  'assessment_type': 'self_review'}
        return app.state.store.save_practice(report_id, question_index, record)

    @app.get('/api/reports/{report_id}/answers')
    def answers(report_id: int):
        if app.state.store.get(report_id) is None:
            raise HTTPException(404, '报告不存在')
        return app.state.store.practices(report_id)

    return app

app = create_app()
