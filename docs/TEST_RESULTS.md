# v0.2 验证记录

环境：Linux / Python 3.12.14。后端测试 **102 passed，2条依赖弃用警告**。
语句覆盖率 349/354 = 98.59%，不包含前端JS和分支覆盖率。
测试包含临时数据库与HTTP Mock，没有真实模型调用。通过率只适用于这批用例。

## 检索评测

12份固定合成资料、30条查询：开发集20条、留出诊断集10条。正例按片段ID宏平均；无答案单独计算。

| 集合 | 策略 | K | Recall@K | MRR@K |
|---|---|---:|---:|---:|
| dev | overlap_baseline | 1 | 78.89% | 0.9333 |
| dev | overlap_baseline | 3 | 100.00% | 0.9667 |
| dev | binary_bm25_aliases | 1 | 78.89% | 0.9333 |
| dev | binary_bm25_aliases | 3 | 100.00% | 0.9667 |
| holdout | overlap_baseline | 1 | 56.25% | 0.6250 |
| holdout | overlap_baseline | 3 | 87.50% | 0.7292 |
| holdout | binary_bm25_aliases | 1 | 56.25% | 0.6250 |
| holdout | binary_bm25_aliases | 3 | 100.00% | 0.7917 |

两种策略的无答案样例空结果率均为100%（开发5条，留出2条）。样例少、无答案查询偏容易；留出集由同一项目编写，不是外部独立基准。不能把100%召回当真实业务正确率。单条结果见 `reports/evaluation.json`。

## 离线微基准

TestClient进程内串行100次请求，5次预热，包含校验、分析、数据库写入和序列化。
平均 2.784ms，中位 2.311ms，P95 3.181ms，P99 17.325ms；错误 0/100。
不包含公网网络或真实模型，也不是并发容量测试。环境敏感，原始统计见 `reports/benchmark.json`。

## 模型质量与部署

8条真实模型检查样例已准备，尚未运行；工具选择正确率、语义依据正确率和真实模型延迟未测。
Docker配置保留，尚未执行容器验证。远程CI以GitHub Actions具体运行结果为准。

## 复现

```bash
python -m pytest --cov=app --cov-report=term-missing --junitxml=reports/junit.xml --html=reports/tests.html --self-contained-html
python -m scripts.evaluate
python -m scripts.benchmark
```

浏览器冒烟已通过：生成报告、保存自评、重载历史、导出 JSON、题库筛选与390px窄屏溢出检查；未发现JS异常。当前Linux环境缺少中文字体，未据此验证中文字形。

此脚本默认pytest不收集。可在独立Python 3.12环境安装 `playwright==1.51.0`，执行 `python -m playwright install chromium --only-shell`，再运行 `python -m scripts.smoke_browser`。
