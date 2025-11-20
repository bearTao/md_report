# Agent配置功能更新说明

## 更新内容

### 1. 移除了报告预览中的模型选择框

**原因**：
- 后端的 `modify_report` API 不接受 `model` 参数
- 系统使用Agent配置中的模型，而不是用户在对话框中选择的模型
- 保留模型选择框会误导用户，让用户认为可以临时切换模型

**影响**：
- 报告预览页面的AI Copilot对话框中不再显示模型选择下拉框
- 系统自动使用"系统设置 > Agent配置 > AI内容优化"中配置的模型
- 用户如需更换模型，需要在Agent配置页面修改

### 2. 修复了Agent配置保存失败的Bug

**问题**：
- 当用户清空某些可选字段（API Key、API Base URL等）时，表单提交空字符串 `""`
- 后端期望接收 `null` 而不是空字符串，导致验证失败

**修复**：
- 前端自动将空字符串转换为 `null`
- 对模型名称进行trim处理，移除首尾空格

### 3. 支持自定义模型名称

**特性**：
- Agent配置页面的模型输入框改为AutoComplete组件
- 可以从预设列表选择常用模型
- 也可以直接输入任意自定义模型名称
- 支持多个提供商的模型（OpenAI、Anthropic、Google、国内提供商等）

## 使用步骤

### 首次使用

1. **运行数据库迁移**（只需执行一次）：
   ```bash
   conda activate test_md
   cd backend/migrations
   python run_migration.py
   ```

2. **配置全局AI设置**：
   - 访问"系统设置 > AI配置"
   - 配置OpenAI API Key和Base URL（作为默认配置）

3. **配置Agent组件**：
   - 访问"系统设置 > Agent配置"
   - 为每个组件配置模型和参数
   - 如果某个组件不需要独立的API Key，留空即可使用全局配置

### 修改报告

1. 打开任意报告预览页面
2. 点击"AI Copilot"按钮
3. 输入修改请求
4. 系统自动使用"AI内容优化"配置的模型进行处理

### 更换模型

如需更换AI Copilot使用的模型：
1. 访问"系统设置 > Agent配置"
2. 展开"AI内容优化"
3. 修改模型名称
4. 保存配置
5. 回到报告预览页面即可使用新模型

## 配置示例

### 场景1：所有组件使用相同API

```
全局AI配置：
- API Key: sk-xxx...
- API Base URL: https://api.openai.com/v1

Agent配置（所有组件）：
- API Key: (留空)
- API Base URL: (留空)
- 模型: gpt-4 / gpt-3.5-turbo 等
```

### 场景2：混合使用不同提供商

```
全局AI配置：
- API Key: sk-xxx... (OpenAI)
- API Base URL: https://api.openai.com/v1

Agent配置 - 意图解析器：
- 模型: gpt-4
- API Key: (留空) - 使用全局OpenAI配置

Agent配置 - AI内容优化：
- 模型: claude-3-opus-20240229
- API Key: sk-ant-xxx... (Anthropic)
- API Base URL: https://api.anthropic.com/v1
```

### 场景3：使用国内模型

```
Agent配置 - AI内容优化：
- 模型: deepseek-chat
- API Key: sk-xxx...
- API Base URL: https://api.deepseek.com/v1
- Temperature: 0.7
```

## 故障排除

### 问题1：保存配置时报错

**解决方案**：
1. 确保已运行数据库迁移脚本
2. 检查模型名称不为空
3. 检查Temperature值在0.0-2.0之间
4. 检查Timeout大于0

### 问题2：AI Copilot不工作

**检查项**：
1. 确保全局AI配置中至少配置了API Key
2. 确保"AI内容优化"组件已启用
3. 检查配置的API Key是否有效
4. 查看浏览器控制台和后端日志

### 问题3：模型名称不知道怎么写

**常用模型名称**：
- OpenAI: `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`
- Anthropic: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`
- Google: `gemini-pro`
- DeepSeek: `deepseek-chat`
- 通义千问: `qwen-max`, `qwen-turbo`

**如何确认**：
查看你使用的API提供商的文档，找到支持的模型列表。

## 技术细节

### API调用方式

报告修改API使用Query参数，而不是JSON body：

```http
POST /api/reports/{report_id}/modify?user_request=修改内容&session_id=xxx
```

### 配置优先级

```
数据库配置（Agent配置页面）
↓
agent_config.yaml中的LLM配置
↓
agent_config.yaml中的全局API配置
↓
环境变量（OPENAI_API_KEY等）
```

### 模型使用规则

- **意图解析器**：解析用户请求时使用
- **响应生成器**：生成对用户的响应时使用（可选，当前默认禁用）
- **AI内容优化**：AI Copilot修改报告时使用

## 相关文件

- 完整文档：`backend/docs/AGENT_CONFIG_GUIDE.md`
- 数据库迁移：`backend/migrations/pg/003_add_agent_llm_configs_table.sql`
- 前端配置页面：`frontend/src/pages/settings/AgentSettings.tsx`
- 后端API：`backend/app/api/config.py`
