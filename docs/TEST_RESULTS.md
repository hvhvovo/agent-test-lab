# v0.2 增强版验证记录

环境：Linux / Python 3.12.14。后端测试 **132 passed，1条依赖弃用警告**。
语句覆盖率 397/402 = 98.76%，不包含前端JS和分支覆盖率。
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

24条真实模型检查样例已准备，尚未运行；工具选择正确率、语义依据正确率和真实模型延迟未测。
Docker配置保留，尚未执行容器验证。远程CI以GitHub Actions具体运行结果为准。

## 复现

```bash
python -m pytest --cov=app --cov-report=term-missing --junitxml=reports/junit.xml --html=reports/tests.html --self-contained-html
python -m scripts.evaluate
python -m scripts.benchmark
```

上一版浏览器冒烟已通过（本轮仅修改提示文案，未重跑浏览器）：生成报告、保存自评、重载历史、导出 JSON、题库筛选与390px窄屏溢出检查；未发现JS异常。当前Linux环境缺少中文字体，未据此验证中文字形。

此脚本默认pytest不收集。可在独立Python 3.12环境安装 `playwright==1.51.0`，执行 `python -m playwright install chromium --only-shell`，再运行 `python -m scripts.smoke_browser`。

新增12项经历依据与评分分母测试。可控故障重放确认：原先合法引用放行的否定经历问题，开启防线后转换为假设场景。该结果来自固定Mock，不代表真实模型语义正确率。

主题降级增强：新增18项测试，覆盖12类主问题主题、未知/歧义、词边界、去重与模板有效性。复现脚本确认召回优化题降级后仍围绕召回验证，不再变为提示词注入题。这是固定样例回归结果，不是对真实模型主题保持率的测量。
