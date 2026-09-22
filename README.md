# Agent Test Lab · AI 应用及自动化测试平台

一个从 Python JD Parser 学习项目演进而来的 **本地单用户、可运行的 v0.1 MVP**：使用 FastAPI、Pydantic 和 SQLite，围绕求职分析工作流建立自动化测试。默认无需 API Key；可选模型模式提供基于资料检索工具的面试题生成。


## 已实现

- JD 关键词提取：忽略大小写、名单去重、ASCII 边界匹配；保留原技能名称。
- 读取用户在页面/API 提交的文本资料，按片段保留 source/id。
- 资料证据匹配和词项检索 baseline（英文词项 + 中文二元组、重叠分块）。
- 输出“资料中提及 / 资料未检出”、引用片段、面试练习题。
- 可选 LLM 模式：Chat Completions 兼容 API、有界 search_profile 工具调用、JSON 输出与引用 ID 校验、token 计数。
- SQLite 报告保存、详情查询、分页历史；路径不依赖启动目录。
- 浏览器演示页、OpenAPI `/docs`、请求 ID 和耗时日志。
- pytest 参数化单元测试、API 测试、数据库持久化测试、HTTP Mock、模型异常与工具调用测试。
- HTML/JUnit/覆盖率报告生成、本地微基准和小型检索评测脚本。
- Dockerfile 和 GitHub Actions 配置（尚未在 Docker 或远程 Actions 上验证）。

## 一分钟启动（Windows PowerShell）

先克隆仓库或下载并解压，在含 README.md 的文件夹里打开终端。已有的 jd_parser.py 和 history.json 可保留在原文件夹；本项目不读取或迁移旧历史。

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

浏览器打开 http://127.0.0.1:8000 。默认页面有合成示例资料，点击“生成报告”即可。服务关闭用 Ctrl+C。不需要激活虚拟环境，不需要修改 PowerShell 执行策略。

macOS/Linux：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

数据库默认在项目 `data/reports.sqlite3`；数据目录已被 Git 忽略。设置 `APP_DB_PATH` 可覆盖。此版本无登录、访问隔离、限流，不要直接开放到公网或存放他人的真实简历。

## 使用与接口

| 操作 | 接口 | 说明 |
|---|---|---|
| 健康检查 | GET /health | 状态、版本 |
| 创建分析 | POST /api/reports | 校验输入、分析、写库，成功201 |
| 查看历史 | GET /api/reports?limit=20&offset=0 | 倒序分页 |
| 查看单份 | GET /api/reports/1 | 不存在返回404 |

请求示例：

```json
{
  "jd": "熟悉 Python 和 SQL，了解 RAG",
  "documents": [{"source": "课程项目", "text": "使用 Python 分析实验数据。"}],
  "mode": "offline"
}
```

这份资料会让 Python 标记为 `mentioned`，SQL/RAG 标记为 `not_found`。这表示证据提及，**不是面试能力分数，更不是录用概率**。资料内的否定或自述不自动证明真实能力。

### 可选模型模式

默认离线功能完整可用。真实调用需要支持 tools 的 Chat Completions 兼容服务。在启动服务器的同一个 PowerShell 中设置：

```powershell
$env:LLM_BASE_URL = "https://你的服务地址/v1"
$env:LLM_MODEL = "你的模型名"
$env:LLM_API_KEY = "仅在你本机填写"
```

然后启动服务，在页面选择 LLM 模式。`.env.example` 只是配置示例，程序不会自动加载 `.env`。LLM 模式会发送 JD，以及模型检索到的资料片段；供应商可能计费。不要将 Key、真实资料或本地数据库提交到 Git。

此模式由模型选择是否调用 `search_profile`，最多4轮/4次工具调用。只允许这个只读工具。面试题经过结构和引用 ID 校验；引用真实存在仍不等于内容得到充分支持。失败返回502且不保存为成功报告，没有静默降级或自动重试。技能提取/Gap 分析目前仍然使用规则。

## 运行测试

另开一个终端，在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=app --cov-report=term-missing --junitxml=reports/junit.xml --html=reports/tests.html --self-contained-html
.\.venv\Scripts\python.exe -m scripts.evaluate
.\.venv\Scripts\python.exe -m scripts.benchmark
```

如需复现本次依赖图，可安装 `requirements-lock.txt`（Linux/Python3.12快照）；跨平台依赖以 requirements-dev.txt 为入口。

测试使用临时数据库和 HTTP Mock，不访问模型服务，也不写你的实际数据库。`reports/tests.html` 可直接用浏览器打开。

本次实测：**55 passed，后端语句覆盖率98.73%**，Linux / Python 3.12.14。详见 [测试结果](docs/TEST_RESULTS.md)。覆盖率不是正确率，不包含浏览器 UI 的自动化覆盖。Windows、Python 3.14、Docker 与 Actions 尚待实际环境验证。

## 结构与阅读顺序

| 文件 | 作用 |
|---|---|
| app/core.py | 输入模型、extract_skills、检索与规则分析 |
| app/storage.py | SQLite 参数化读写 |
| app/llm.py | 模型适配器、工具白名单、输出校验 |
| app/main.py | API、日志和错误映射 |
| app/index.html | 本地演示页面 |
| tests/ | 单元/API/Mock/持久化/工具调用测试 |
| scripts/ | 可复现微基准、检索评测 |
| docs/ | 架构、测试设计、Bug记录、学习顺序 |
| reports/ | 本次测试摘要与实测数据 |

建议先读 extract_skills 和 test_extract，再看请求校验、数据库和 API，最后看 LLM。不要用一次运行成功替代理解代码。

## 已知问题与计划

- v0.1 是规则工作流 + 可选工具调用面试助手，不是完整的自主求职 Agent。
- 词项检索 baseline 不是向量 RAG；不支持 PDF/OCR，不识别同义表述；只处理提交的纯文本。
- 关键词规则不能处理否定、必备/加分或复杂语义，例如“不要求 Python”。
- 面试题没有经过真实模型质量评测；Mock 测试只说明协议、异常处理和引用约束按预期工作。
- 没有身份认证、并发负载测试、生产监控、自动重试、成本金额计算或语义引用验证。
- 单次处理最多20份、每份20000字符，JD最多10000字符；这是教学版限制。
- 后续：真实标注集 → embedding 检索 → 输出质量评测 → 认证与部署。具体先做哪个，以能解释和验证为准。


