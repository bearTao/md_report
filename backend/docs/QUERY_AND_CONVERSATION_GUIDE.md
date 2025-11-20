# 查询和通用对话功能指南

本文档介绍报告修改代理的查询和通用对话功能。

## 概述

除了修改类操作（更新参数、优化内容、调整章节等），系统现在支持：

1. **查询操作（QUERY）**: 查询报告的各种信息
2. **通用对话（GENERAL_CONVERSATION）**: 问候、感谢、咨询等日常交流

## 查询操作

### 支持的查询类型

#### 1. 显示报告内容 (`show_content`)

查看完整的报告内容和统计信息。

**示例请求**：
- "输出当前报告内容"
- "显示报告"
- "让我看看报告"

**返回内容**：
- 完整的 Markdown 内容
- 字符数、行数统计

---

#### 2. 列出所有变量 (`list_variables`)

查看报告中所有变量的详细信息。

**示例请求**：
- "列出所有变量"
- "显示变量列表"
- "有哪些变量"

**返回内容**：
- 变量名称
- 变量类型（模板/运行时）
- 数据来源
- 当前值
- 依赖关系

---

#### 3. 显示参数列表 (`show_parameters`)

只显示用户输入的参数（过滤掉其他变量）。

**示例请求**：
- "显示所有参数"
- "当前参数是什么"
- "列出可修改的参数"

**返回内容**：
- 参数名称和当前值

---

#### 4. 显示章节结构 (`show_sections`)

查看报告的章节组织结构。

**示例请求**：
- "显示章节结构"
- "报告有哪些章节"
- "列出目录"

**返回内容**：
- 层级化的章节列表
- 每个章节的标题

---

#### 5. 获取统计信息 (`get_statistics`)

获取报告的详细统计数据。

**示例请求**：
- "报告统计信息"
- "当前报告有多少字"
- "显示数据统计"

**返回内容**：
- 字符数、词数、行数
- 章节数量
- 变量统计（总数、参数数、AI变量数）
- 报告元信息（ID、版本、模板等）

---

#### 6. 显示修改历史 (`show_history`)

查看报告的修改历史记录。

**示例请求**：
- "显示修改历史"
- "之前做了哪些修改"
- "查看历史记录"

**返回内容**：
- 每次修改的用户请求
- 操作数量
- 版本号
- 时间戳

---

## 通用对话

### 支持的对话类型

#### 1. 问候（Greeting）

**示例**：
- "你好"
- "早上好"
- "Hi"

**系统响应**：
- 友好的问候
- 当前编辑状态介绍
- 可用功能说明

---

#### 2. 感谢（Thanks）

**示例**：
- "谢谢"
- "多谢帮助"
- "Thanks"

**系统响应**：
- 礼貌的回复

---

#### 3. 咨询问题（Question）

**示例**：
- "我能做什么"
- "如何修改报告"
- "这个系统有什么功能"

**系统响应**：
- 功能介绍
- 使用建议

---

#### 4. 请求建议（Suggestion Request）

**示例**：
- "有什么建议吗"
- "我应该怎么做"
- "如何改进报告"

**系统响应**：
- 基于当前报告状态的个性化建议
- 可尝试的操作列表

---

#### 5. 反馈（Feedback）

**示例**：
- "这个很好"
- "有点问题"
- "报告不错"

**系统响应**：
- 感谢用户反馈
- 鼓励继续提供意见

---

## 使用示例

### 查询示例

```python
# 示例 1: 查询报告内容
user_request = "输出当前报告内容"

# 系统会识别为 QUERY 意图
intent = ModificationIntent(
    intent_type=IntentType.QUERY,
    query_type="show_content",
    confidence=0.95
)

# 返回完整的报告内容
```

```python
# 示例 2: 查询统计信息
user_request = "当前报告有多少字"

# 系统会识别为 QUERY 意图
intent = ModificationIntent(
    intent_type=IntentType.QUERY,
    query_type="get_statistics",
    confidence=0.9
)

# 返回统计信息
```

### 对话示例

```python
# 示例 1: 问候
user_request = "你好"

# 系统会识别为 GENERAL_CONVERSATION 意图
intent = ModificationIntent(
    intent_type=IntentType.GENERAL_CONVERSATION,
    conversation_context="你好",
    confidence=1.0
)

# 返回友好的问候和功能介绍
```

```python
# 示例 2: 请求建议
user_request = "有什么建议吗"

# 系统会识别为 GENERAL_CONVERSATION 意图
intent = ModificationIntent(
    intent_type=IntentType.GENERAL_CONVERSATION,
    conversation_context="有什么建议吗",
    confidence=0.9
)

# 返回基于当前报告状态的建议
```

---

## 混合使用

你可以在一个请求中同时包含修改和查询操作：

```python
# 示例: 修改后查询
user_request = "将时间范围改为一周，然后显示所有参数"

# 系统会识别为两个意图：
intents = [
    ModificationIntent(
        intent_type=IntentType.UPDATE_PARAMETER,
        target_variable="time_range",
        new_value="一周",
        confidence=0.9
    ),
    ModificationIntent(
        intent_type=IntentType.QUERY,
        query_type="show_parameters",
        confidence=0.85
    )
]

# 系统会先执行修改，然后显示更新后的参数列表
```

---

## API 接口

### 请求格式

```json
{
    "report_id": "report_123",
    "user_request": "输出当前报告内容",
    "session_id": "session_456"
}
```

### 响应格式（查询操作）

```json
{
    "success": true,
    "session_id": "session_456",
    "report_id": "report_123",
    "new_version": 1,
    "explanation": "# 当前报告内容\n\n...",
    "operations_summary": [
        "查询完成: show_content"
    ],
    "markdown_content": "# Test Report\n...",
    "metadata": {
        "total_duration_ms": 50,
        "total_cost_usd": 0.0,
        "operations_count": 1,
        "llm_calls_count": 1,
        "from_version": 1,
        "to_version": 1
    }
}
```

### 响应格式（对话操作）

```json
{
    "success": true,
    "session_id": "session_456",
    "report_id": "report_123",
    "new_version": 1,
    "explanation": "您好！我是报告修改助手...",
    "operations_summary": [],
    "markdown_content": "# Test Report\n...",
    "metadata": {
        "total_duration_ms": 30,
        "total_cost_usd": 0.0,
        "operations_count": 1,
        "llm_calls_count": 1,
        "from_version": 1,
        "to_version": 1
    }
}
```

---

## 技术实现

### 新增模型

#### IntentType 枚举
```python
class IntentType(str, Enum):
    # ... 其他类型
    QUERY = "query"
    GENERAL_CONVERSATION = "general_conversation"
```

#### QueryDetails 模型
```python
class QueryDetails(BaseModel):
    query_type: str
    query_result: Any
    result_format: str = "text"
```

#### GeneralConversationDetails 模型
```python
class GeneralConversationDetails(BaseModel):
    user_message: str
    system_response: str
    conversation_type: str = "general"
```

### 执行策略

- **QueryStrategy**: 处理查询操作
- **GeneralConversationStrategy**: 处理通用对话

这两个策略继承自 `ExecutionStrategy` 基类，实现 `execute` 方法。

---

## 注意事项

1. **查询操作不修改报告**：查询操作只读取信息，不会改变报告的版本号或内容。

2. **对话操作不改变状态**：通用对话也不会修改报告，只是提供友好的交互体验。

3. **响应格式**：
   - 查询和对话操作的响应会直接显示在 `explanation` 字段中
   - 不会有"已完成以下修改"等修改类的措辞

4. **混合操作**：
   - 可以在一个请求中混合修改和查询操作
   - 系统会按顺序执行所有操作

5. **错误处理**：
   - 查询失败会返回友好的错误消息
   - 不会影响报告的现有状态

---

## 测试

运行测试用例：

```bash
conda activate test_md
cd backend
pytest tests/agent/test_query_and_conversation.py -v
```

---

## 未来扩展

可以考虑添加更多查询类型：

- `search_content`: 在报告中搜索特定内容
- `compare_versions`: 比较不同版本的差异
- `export_data`: 导出数据到不同格式
- `validate_report`: 验证报告的完整性

以及更多对话类型：

- `help`: 获取帮助信息
- `tutorial`: 交互式教程
- `explain`: 解释某个概念或功能
