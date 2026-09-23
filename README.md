# Agent Test Lab

面向测试开发与 AI 测试的面试训练工具。输入岗位要求和项目材料，生成场景题、查看证据、记录回答与复盘。

Python · FastAPI · Pydantic · SQLite · pytest

## 功能

- **场景题库**：30 道题，覆盖工具调用、RAG 评测、接口测试、事务、并发、性能和安全。每题包含追问、考察点与常见误区，支持技能匹配和难度筛选。
- **岗位分析**：统一技能词表、别名和边界匹配，展示资料中提及的技能及对应片段。
- **面试复盘**：作答、展开追问、勾选自评要点，保存到历史报告并导出 JSON。
- **模型出题**：可选 Chat Completions 兼容服务，通过只读检索工具获取资料；限制工具预算，校验参数、输出结构和引用 ID。
- **测试与评测**：单元/API/数据库/Mock 测试，检索标注集、离线耗时统计、HTML/JUnit 报告与 CI 配置。

题目示例：

> 模型连续四次检索后触发轮次上限，最后一次结果还没用于回答。怎样分别设计模型轮次与工具次数预算？
>
> 资料写着“尚未做过 RAG”，模型却问“你在 RAG 项目中如何优化召回”。引用 ID 是真的，怎样定位并评测这个问题？

## 运行

克隆仓库，或下载 ZIP 并解压，进入含 `README.md` 的目录。

```bash
git clone https://github.com/hvhvovo/agent-test-lab.git
cd agent-test-lab
```

Windows PowerShell：

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

macOS / Linux：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开 [训练页面](http://127.0.0.1:8000) 或 [API 文档](http://127.0.0.1:8000/docs)。默认题库模式无需密钥。可先用 `熟悉 Python、pytest、RAG 和 Agent` 生成报告，写下回答后保存复盘。

数据库位于 `data/reports.sqlite3`，重启服务会保留历史。升级前备份旧的 `data` 目录；复盘表会自动创建。当前为本地单用户版本，不直接开放到公网。

### 模型模式

在启动服务的同一个 PowerShell 窗口设置：

```powershell
$env:LLM_BASE_URL = "https://你的服务地址/v1"
$env:LLM_MODEL = "你的模型名"
$env:LLM_API_KEY = "仅在本机填写"
```

服务需要支持 `tools` 和 `tool_choice`。程序读取环境变量，不自动加载 `.env`。模型模式会发送 JD 和检索片段，可能产生费用；密钥、个人材料和数据库不要提交到仓库。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing --junitxml=reports/junit.xml --html=reports/tests.html --self-contained-html
.\.venv\Scripts\python.exe -m scripts.evaluate
.\.venv\Scripts\python.exe -m scripts.benchmark
```

macOS / Linux 将开头替换为 `.venv/bin/python`。HTML 报告生成在 `reports/tests.html`，CI 报告可从 [Actions](https://github.com/hvhvovo/agent-test-lab/actions) 下载。

本地后端验证：**102 项通过，语句覆盖率 98.59%**。检索集包含 **30 条合成标注样例**，分别记录 Recall@K、MRR 和无答案场景结果。指标口径与已知限制见 [测试结果](docs/TEST_RESULTS.md)。

真实模型评测独立运行，需先配置模型并显式确认：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_llm --live
```

结果按 8 个场景保存，需对照标注人工检查经历编造、否定和主体归属；Mock 通过率不作为真实模型质量指标。

## 结构

| 目录 / 文件 | 内容 |
|---|---|
| `app/question_bank.py` | 场景题、追问、考察点 |
| `app/skills.py` | 共用技能与别名匹配 |
| `app/core.py` | 选题、分块、二值 BM25 检索、证据分析 |
| `app/llm.py` | 模型适配、工具预算、整批参数预检 |
| `app/main.py` / `storage.py` | API 与 SQLite 存储 |
| `tests/` | 自动化测试 |
| `evals/` / `scripts/` | 标注集、评测和微基准 |

## 当前边界

检索使用词项与技能别名，尚未使用向量数据库；只接收文本。技能提及无法可靠区分否定、计划与真实经验。复盘为用户自评；引用存在不保证语义正确。真实模型质量、并发容量与 Docker 运行仍需单独验证。

[架构](docs/ARCHITECTURE.md) · [测试设计](docs/TEST_CASES.md) · [问题记录](docs/BUG_LOG.md) · [题库维护](docs/QUESTION_BANK.md)
