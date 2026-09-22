# Agent Test Lab

一个求职分析小工具，也是用来练习 AI 应用测试的项目。

项目从一个提取 JD 技能关键词的 Python 脚本开始。目前可以输入岗位描述和项目经历，查看资料里提到了哪些技能、哪些还没有找到对应证据，并生成面试练习题。分析结果会保存在 SQLite 中，方便之后回看。

开发中关注两件事：功能能不能用，以及遇到空输入、模型超时、错误的工具调用时，程序能不能按预期处理。后端使用 FastAPI 和 Pydantic，测试使用 pytest。

## 目前能做什么

默认使用离线模式，不需要 API Key。技能匹配和资料检索通过规则完成，面试题使用模板生成。

配置模型后，可以切换到 LLM 模式。模型能够调用 `search_profile` 检索本次提交的资料，再根据检索结果生成面试题。程序会检查返回格式和引用 ID，并限制调用轮次。这个模式目前只用于面试题生成，技能分析仍然使用规则。

例如，岗位要求 Python、SQL 和 RAG，而项目资料只提到了 Python，报告会列出 Python 的相关片段，并将 SQL、RAG 标为“当前资料未检出”。这个结果用来帮助补充材料，不代表实际掌握程度。

## 本地运行

先下载代码，进入项目目录：

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

启动后打开 [演示页面](http://127.0.0.1:8000)，可以直接用页面里的示例生成报告。[接口文档](http://127.0.0.1:8000/docs) 支持手动发送请求。停止服务按 Ctrl+C。

报告保存在 `data/reports.sqlite3`，该目录已加入 Git 忽略规则。目前适合在本机使用，还没有登录和用户隔离功能。

### 接入模型（可选）

需要一个支持工具调用的 Chat Completions 兼容服务。在启动服务的同一个 PowerShell 窗口中设置：

```powershell
$env:LLM_BASE_URL = "https://你的服务地址/v1"
$env:LLM_MODEL = "你的模型名"
$env:LLM_API_KEY = "你的密钥"
```

随后启动服务，在页面选择 LLM 模式。`.env.example` 仅供参考，程序不会自动读取 `.env` 文件。

调用时会将 JD 和检索到的资料片段发送给模型服务，可能产生费用。密钥只在本机配置，不要提交到仓库。

## 测试

测试覆盖技能提取、输入校验、API、数据库读写，以及模型响应和工具调用的异常情况。测试中的模型请求使用 Mock，数据库使用临时文件，可以离线运行。

在项目根目录执行（Windows）：

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing --junitxml=reports/junit.xml --html=reports/tests.html --self-contained-html
```

macOS / Linux 将命令开头替换为 `.venv/bin/python`。运行后，用浏览器打开 `reports/tests.html` 查看报告。

已记录的一次本地测试结果为 **55 项通过，后端语句覆盖率 98.73%**，环境是 Linux / Python 3.12.14。这个数字不包含前端交互，也不代表模型回答质量。详细记录见 [测试结果](docs/TEST_RESULTS.md)，远程运行情况见仓库的 [Actions](https://github.com/hvhvovo/agent-test-lab/actions)。

另外提供两个脚本，分别检查少量手写检索样例和记录离线接口耗时：

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate
.\.venv\Scripts\python.exe -m scripts.benchmark
```

结果写入 `reports/`。耗时测试通过进程内 TestClient 串行执行，尚未做并发压测或真实模型性能测试。

## 代码在哪里

| 路径 | 内容 |
| --- | --- |
| `app/core.py` | 技能提取、文本分块、检索和规则分析 |
| `app/llm.py` | 模型请求、工具调用和输出校验 |
| `app/storage.py` | SQLite 报告存储 |
| `app/main.py` | FastAPI 接口 |
| `app/index.html` | 演示页面 |
| `tests/` | 单元测试和 API 测试 |
| `scripts/` | 检索评测、接口耗时统计 |
| `docs/` | 架构、测试用例和问题记录 |

接口包括 `GET /health`、`POST /api/reports`、`GET /api/reports` 和 `GET /api/reports/{id}`。请求字段和示例可以在启动后的接口文档中查看。

## 还需要改进的地方

最明显的问题是关键词规则不能理解语义。例如“不要求 Python”仍然会提取出 Python，也无法区分必备技能和加分项。资料检索目前按词项匹配，只支持纯文本，还没有接入向量检索或 PDF 解析。

LLM 部分已经有协议和异常处理测试，但还没有做真实模型的回答质量评测。引用 ID 正确，也不能保证回答准确使用了那段资料。

接下来准备先整理有代表性的测试样例，再逐步改进技能提取和资料检索。具体问题记在 [Bug 记录](docs/BUG_LOG.md) 中，测试设计和架构分别见 [测试用例](docs/TEST_CASES.md) 与 [系统架构](docs/ARCHITECTURE.md)。
