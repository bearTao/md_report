# Agent配置快速开始

## 5分钟上手

### 方式一：使用环境变量（推荐）

最简单的方式，适合快速开始：

```bash
# 1. 设置API密钥
export OPENAI_API_KEY="your-api-key-here"

# 2. 直接运行（使用默认配置）
python main.py

# 3. 验证配置
python verify_agent_config.py
```

**完成！** Agent现在使用以下默认配置：
- Intent Parser: gpt-4, temperature=0.1
- Explanation Generator: 模板模式（不使用LLM）
- AI Refinement: gpt-4, temperature=0.7

---

### 方式二：使用配置文件

更灵活的方式，适合自定义配置：

```bash
# 1. 创建配置文件
cd backend
cp config/agent_config.example.yaml config/agent_config.yaml

# 2. 编辑配置文件
vim config/agent_config.yaml
# 或使用任何文本编辑器打开

# 3. 设置API密钥（推荐通过环境变量）
export OPENAI_API_KEY="your-api-key-here"

# 4. 运行
python main.py

# 5. 验证配置
python verify_agent_config.py
```

---

## 配置示例

### 示例1：开发环境（低成本）

```yaml
# config/agent_config.yaml
intent_parser:
  llm:
    model: "gpt-3.5-turbo"  # 使用便宜的模型
    temperature: 0.1

explanation_generator:
  use_llm: false  # 使用模板模式，免费

ai_refinement:
  llm:
    model: "gpt-3.5-turbo"  # 使用便宜的模型

log_level: "DEBUG"  # 详细日志
```

```bash
# 设置API密钥
export OPENAI_API_KEY="your-key"

# 运行
python main.py
```

---

### 示例2：生产环境（高质量）

```yaml
# config/agent_config.yaml
intent_parser:
  llm:
    model: "gpt-4"
    temperature: 0.1

explanation_generator:
  use_llm: false  # 仍使用模板模式保持成本

ai_refinement:
  llm:
    model: "gpt-4"
    temperature: 0.7

log_level: "INFO"
enable_performance_tracking: true
```

```bash
# 设置API密钥
export OPENAI_API_KEY="your-key"

# 运行
python main.py
```

---

### 示例3：使用代理

如果需要通过代理访问OpenAI API：

```yaml
# config/agent_config.yaml
api:
  api_base: "https://your-proxy.com/v1"

# 其他配置...
```

或使用环境变量：

```bash
export OPENAI_API_KEY="your-key"
export OPENAI_API_BASE="https://your-proxy.com/v1"

python main.py
```

---

## 验证配置

运行验证脚本检查配置是否正确：

```bash
python verify_agent_config.py
```

输出示例：
```
============================================================
Agent配置验证
============================================================

✓ 配置加载成功

【API配置】
  API Key: ✓ 已配置
  API Base: 默认
  Organization: 无

【意图解析器】
  启用状态: ✓ 已启用
  模型: gpt-4
  温度: 0.1
  超时: 60秒
  最大重试: 2次

【响应生成器】
  使用LLM: ✗ 否(模板模式)
  模型: gpt-3.5-turbo
  温度: 0.7
  最大token: 500

【AI内容优化】
  Fallback: ✓ 已启用
  模型: gpt-4
  温度: 0.7
  超时: 90秒

============================================================
✓ 配置验证通过！Agent可以正常使用。
============================================================
```

---

## 常见问题

### Q: API密钥应该放在哪里？

**A:** 推荐使用环境变量，不要直接写在配置文件中：

```bash
# 推荐 ✓
export OPENAI_API_KEY="your-key"

# 不推荐 ✗（除非配置文件不会提交到版本控制）
# config/agent_config.yaml
api:
  api_key: "your-key"  # 危险！
```

### Q: 如何降低成本？

**A:** 使用以下配置：

1. ExplanationGenerator使用模板模式（`use_llm: false`）
2. 使用gpt-3.5-turbo替代gpt-4
3. 限制max_tokens

```yaml
explanation_generator:
  use_llm: false  # 免费

intent_parser:
  llm:
    model: "gpt-3.5-turbo"  # 便宜20倍
    max_tokens: 500  # 限制输出
```

### Q: 配置文件在哪里？

**A:** 优先级顺序：

1. `AGENT_CONFIG_PATH`环境变量指定的路径
2. `backend/config/agent_config.yaml`
3. `backend/config/agent_config.yml`
4. `backend/agent_config.yaml`
5. 使用默认值

### Q: 如何在代码中使用？

**A:** 

```python
# 最简单 - 使用默认配置
from app.services.agent.intent_parser import IntentParser

parser = IntentParser()  # 自动从配置加载

# 覆盖特定参数
parser = IntentParser(temperature=0.2)  # 其他参数从配置加载

# 获取配置
from app.core.agent_config import get_config

config = get_config()
print(config.intent_parser.llm.model)
```

---

## 下一步

✓ 已完成配置？查看更多文档：

- **详细配置说明**: `config/README.md`
- **配置更新日志**: `AGENT_CONFIG_CHANGELOG.md`
- **API文档**: `API_使用文档.md`
- **Agent架构**: `docs/ARCHITECTURE_REPORT_MODIFICATION.md`

---

## 获取帮助

如果遇到问题：

1. 运行验证脚本: `python verify_agent_config.py`
2. 查看详细日志: `export AGENT_LOG_LEVEL=DEBUG`
3. 参考配置说明: `config/README.md`

---

**就这么简单！开始使用Agent吧 🚀**
