# 测试设计

| 范围 | 场景 | 预期 | 对应测试 |
|---|---|---|---|
| 提取 | 大小写、重复名单、顺序 | 规范名、去重、名单顺序 | test_extract |
| 提取边界 | digital/MySQL/C++ | 不误匹配Git/SQL，C++可命中 | test_extract |
| 输入 | 空白、None、错误类型、超长、额外字段 | 拒绝/422，不写库 | test_request_validation / test_invalid_api |
| 证据 | 长文本跨分块、无证据、无技能 | 引用可定位；不推断能力；覆盖率null | test_chunk_long_document_and_evidence 等 |
| 检索 | 多资料排名、无命中 | 正确source或空结果 | test_retrieval_ranking_and_no_hits |
| 数据库 | 新建、读取、重新启动 | 记录不丢失 | test_create_read_persist |
| 数据库 | SQL语句形文本 | 当作普通数据保存 | test_sql_content_is_data |
| API | 分页、不存在、非法分页 | 正确次序、404/422 | test_history_pagination_and_missing |
| 模型HTTP | 协议、超时、429、坏响应 | 请求正确、安全错误提示 | test_http_contract / test_http_errors |
| 工具调用 | 检索后引用、未知工具、坏参数、超限 | 合法执行；非法拒绝 | test_tool_call_then_grounded_answer 等 |
| 模型输出 | 非JSON、空题目、编造引用 | 拒绝，不作为成功结果 | test_bad_model_outputs |
| 失败事务 | 模型失败 | 502，数据库仍为空 | test_provider_failure_not_saved |

所有测试均可离线执行。浏览器交互、真实供应商兼容性、真实模型质量、容器和CI执行不在本次已验证范围。
