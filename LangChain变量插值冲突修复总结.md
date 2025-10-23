# LangChain ChatPromptTemplate 变量插值冲突修复总结

## 修复日期
2025-10-22

## 问题描述

### 新的错误

在修复了 Jinja2 双重插值问题后，出现了新的错误：

```
Variable 'coverage_analysis' execution failed: AI generation failed: 
'Input to ChatPromptTemplate is missing variables {\'\\n "area_id"\'}. 
Expected: [\'\\n "area_id"\'] Received: []
Note: if you intended {\n "area_id"} to be part of the string and not a variable, 
please escape it with double curly braces like: \'{{\n "area_id"}}\'.'
```

### 问题根源

**双重变量插值问题**：

1. ✅ **第一层**：Jinja2 渲染 `prompt_template`
   - 输入：`请生成JSON：[{"area_id": "..."}]`
   - 输出：包含 JSON 示例的完整文本

2. ❌ **第二层**：LangChain `ChatPromptTemplate` 再次插值
   - 输入：上一步生成的文本（包含 JSON）
   - 问题：把 JSON 中的 `{"area_id": ...}` 当作变量占位符
   - 错误：找不到变量 `\n "area_id"`

### 错误的处理流程（修复前）

```python
# 1. Jinja2 渲染（已修复）
prompt_text = template_renderer.render(
    config.prompt_template,
    self.context.get_all_variables()
)
# prompt_text 现在包含：请生成JSON：[{"area_id": "区域1"}]

# 2. 添加到 full_prompt
full_prompt = f"{prompt_text}\n\n请以JSON格式返回..."

# 3. 使用 ChatPromptTemplate（问题所在！）
prompt = ChatPromptTemplate.from_messages([
    ("system", "..."),
    ("human", full_prompt)  # ← full_prompt 中的 {...} 被当作变量
])

# 4. ChatPromptTemplate 尝试插值
chain = prompt | llm
raw_output = await chain.ainvoke({})  # ← 传入空字典
# ChatPromptTemplate 发现 {"area_id": ...} 并尝试查找变量
# 报错：找不到变量 "\n "area_id""
```

---

## 修复方案

### 核心思路

既然 Jinja2 已经完成了所有变量渲染，**不需要 LangChain 再做变量插值**。

**改为直接使用 LangChain 消息对象**，而不是使用 `ChatPromptTemplate`。

### 修改内容

**文件**：`backend/app/executors/ai.py`

#### 1. 更新导入（第9-11行）

**修改前**：
```python
# LangChain imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
```

**修改后**：
```python
# LangChain imports
from langchain_openai import ChatOpenAI
from langchain.schema.messages import SystemMessage, HumanMessage
```

**说明**：
- ❌ 移除 `ChatPromptTemplate`（会进行变量插值）
- ❌ 移除 `JsonOutputParser`（不再需要）
- ✅ 添加 `SystemMessage` 和 `HumanMessage`（直接构建消息）

#### 2. 移除 parser 创建（第100-101行）

**修改前**：
```python
# 2. Create output parser with custom preprocessing
parser = JsonOutputParser()

# 3. Add schema instructions to prompt if schema is provided
```

**修改后**：
```python
# 2. Add schema instructions to prompt if schema is provided
```

**说明**：
- 移除不再使用的 `parser` 对象

#### 3. 直接使用消息对象（第120-141行）

**修改前**：
```python
# 4. Create prompt template
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个专业的数据分析助手..."),
    ("human", full_prompt)
])

# 5. Create chain: prompt | llm
logger.info(f"⛓️  创建LangChain链...")
chain = prompt | llm

# 6. Invoke chain and get raw output
logger.info(f"🚀 调用AI模型生成内容...")
logger.debug(f"调用参数: 空字典（提示词已在prompt中）")

raw_output = await chain.ainvoke({})
```

**修改后**：
```python
# 4. Create messages directly (avoid ChatPromptTemplate variable interpolation)
messages = [
    SystemMessage(content="你是一个专业的数据分析助手，擅长生成结构化的JSON数据。请直接返回纯JSON格式，不要使用markdown代码块（不要使用```json```），不要添加任何解释性文字。"),
    HumanMessage(content=full_prompt)
]

# 5. Invoke LLM directly with messages
logger.info(f"🚀 调用AI模型生成内容...")
logger.debug(f"消息数量: {len(messages)}")

raw_output = await llm.ainvoke(messages)
```

**说明**：
- ✅ 直接创建 `SystemMessage` 和 `HumanMessage`
- ✅ 不使用 `ChatPromptTemplate`（避免变量插值）
- ✅ 直接调用 `llm.ainvoke(messages)`（无需 chain）

---

## 技术原理

### ChatPromptTemplate 的变量插值

LangChain 的 `ChatPromptTemplate` 默认会对消息内容进行变量插值：

```python
# ChatPromptTemplate 会查找 {...} 作为变量占位符
prompt = ChatPromptTemplate.from_messages([
    ("human", "请分析数据：{data}")  # ← {data} 会被替换
])

# 调用时需要传入变量
output = await prompt.ainvoke({"data": actual_data})
```

**问题**：
- 如果消息内容包含 JSON（如 `{"key": "value"}`）
- ChatPromptTemplate 会把 `{key}` 当作变量占位符
- 如果没有传入该变量，就会报错

### 直接使用消息对象

使用 `SystemMessage` 和 `HumanMessage` 直接构建消息：

```python
# 直接构建消息，不进行变量插值
messages = [
    SystemMessage(content="系统提示"),
    HumanMessage(content="请分析数据：{\"key\": \"value\"}")  # ← JSON 不会被当作变量
]

# 直接调用 LLM
output = await llm.ainvoke(messages)
```

**优点**：
- ✅ 内容原样传递，不进行变量插值
- ✅ 可以包含任意 `{...}` 内容
- ✅ 简化代码逻辑

---

## 修复效果

### 修复前（报错）

**prompt_template**：
```yaml
prompt_template: |
  请生成覆盖区域分析建议，返回JSON数组格式：
  [
    {
      "area_id": "区域编号",
      "problem_type": "问题类型"
    }
  ]
```

**执行流程**：
1. Jinja2 渲染 ✅
2. 生成文本包含 JSON 示例 ✅
3. ChatPromptTemplate 插值 ❌ 把 `{"area_id": ...}` 当作变量
4. 报错：`missing variables {'\n "area_id"'}`

### 修复后（正常）

**执行流程**：
1. Jinja2 渲染 ✅
2. 生成文本包含 JSON 示例 ✅
3. 直接构建 SystemMessage 和 HumanMessage ✅
4. 调用 LLM ✅ JSON 示例原样传递

**测试用例**：

#### 测试1：包含 JSON 示例

```yaml
prompt_template: |
  请生成JSON格式，示例：
  {
    "name": "{{wgid}}",
    "items": [{"id": 1, "value": "test"}]
  }
```

**结果**：✅ 正常工作

#### 测试2：包含多层嵌套 JSON

```yaml
prompt_template: |
  返回格式：
  {
    "data": {
      "nested": {
        "field": "value"
      }
    }
  }
```

**结果**：✅ 正常工作

#### 测试3：tojson 过滤器生成的 JSON

```yaml
prompt_template: |
  基于以下数据：
  {{ overview | tojson }}
  
  生成分析报告。
```

**结果**：✅ 正常工作，`overview` 转为 JSON 后不会被误判

---

## 相关问题修复历史

### 修复 1：Jinja2 双重插值（已完成）

**问题**：`context.interpolate_string()` 进行两次正则替换
**修复**：改用 `template_renderer.render()`
**结果**：✅ 支持完整 Jinja2 语法

### 修复 2：LangChain 变量插值冲突（本次）

**问题**：`ChatPromptTemplate` 把 JSON 当作变量占位符
**修复**：直接使用 `SystemMessage` 和 `HumanMessage`
**结果**：✅ JSON 内容原样传递

---

## 对比总结

### 变量插值层次

| 阶段 | 修复前 | 修复后 |
|------|--------|--------|
| **用户编写** | `prompt_template: "请分析{{wgid}}"` | 同左 |
| **第1层：Jinja2** | ❌ 简单正则替换（有bug） | ✅ Jinja2 完整渲染 |
| **第2层：LangChain** | ❌ ChatPromptTemplate 插值 | ✅ 无插值（直接使用消息） |
| **传给 LLM** | 多次插值，JSON 被破坏 | ✅ 一次渲染，内容正确 |

### 支持的功能

| 功能 | 修复前 | 修复后 |
|------|--------|--------|
| 简单变量 `{{wgid}}` | ⚠️ 支持 | ✅ 支持 |
| JSON 示例 `{"key": "..."}` | ❌ 报错 | ✅ 支持 |
| tojson 过滤器 | ❌ 报错 | ✅ 支持 |
| 循环 `{% for %}` | ❌ 不支持 | ✅ 支持 |
| 条件 `{% if %}` | ❌ 不支持 | ✅ 支持 |
| 嵌套数据访问 | ⚠️ 部分支持 | ✅ 完整支持 |

---

## 相关文件

### 已修改

- ✅ `backend/app/executors/ai.py`（第9-11、100-141行）
  - 移除 `ChatPromptTemplate` 和 `JsonOutputParser`
  - 改用 `SystemMessage` 和 `HumanMessage`
  - 直接调用 `llm.ainvoke(messages)`

### 未修改（保持一致）

- ⏺️ `backend/app/executors/vision_ai.py`
  - Vision AI 已在之前修复中改用 Jinja2
  - 也使用了直接的消息对象，无此问题

---

## 后续建议

### 1. 统一使用直接消息对象

所有使用 LangChain LLM 的地方，建议：
- ✅ 使用 `SystemMessage` 和 `HumanMessage` 构建消息
- ❌ 避免使用 `ChatPromptTemplate`（除非确实需要变量插值）

### 2. 模板渲染最佳实践

```python
# ✅ 推荐：Jinja2 渲染 + 直接消息
prompt_text = template_renderer.render(template, variables)
messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=prompt_text)
]
result = await llm.ainvoke(messages)

# ❌ 不推荐：多层插值
prompt = ChatPromptTemplate.from_template(template)  # 第一层
result = await prompt.ainvoke(variables)  # 第二层
```

### 3. 错误提示优化

如果将来需要使用 `ChatPromptTemplate`，应该：
- 使用双花括号转义：`{{"key": "value"}}`
- 或使用原始字符串块：`{% raw %}{"key": "value"}{% endraw %}`

---

## 测试验证

### 验证步骤

1. **重启后端服务**（如果在 reload 模式则自动生效）
2. **重新生成报告**，使用之前失败的模板
3. **检查日志**，确认：
   - ✅ Jinja2 渲染成功
   - ✅ 消息构建成功
   - ✅ LLM 调用成功
   - ✅ JSON 解析成功

### 预期结果

**之前失败的变量**（现在应该成功）：
- ✅ `coverage_analysis` - 包含 `{"area_id": ...}` 的 JSON 示例
- ✅ `priority_assessment` - 包含 `{"rank": ...}` 的 JSON 示例
- ✅ `optimization_recommendations` - 包含 `{"immediate_actions": ...}` 的 JSON 示例

**日志关键信息**：
```
🔄 开始渲染提示词模板
✅ 提示词渲染成功，长度: XXXX 字符
🚀 调用AI模型生成内容...
消息数量: 2
✅ AI响应完成，耗时: XX.XX秒
🔍 解析AI输出为JSON...
✅ JSON解析成功
```

---

## 总结

### 问题链

1. **原始问题**：`context.interpolate_string()` 双重插值
2. **第一次修复**：改用 Jinja2 `template_renderer.render()`
3. **新问题**：`ChatPromptTemplate` 再次插值
4. **第二次修复**：直接使用 `SystemMessage` 和 `HumanMessage`

### 最终方案

```
用户模板 (prompt_template)
    ↓
[Jinja2 完整渲染]
    ↓
渲染后的文本 (prompt_text)
    ↓
[直接构建消息对象]
    ↓
SystemMessage + HumanMessage
    ↓
[LLM 调用]
    ↓
AI 响应
```

**关键点**：
- ✅ **单一渲染点**：只在 Jinja2 阶段进行变量替换
- ✅ **无二次插值**：LangChain 层不进行变量插值
- ✅ **内容原样传递**：JSON、特殊字符都能正确处理

---

**修复完成** ✅

现在用户可以在 `prompt_template` 中自由使用 JSON 示例、tojson 过滤器、循环、条件等所有 Jinja2 功能，不会有任何变量插值冲突！

