"""可选浏览器冒烟：临时数据库、独立服务；不访问真实模型。"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory() as tmp:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        env={**os.environ,'APP_DB_PATH':str(Path(tmp)/'browser.sqlite3')}
        server=subprocess.Popen([sys.executable,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port)],
                                cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            url=f'http://127.0.0.1:{port}'
            for _ in range(100):
                if server.poll() is not None:raise RuntimeError('server exited')
                try:
                    urllib.request.urlopen(url+'/health',timeout=.2).close();break
                except OSError:time.sleep(.1)
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1280,'height':900})
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(url)
                page.locator('#jd').fill('熟悉 Agent 和 RAG，能够完成 pytest 接口测试')
                page.locator('#profile').fill('使用 Python 和 pytest 编写接口测试。')
                page.locator('#submit').click()
                expect(page.locator('#questions article')).to_have_count(5)
                first=page.locator('#questions article').first
                first.locator('textarea').first.fill('先固定输入和预期，模拟工具响应，检查实际调用次数和返回内容。')
                first.get_by_text('对照考察点与常见误区',exact=True).click()
                first.locator('input[type=checkbox]').first.check()
                first.get_by_role('button',name='保存回答与自评').click()
                expect(first.get_by_text('已保存 · 需复习',exact=True)).to_be_visible()
                with page.expect_download() as download:
                    page.locator('#export').click()
                exported=json.loads(Path(download.value.path()).read_text())
                assert len(exported['answers'])==1
                page.reload()
                page.locator('#history').click()
                page.locator('#history-items button').first.click()
                expect(page.locator('#questions textarea').first).to_have_value(exported['answers'][0]['answer'])
                page.locator('#tab-bank').click()
                page.locator('#bank-query').fill('RAG')
                expect(page.locator('#bank-items article').first).to_be_visible()
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                (ROOT/'reports').mkdir(exist_ok=True)
                page.screenshot(path=str(ROOT/'reports/browser-mobile.png'),full_page=True)
                assert not errors,errors
                browser.close()
                print('Browser smoke passed: generate, answer, self-review, history, export, bank filter, mobile overflow; no JS errors.')
        finally:
            server.terminate()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.kill();server.wait()

if __name__=='__main__':main()
