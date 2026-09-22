# 本次验证记录

- 环境：Linux，Python 3.12.14，依赖见 requirements*.txt。
- pytest：55 passed，2条依赖弃用警告；耗时0.90秒。
- 后端语句覆盖率：234 / 237 = 98.73%。不包含前端JS，不包含分支覆盖率。
- 模型：使用httpx.MockTransport/Mock测试，没有真实模型调用、没有产生API费用。
- 真实LLM正确率、供应商兼容性、Docker、远程GitHub Actions、Windows/Python3.14均未验证。
- 测试HTML和JUnit文件随项目ZIP提供；重新运行命令会生成本机的新报告。

## 本地微基准

100次串行请求，5次预热，进程内TestClient，包含SQLite写入：中位1.328ms，P95 2.047ms，最大17.492ms。仅代表本次运行环境的离线微基准，不是公网延迟、并发容量或LLM耗时。原始汇总见 reports/benchmark.json，脚本可复现。

## 小型规则/检索检查

8条手写技能提取 smoke 样例 exact match 8/8；3条手写词项检索样例 Hit@1 3/3。样本极小且不是独立业务评测集，不用于宣称产品准确率。额外记录否定句反例，见 reports/evaluation.json。

## 复现

```bash
python -m pytest --cov=app --cov-report=term-missing --junitxml=reports/junit.xml --html=reports/tests.html --self-contained-html
python -m scripts.benchmark
python -m scripts.evaluate
```
