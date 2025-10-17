# 配置 OpenAI API Base 说明

## ✅ 功能已添加

现在系统完全支持配置 `OPENAI_API_BASE`，可以使用代理或第三方OpenAI兼容服务！

## 📋 配置方式

### 方式 1：通过前端界面配置（推荐）

1. 访问 **AI设置页面**：http://localhost:5174/settings/ai

2. 填写配置信息：
   - **OpenAI API Key**: `sk-...`（必填）
   - **API Base URL**: 例如 `https://api.openai-proxy.com/v1`（可选）

3. 点击"保存配置"

4. 配置会保存到数据库，重启后依然有效

### 方式 2：通过环境变量配置

```bash
# 在启动后端前设置环境变量
export OPENAI_API_KEY="sk-..."
export OPENAI_API_BASE="https://api.openai-proxy.com/v1"

# 启动后端
cd /data/tao/code/xuqiu/backend
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**注意**：环境变量优先级高于数据库配置

### 方式 3：通过 API 配置

```bash
curl -X PUT http://localhost:8000/api/config/ai \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "api_key": "sk-...",
    "api_base": "https://api.openai-proxy.com/v1"
  }'
```

## 🔍 验证配置

### 查看当前配置

```bash
curl http://localhost:8000/api/config/ai | python3 -m json.tool
```

**响应示例**：
```json
{
    "configured": true,
    "provider": "openai",
    "api_base": "https://api.openai-proxy.com/v1"
}
```

### 测试AI生成

1. 创建包含 `ai_generation` 字段的模板
2. 生成报告
3. 查看日志验证是否使用了配置的 API Base：

```bash
tail -f /data/tao/code/xuqiu/backend/logs/app.log | grep "api_base"
```

## 🌍 常见 API Base URL

### 官方 OpenAI
```
https://api.openai.com/v1
```

### 国内代理示例（请替换为实际可用的）
```
https://api.openai-proxy.com/v1
https://api.openai-sb.com/v1
https://api.chatanywhere.com.cn/v1
```

### Azure OpenAI
```
https://<your-resource-name>.openai.azure.com/
```

### 本地部署的兼容服务
```
http://localhost:8080/v1
```

## 📝 完整流程示例

### 场景：使用国内代理

1. **配置 API**
```bash
curl -X PUT http://localhost:8000/api/config/ai \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "api_key": "sk-your-real-key",
    "api_base": "https://api.your-proxy.com/v1"
  }'
```

2. **验证配置**
```bash
curl http://localhost:8000/api/config/ai | python3 -m json.tool
```

3. **创建测试模板**（通过前端或API）

4. **生成报告并监控**
```bash
# 在一个终端监控日志
tail -f /data/tao/code/xuqiu/backend/logs/app.log | grep -E "app.executors.ai|API"

# 在另一个终端生成报告（通过前端）
# http://localhost:5174/generate
```

5. **查看详细日志**
日志会显示：
- ✅ 使用的 API Base URL
- ✅ AI 调用过程
- ✅ 响应时间
- ✅ 生成结果

## 🛠️ 技术细节

### 数据库字段

```sql
-- ai_provider_keys 表新增字段
ALTER TABLE ai_provider_keys ADD COLUMN api_base VARCHAR(500);
```

### 优先级

1. **环境变量** (`OPENAI_API_BASE`) - 最高优先级
2. **数据库配置** - 次优先级
3. **未配置** - 使用 OpenAI 默认 URL

### 后端代码流程

```python
# 1. 获取配置
openai_api_key, openai_api_base = get_ai_config(db)

# 2. 创建调度器
scheduler = ExecutionScheduler(
    openai_api_key=openai_api_key,
    openai_api_base=openai_api_base
)

# 3. AI Executor 使用配置
if self.openai_api_base:
    llm_kwargs["base_url"] = self.openai_api_base
```

## ❓ 常见问题

### Q: API Base 必须配置吗？
A: **不必须**。如果不配置，系统会使用 OpenAI 官方 API（`https://api.openai.com/v1`）

### Q: 如何判断是否在使用代理？
A: 查看日志文件，搜索 "LLM配置" 或 "api_base"：
```bash
grep "LLM配置" /data/tao/code/xuqiu/backend/logs/app.log
grep "api_base" /data/tao/code/xuqiu/backend/logs/app.log
```

### Q: 可以使用其他 AI 服务吗？
A: 可以！只要是 OpenAI API 兼容的服务，都可以通过配置 `api_base` 使用，例如：
- Azure OpenAI
- 本地部署的 LLaMA
- 其他兼容 OpenAI API 格式的服务

### Q: 环境变量和数据库配置可以混用吗？
A: 可以，但环境变量优先级更高。推荐生产环境使用环境变量，开发环境使用数据库配置。

### Q: 如何清除配置？
A: 通过 API 将 `api_base` 设置为 `null`：
```bash
curl -X PUT http://localhost:8000/api/config/ai \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "api_key": "sk-...",
    "api_base": null
  }'
```

## 🔒 安全提示

1. **不要将 API Key 提交到版本控制**
2. **生产环境建议使用环境变量或密钥管理系统**
3. **API Key 在数据库中是明文存储的（P0版本），生产环境需要加密**
4. **如果使用代理，确保代理服务可信**

## ✅ 更新内容总结

本次更新添加了以下功能：

- ✅ 数据库新增 `api_base` 字段
- ✅ 前端 AI 设置页面支持配置 API Base URL
- ✅ 后端 API 支持读取和保存 API Base
- ✅ AI Executor 使用配置的 API Base
- ✅ 支持环境变量配置
- ✅ 优先级：环境变量 > 数据库 > 默认值
- ✅ 完整的日志记录
- ✅ 向后兼容（不配置也能正常工作）

现在您可以轻松配置代理或使用其他 OpenAI 兼容的 AI 服务了！🎉

