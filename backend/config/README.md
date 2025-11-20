# Agent配置说明

本目录包含Agent相关的配置文件。配置系统支持多种配置来源，优先级如下：

**环境变量 > 配置文件 > 默认值**

## 配置文件

### agent_config.yaml
实际使用的配置文件。可以根据需要修改此文件。

### agent_config.example.yaml
配置文件示例，包含所有可配置项的说明。

## 配置项说明

### API配置 (`api`)
```yaml
api:
  api_key: null          # OpenAI API密钥
  api_base: null         # API基础URL（用于代理或自定义端点）
  organization: null     # OpenAI组织ID（可选）
```

**推荐做法**: 通过环境变量设置API密钥，不要直接写在配置文件中：
```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_API_BASE="https://api.openai.com/v1"  # 可选
```

### 意图解析器配置 (`intent_parser`)
```yaml
intent_parser:
  enabled: true          # 是否启用意图解析器
  max_retries: 2         # 最大重试次数
  llm:
    model: "gpt-4"       # 使用的模型
    temperature: 0.1     # 生成温度（0.0-2.0）
    max_tokens: null     # 最大生成token数
    timeout: 60          # 请求超时时间（秒）
```

**说明**:
- `model`: 意图解析需要高质量模型，推荐使用 gpt-4
- `temperature`: 较低值(0.1)确保解析的一致性和准确性
- `max_tokens`: null表示无限制

### 响应生成器配置 (`explanation_generator`)
```yaml
explanation_generator:
  use_llm: false         # 是否使用LLM生成响应
  llm:
    model: "gpt-3.5-turbo"  # 使用较便宜的模型
    temperature: 0.7     # 生成温度
    max_tokens: 500      # 限制响应长度
    timeout: 30
```

**说明**:
- `use_llm`: 默认false使用模板模式，成本更低
- 如果启用LLM模式，可使用 gpt-3.5-turbo 降低成本

### AI内容优化配置 (`ai_refinement`)
```yaml
ai_refinement:
  fallback_enabled: true  # 是否启用fallback模式
  llm:
    model: "gpt-4"        # 使用高质量模型
    temperature: 0.7      # 平衡创造性和一致性
    max_tokens: null
    timeout: 90           # AI生成可能需要更长时间
```

**说明**:
- `fallback_enabled`: LLM失败时使用简单的文本拼接作为备选方案
- `model`: 内容生成需要高质量，推荐 gpt-4
- `timeout`: 内容生成可能需要较长时间，设置更长的超时

### 通用配置
```yaml
log_level: "INFO"                    # 日志级别
enable_performance_tracking: true    # 是否启用性能追踪
```

**日志级别**: DEBUG, INFO, WARNING, ERROR, CRITICAL

## 环境变量配置

### 完整环境变量列表

| 环境变量 | 说明 | 示例 |
|---------|------|------|
| `OPENAI_API_KEY` | OpenAI API密钥 | `sk-xxx...` |
| `OPENAI_API_BASE` | API基础URL | `https://api.openai.com/v1` |
| `OPENAI_ORGANIZATION` | 组织ID | `org-xxx...` |
| `AGENT_CONFIG_PATH` | 自定义配置文件路径 | `/path/to/config.yaml` |
| `AGENT_LOG_LEVEL` | 日志级别 | `INFO` |
| `INTENT_PARSER_MODEL` | 意图解析模型 | `gpt-4` |
| `INTENT_PARSER_TEMPERATURE` | 意图解析温度 | `0.1` |
| `AI_REFINEMENT_MODEL` | AI优化模型 | `gpt-4` |
| `AI_REFINEMENT_TEMPERATURE` | AI优化温度 | `0.7` |

### 设置环境变量

**Linux/Mac**:
```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_API_BASE="https://api.openai.com/v1"
export AGENT_LOG_LEVEL="DEBUG"
```

**Windows (PowerShell)**:
```powershell
$env:OPENAI_API_KEY = "your-api-key"
$env:OPENAI_API_BASE = "https://api.openai.com/v1"
$env:AGENT_LOG_LEVEL = "DEBUG"
```

**Windows (CMD)**:
```cmd
set OPENAI_API_KEY=your-api-key
set OPENAI_API_BASE=https://api.openai.com/v1
set AGENT_LOG_LEVEL=DEBUG
```

### 使用 .env 文件

在项目根目录创建 `.env` 文件：
```bash
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=https://api.openai.com/v1
AGENT_LOG_LEVEL=INFO
```

然后在代码中加载（已集成到配置系统）。

## 快速开始

### 1. 使用环境变量（推荐）
```bash
# 设置API密钥
export OPENAI_API_KEY="your-api-key"

# 直接运行，将使用默认配置
python main.py
```

### 2. 使用配置文件
```bash
# 复制示例配置
cp config/agent_config.example.yaml config/agent_config.yaml

# 编辑配置文件
vim config/agent_config.yaml

# 运行
python main.py
```

### 3. 混合模式
```bash
# 在配置文件中设置模型参数
# 在环境变量中设置API密钥（更安全）
export OPENAI_API_KEY="your-api-key"

# 运行
python main.py
```

## 配置最佳实践

### 开发环境
- 使用配置文件设置模型参数
- 使用环境变量设置API密钥
- 启用 DEBUG 日志级别
- 使用 gpt-3.5-turbo 降低成本

```yaml
# config/agent_config.yaml (开发环境)
intent_parser:
  llm:
    model: "gpt-3.5-turbo"  # 使用便宜的模型
    temperature: 0.1

ai_refinement:
  llm:
    model: "gpt-3.5-turbo"  # 使用便宜的模型

log_level: "DEBUG"
```

### 生产环境
- 使用环境变量设置所有敏感信息
- 使用高质量模型确保准确性
- 使用 INFO 或 WARNING 日志级别
- 启用性能追踪

```yaml
# config/agent_config.yaml (生产环境)
intent_parser:
  llm:
    model: "gpt-4"
    temperature: 0.1

ai_refinement:
  llm:
    model: "gpt-4"
    temperature: 0.7

log_level: "INFO"
enable_performance_tracking: true
```

### 成本优化
如果需要降低成本，可以考虑：

1. **ExplanationGenerator**: 使用模板模式(`use_llm: false`)
2. **IntentParser**: 使用 gpt-3.5-turbo（准确度略降）
3. **AIRefinement**: 根据需求选择模型

```yaml
explanation_generator:
  use_llm: false  # 使用模板模式，成本为0

intent_parser:
  llm:
    model: "gpt-3.5-turbo"  # 便宜但准确度略低

ai_refinement:
  llm:
    model: "gpt-4"  # 保持高质量
```

## 配置验证

可以通过以下代码验证配置是否正确加载：

```python
from app.core.agent_config import get_config

config = get_config()
print(f"Intent Parser Model: {config.intent_parser.llm.model}")
print(f"API Key Configured: {bool(config.api.api_key)}")
print(f"Log Level: {config.log_level}")
```

## 故障排查

### 问题1: API密钥未配置
**错误**: `OpenAI API密钥未配置`

**解决方案**:
1. 检查环境变量是否设置: `echo $OPENAI_API_KEY`
2. 检查配置文件是否包含api_key
3. 确保配置文件路径正确

### 问题2: 配置文件未找到
**警告**: `未找到配置文件,使用默认配置`

**解决方案**:
1. 确保配置文件在正确的位置: `config/agent_config.yaml`
2. 或设置环境变量: `export AGENT_CONFIG_PATH=/path/to/config.yaml`

### 问题3: 模型调用失败
**错误**: `LLM初始化失败`

**解决方案**:
1. 检查API密钥是否有效
2. 检查api_base是否正确（如果使用代理）
3. 检查网络连接
4. 查看详细日志: 设置 `AGENT_LOG_LEVEL=DEBUG`

## 配置更新

配置系统支持在运行时重新加载配置：

```python
from app.core.agent_config import config_manager

# 重新加载配置
config_manager.reload_config()
```

**注意**: 已创建的Agent实例不会自动更新，需要重新创建。

## 更多信息

- [Agent架构文档](../docs/ARCHITECTURE_REPORT_MODIFICATION.md)
- [API使用文档](../API_使用文档.md)
- [开发者指南](../docs/DEVELOPER_GUIDE_STRATEGIES.md)
