# 查询和通用对话功能 - 快速开始

## 🎯 功能概述

报告修改代理现在支持两种新的交互方式：

### 1️⃣ 查询操作 (QUERY)
查询报告的各种信息，无需修改报告。

**支持的查询**：
- 📄 显示报告内容
- 📋 列出所有变量
- ⚙️ 显示参数列表
- 📊 显示章节结构
- 📈 获取统计信息
- 📜 显示修改历史

### 2️⃣ 通用对话 (GENERAL_CONVERSATION)
与助手进行自然的日常交流。

**支持的对话**：
- 👋 问候
- 🙏 感谢
- ❓ 咨询问题
- 💡 请求建议
- 📝 反馈意见

---

## 🚀 快速示例

### 查询示例

```bash
# API 请求
POST /api/reports/modify
{
    "report_id": "report_123",
    "user_request": "输出当前报告内容"
}

# 系统会自动识别为查询操作，并返回完整的报告内容
```

### 对话示例

```bash
# API 请求
POST /api/reports/modify
{
    "report_id": "report_123",
    "user_request": "你好"
}

# 系统会友好地问候并介绍可用功能
```

### 混合操作示例

```bash
# 修改后查询
POST /api/reports/modify
{
    "report_id": "report_123",
    "user_request": "将时间范围改为一周，然后显示所有参数"
}

# 系统会先修改参数，然后显示更新后的参数列表
```

---

## 📝 用户请求示例

### 查询类请求

```
✅ "输出当前报告内容"
✅ "显示所有参数"
✅ "列出所有变量"
✅ "当前报告有多少字"
✅ "显示章节结构"
✅ "查看修改历史"
```

### 对话类请求

```
✅ "你好"
✅ "谢谢"
✅ "有什么建议吗"
✅ "这个报告怎么样"
✅ "我能做什么"
```

---

## 🧪 测试

### 运行单元测试

```bash
conda activate test_md
cd backend
pytest tests/agent/test_query_and_conversation.py -v
```

**测试结果**: ✅ 11/11 通过

### 运行演示脚本

```bash
conda activate test_md
cd backend
$env:PYTHONPATH="E:\Desktop\code\xuqiu\xuqiu\backend"
python examples/query_and_conversation_demo.py
```

---

## 📚 文档

### 详细文档
- **[完整使用指南](docs/QUERY_AND_CONVERSATION_GUIDE.md)** - 所有功能的详细说明
- **[更新日志](docs/CHANGELOG_QUERY_CONVERSATION.md)** - 技术实现和代码改动

### 代码位置
- 数据模型: `app/schemas/modification_schemas.py`
- 意图解析: `app/services/agent/intent_parser.py`
- 查询策略: `app/services/agent/strategies/query_strategy.py`
- 对话策略: `app/services/agent/strategies/general_conversation_strategy.py`
- 测试代码: `tests/agent/test_query_and_conversation.py`

---

## 🎨 技术亮点

### 1. 无缝集成
- ✅ 完全兼容现有的修改功能
- ✅ 可以混合使用修改和查询操作
- ✅ 统一的 API 接口

### 2. 智能识别
- ✅ LLM 自动识别用户意图
- ✅ 支持自然语言表达
- ✅ 多意图并行处理

### 3. 友好交互
- ✅ 上下文感知的对话响应
- ✅ 个性化的建议生成
- ✅ 清晰的结果展示

---

## 📊 支持的查询类型详解

### show_content
显示完整的报告内容和统计信息。

**示例**: "输出当前报告内容", "显示报告"

**返回**: Markdown 格式的完整报告 + 字符数/行数统计

---

### list_variables
列出所有变量的详细信息。

**示例**: "列出所有变量", "显示变量列表"

**返回**: 变量名、类型、来源、值、依赖关系

---

### show_parameters
只显示用户输入的参数。

**示例**: "显示所有参数", "当前参数是什么"

**返回**: 参数名称和当前值列表

---

### show_sections
显示报告的章节结构。

**示例**: "显示章节结构", "列出目录"

**返回**: 层级化的章节列表

---

### get_statistics
获取报告的统计数据。

**示例**: "当前报告有多少字", "报告统计信息"

**返回**: 字符数、词数、行数、章节数、变量统计、报告元信息

---

### show_history
显示修改历史记录。

**示例**: "显示修改历史", "查看历史记录"

**返回**: 每次修改的请求、操作数、版本号、时间戳

---

## 💬 支持的对话类型详解

### greeting (问候)
**触发词**: "你好", "早上好", "Hi", "Hello"

**响应**: 友好问候 + 当前状态 + 功能介绍

---

### thanks (感谢)
**触发词**: "谢谢", "多谢", "Thanks", "Thank you"

**响应**: 礼貌回复

---

### question (咨询问题)
**触发词**: 一般性问题

**响应**: 功能介绍 + 使用建议

---

### suggestion_request (请求建议)
**触发词**: "建议", "推荐", "怎么样", "如何"

**响应**: 基于当前报告状态的个性化建议

---

### feedback (反馈)
**触发词**: "很好", "不错", "有问题"

**响应**: 感谢反馈

---

## 🔧 开发者指南

### 添加新的查询类型

1. 在 `QueryStrategy` 中添加处理方法
2. 在 `_execute_query` 中注册新类型
3. 更新意图解析器的提示词
4. 添加测试用例

### 添加新的对话类型

1. 在 `GeneralConversationStrategy` 中添加处理方法
2. 在 `_classify_conversation_type` 中添加识别规则
3. 更新意图解析器的提示词
4. 添加测试用例

---

## ⚠️ 注意事项

1. **查询操作不修改报告** - 版本号保持不变
2. **对话操作不改变状态** - 纯信息交互
3. **响应格式** - 查询/对话操作的响应直接显示，无"修改完成"措辞
4. **混合操作** - 可以在一个请求中混合修改和查询
5. **错误处理** - 查询失败返回友好错误，不影响报告状态

---

## 📞 联系支持

如有问题或建议，请参考：
- 📖 [完整文档](docs/QUERY_AND_CONVERSATION_GUIDE.md)
- 🔍 [更新日志](docs/CHANGELOG_QUERY_CONVERSATION.md)
- 🧪 [测试代码](tests/agent/test_query_and_conversation.py)

---

**更新日期**: 2025-11-18  
**版本**: 1.0.0  
**状态**: ✅ 生产就绪
