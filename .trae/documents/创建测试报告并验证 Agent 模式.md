## 前置条件
- 配置 `OpenAI` 访问密钥：通过 `PUT /api/config/ai` 或设置环境变量 `OPENAI_API_KEY` 与可选 `OPENAI_API_BASE`；Agent 的意图解析依赖该密钥（`app/services/agent/modification_agent.py`）。
- 服务端已启用 Reports/Templates/DB Connections 路由（`app/main.py`）。

## 接入远程数据库
- 新增数据库连接（PostgreSQL）：`POST /api/config/db-connections`
  - `name`: `test_microgrid`
  - `engine`: `postgresql`
  - `host`: `10.10.20.10`
  - `port`: `14632`
  - `database`: `test_db`
  - `username`: `microgrid`
  - `password`: `microgrid123`
  - `is_active`: `true`
- 验证连接：`POST /api/config/db-connections/{connection_id}/test` 应返回 `success=true`（参考 `app/api/db_connections.py:190`）。
- 生成时会自动注册到连接池（`app/api/reports.py:288-324`）；变量中的 `sql_config.connection` 需使用该连接名。

## 准备测试数据
- 在远程库创建并填充基础表：
  - `meter_readings(ts TIMESTAMP, device_id TEXT, energy_kwh NUMERIC, power_kw NUMERIC)`
  - `alarms(ts TIMESTAMP, device_id TEXT, level TEXT, message TEXT)`
- 插入最近 7~14 天的演示数据，覆盖多设备、峰谷变化与若干告警。将用于 SQL 变量与 AI 概述内容。

## 创建测试模板
- 模板 A「微电网日报」：聚合能耗并生成概述
  - 变量
    - `start_date`/`end_date`：`user_input`
    - `total_energy`：`sql`，`SELECT sum(energy_kwh) AS total_kwh FROM meter_readings WHERE ts >= :start_date AND ts < :end_date`；`result_mode=first_value`，`type=number`，`connection=test_microgrid`
    - `avg_power`：`sql`，`SELECT avg(power_kw) AS avg_kw FROM meter_readings WHERE ts >= :start_date AND ts < :end_date`；`first_value`
    - `generated_at`：`system`，`datetime` 字段
    - `ai_summary`：`ai_generation`，`model=gpt-4`，`prompt_template` 引用上述值生成中文摘要
  - 模板内容（示例）
    - 标题含时间范围与 `generated_at`
    - 能耗与功率统计段落
    - AI 概述段落 `{{ ai_summary }}`
- 模板 B「设备告警周报」：聚合告警并由 AI 生成整改建议
  - 变量
    - `week_start`/`week_end`：`user_input`
    - `top_alarms`：`sql`，查询 `alarms` 的不同设备告警计数 TOP5，`type=array`
    - `recommendations`：`ai_generation`，基于 `top_alarms` 生成中文建议
- 模板 C「最小演示模板」：仅含两个段落，方便测试「添加/修改/删除章节」的模板操作策略。
- 创建接口：`POST /api/templates`，先用 `template_renderer.validate_template` 校验（路由已集成）。

## 生成测试报告
- 调用：`POST /api/reports/generate`，传入 `template_id` 与 `inputs`
  - 模板 A 示例 `inputs`：`{"start_date":"2025-11-10","end_date":"2025-11-17"}`
  - 模板 B 示例 `inputs`：`{"week_start":"2025-11-10","week_end":"2025-11-17"}`
- 进度与事件：WebSocket 推送（任务开始/变量执行/渲染完成），同时在 `generation_task_variables` 与 `execution_logs` 写明细。
- 完成后：在 `reports` 写入最终 `markdown_content`、`status`、`duration_ms`、`cost_usd`。

## 验证 Agent 模式
- 修改入口：`POST /api/reports/{report_id}/modify?user_request=...`（`app/api/reports.py:1527`），内部 orchestrator：`ReportModificationAgent`。
- 场景用例
  - 参数更新：例如「把时间范围改为最近一周」→ 更新 `start_date/end_date`，重执行依赖变量，重新渲染
  - AI 内容优化：例如「把摘要改为更简洁的要点列表」→ 优化提示词，重生成 `ai_summary`
  - 模板操作：例如「新增一个“峰值时段分析”章节」或「删除告警列表章节」→ 修改临时模板，渲染新版本
- 会话与版本：
  - 首次修改自动创建 `conversation_sessions` 与 `report_states(version=1)`；每次成功修改生成新版本（`report_states.version+=1`）、写 `conversation_turns` 与可选 `report_modification_history`。
- 说明与结果：返回 `ReportModificationResponse`，含 `explanation`、`operations_summary`、新 `markdown_content` 与 `metadata`（耗时、成本、版本号）。

## 可观测性与日志
- 查询报告列表：`GET /api/reports`
- 查询单报告：`GET /api/reports/{report_id}`
- 任务状态：`GET /api/reports/tasks/{task_id}/status`
- 执行日志：`GET /api/reports/{report_id}/logs`（若有）
- 对话历史：`GET /api/reports/{report_id}/conversation`（`app/api/reports.py:1614`）

## 清理与回滚
- 删除报告（含变量记录与任务）：`DELETE /api/reports/{report_id}`
- 删除模板：`DELETE /api/templates/{template_id}`
- 停用或删除 DB 连接：`PUT/DELETE /api/config/db-connections/{connection_id}`

## 验证标准
- 生成阶段：所有变量执行成功，报告 `status=success`，Markdown 内容正确展示。
- Agent 修改：
  - 能正确识别意图并执行对应策略（参数更新/AI 优化/模板操作），返回新版本内容
  - 对话会话与版本化状态落库完整（`conversation_sessions`、`conversation_turns`、`report_states`）
  - WebSocket 进度事件可见；`execution_logs`/`generation_task_variables` 有对应记录（如涉及重执行）
- 数据库连接：远程库查询稳定；`db_connector` 注册成功日志可见（`reports.py:320`）。

## 交付项
- 远程库示例建表与数据 SQL
- 3 个模板（A/B/C）与其 metadata JSON
- 生成与修改的接口调用示例（curl/HTTP），含典型 `user_request` 文本
- 一次完整的 Agent 会话轨迹（版本号、操作摘要、说明文本）