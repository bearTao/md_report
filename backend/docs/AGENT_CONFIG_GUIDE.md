# Agent配置指南

## 概述

从本版本开始，系统支持为每个Agent组件配置独立的LLM模型和参数。这意味着：

- **意图解析器（Intent Parser）** - 可以使用专门的模型来理解用户意图
- **响应生成器（Explanation Generator）** - 可以使用不同的模型来生成用户响应
- **AI内容优化（AI Refinement）** - 可以使用高质量模型来优化报告内容

每个组件都可以配置自己的：
- 模型名称（如 GPT-4, GPT-3.5 Turbo, Claude 3等）
- API Key
- API Base URL
- Organization ID
- Temperature（生成温度）
- Max Tokens（最大token数）
- Timeout（超时时间）

## 配置优先级

配置的加载优先级如下：

1. **数据库配置**（优先级最高）- 在Web界面的"Agent配置"页面中设置
2. **LLM级别配置** - 在agent_config.yaml中为每个组件单独配置
3. **全局API配置** - 在agent_config.yaml的api部分配置
4. **环境变量** - 如 OPENAI_API_KEY

## 使用场景

### 场景1：所有组件使用相同的API配置

如果所有Agent组件都使用相同的OpenAI API Key和Base URL：

1. 在"系统设置 > AI配置"中配置全局API Key和Base URL
2. 在"系统设置 > Agent配置"中只需为每个组件选择想要的模型即可
3. API Key和Base URL字段留空，系统会自动使用全局配置

### 场景2：不同组件使用不同的API配置

如果想为某些组件使用不同的API（比如意图解析用OpenAI，内容优化用Claude）：

1. 在"系统设置 > Agent配置"中为特定组件配置独立的API Key和Base URL
2. 其他组件的API配置留空，会使用全局配置

### 场景3：成本优化

根据不同任务的重要性选择不同成本的模型：

- **意图解析器**：使用GPT-4（准确性要求高）
- **响应生成器**：使用GPT-3.5 Turbo（成本低）
- **AI内容优化**：使用GPT-4（质量要求高）

## Web界面配置

1. 访问"系统设置 > Agent配置"
2. 展开想要配置的组件（意图解析器、响应生成器、AI内容优化）
3. 配置以下参数：
   - **模型**：可以从列表选择常用模型，或直接输入任意模型名称（支持所有提供商）
   - **API Key**（可选）：留空则使用全局AI配置
   - **API Base URL**（可选）：留空则使用全局AI配置
   - **Organization ID**（可选）：用于OpenAI的组织ID
   - **Temperature**：控制生成的随机性（0.0-2.0）
   - **Max Tokens**（可选）：限制生成的最大token数
   - **Timeout**：请求超时时间（秒）
4. 点击"保存配置"

### 支持的模型提供商

模型名称输入框支持自动完成，预设了常用模型选项，包括：

- **OpenAI**: gpt-4, gpt-4-turbo, gpt-3.5-turbo 等
- **Anthropic**: claude-3-opus-20240229, claude-3-sonnet-20240229, claude-2.1 等
- **Google**: gemini-pro, gemini-pro-vision 等
- **Azure OpenAI**: gpt-4-azure, gpt-35-turbo 等
- **国内提供商**: deepseek-chat, qwen-max, moonshot-v1-8k 等

你也可以直接输入任意自定义模型名称，只要你的API端点支持该模型即可。

## 文件配置（可选）

也可以通过配置文件进行配置，在`backend/config/agent_config.yaml`中：

```yaml
# AI内容优化配置
ai_refinement:
  llm:
    model: "gpt-4"
    api_key: "sk-..."  # 可选，为这个组件单独配置API Key
    api_base: "https://api.openai.com/v1"  # 可选
    temperature: 0.7
    max_tokens: null
    timeout: 90
  fallback_enabled: true
  use_db_config: true  # true表示优先使用数据库配置
```

## 报告预览中的模型选择

在报告预览页面使用AI Copilot时：

- 默认模型会自动设置为"AI内容优化"配置中的模型
- 这是因为AI Copilot主要用于优化和改进报告内容
- 用户仍然可以在下拉列表中手动选择其他模型

## 数据库迁移

首次使用此功能需要运行数据库迁移：

```bash
# 激活conda环境
conda activate test_md

# 运行迁移脚本
cd backend/migrations
python run_migration.py
```

迁移脚本会：
1. 创建`agent_llm_configs`表
2. 插入默认配置（可以在Web界面中修改）

## 默认配置

系统提供以下默认配置：

| 组件 | 默认模型 | Temperature | Timeout | 启用状态 |
|------|---------|-------------|---------|----------|
| 意图解析器 | gpt-4 | 0.1 | 60s | 启用 |
| 响应生成器 | gpt-3.5-turbo | 0.7 | 30s | 禁用 |
| AI内容优化 | gpt-4 | 0.7 | 90s | 启用 |

## 注意事项

1. **API Key安全性**：
   - 生产环境建议使用环境变量或加密存储API Key
   - 当前版本API Key以明文存储在数据库中
   
2. **配置生效时间**：
   - 配置修改后立即生效
   - 无需重启后端服务

3. **全局配置回退**：
   - 如果某个组件没有配置API Key，会自动使用全局AI配置
   - 确保至少配置了全局AI配置

4. **模型兼容性**：
   - 确保选择的模型与配置的API Base URL兼容
   - 例如：Claude模型需要配置Anthropic的API endpoint

## 故障排除

### 问题：Agent配置页面加载失败

**解决方案**：
1. 检查数据库迁移是否已运行
2. 检查后端日志查看错误信息
3. 确保数据库连接正常

### 问题：保存配置后没有生效

**解决方案**：
1. 检查浏览器控制台是否有错误
2. 检查后端API响应状态
3. 刷新页面重新加载配置

### 问题：AI Copilot使用的不是配置的模型

**解决方案**：
1. 检查"Agent配置"中"AI内容优化"的配置
2. 确保该配置已启用
3. 刷新报告预览页面

## API文档

### 获取Agent配置

```
GET /api/config/agent
```

响应示例：
```json
{
  "configs": {
    "intent_parser": {
      "component": "intent_parser",
      "model": "gpt-4",
      "api_key": null,
      "api_base": null,
      "organization": null,
      "temperature": 0.1,
      "max_tokens": null,
      "timeout": 60,
      "enabled": true
    },
    "ai_refinement": {
      "component": "ai_refinement",
      "model": "gpt-4",
      "api_key": null,
      "api_base": null,
      "organization": null,
      "temperature": 0.7,
      "max_tokens": null,
      "timeout": 90,
      "enabled": true
    }
  }
}
```

### 更新Agent配置

```
PUT /api/config/agent
```

请求体：
```json
{
  "component": "ai_refinement",
  "model": "gpt-4-turbo",
  "api_key": "sk-...",
  "api_base": "https://api.openai.com/v1",
  "organization": null,
  "temperature": 0.7,
  "max_tokens": 4000,
  "timeout": 90,
  "enabled": true
}
```

## 相关文件

- 数据库模型：`backend/app/models/db_models.py` - `AgentLLMConfig`类
- 配置管理：`backend/app/core/agent_config.py` - `ConfigManager`类
- API接口：`backend/app/api/config.py` - Agent配置endpoints
- 前端页面：`frontend/src/pages/settings/AgentSettings.tsx`
- 迁移脚本：`backend/migrations/pg/003_add_agent_llm_configs_table.sql`
