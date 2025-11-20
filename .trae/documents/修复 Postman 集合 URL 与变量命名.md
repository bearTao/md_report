## 问题诊断
- 导入后 URL 为空，只有 Params，根因是集合变量命名与用户期望不一致（`{{baseUrl}}` vs `{{base_url}}`）且部分条目使用对象式 URL 导致 UI 解析为仅参数视图。

## 修复内容
- 统一变量命名为 `{{baseUrl}}`，默认值 `http://localhost:8000`。
- 将所有请求的 `url` 字段改为纯字符串形式：`"{{baseUrl}}/path"`，避免对象式拆分导致地址为空的展示问题。
- 保留查询参数在原始字符串中（示例值可直接编辑），不再使用 `url.query` 字段，确保导入后地址完整可见。
- 校正所有端点使用的变量占位符（如 `{{report_id}}` → `{{reportId}}` 统一风格，或保持原风格但与集合变量一致）。

## 交付物
- 一份可直接导入的 Postman 集合 JSON（schema v2.1），覆盖：
  - 根与健康检查、OpenAPI
  - 模板管理 `/api/templates`
  - 报告与任务 `/api/reports`
  - 配置 `/api/config`
  - 数据库连接 `/api/config/db-connections`
  - 调试 `/api/debug`
- 集合级变量：`baseUrl`、`templateId`、`reportId`、`taskId`、`variableName`、`connectionId`（可在 Postman 中一键调整）。

## 验证
- 在 Postman 中 Import 后检查每个请求的 URL 显示形如 `{{baseUrl}}/health`、`{{baseUrl}}/api/reports/generate`。
- 变更集合变量 `baseUrl` 为实际服务地址（如 `http://127.0.0.1:8000`）并快速执行健康检查与列表接口验证。

## 可选增强（如需）
- 额外提供一个 Postman 环境 JSON（仅 `baseUrl`），便于一键选择环境。
- 为每个端点补充示例响应 `tests`（断言 2xx/特定字段）。

请确认以上方案，我将生成并提供修正后的 Postman 集合 JSON。