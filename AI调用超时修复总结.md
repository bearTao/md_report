# AI 调用超时问题修复总结

## 修复日期
2025-10-22

## 问题描述

### 现象

**前端**：
- AI 变量一直显示"执行中"状态
- 永不完成，报告无法生成

**后端**：
- 日志显示大部分变量执行成功
- 但 `priority_assessment` 变量在调用 AI 后一直没有响应
- 没有报告渲染和保存的日志

### 具体案例

**任务 ID**: `task_09ef476b97c2`

**日志分析**：
```
16:16:23 - [priority_assessment] Starting execution
16:16:23 - 🚀 调用AI模型生成内容...
16:16:23 - ⏳ 请等待AI响应（可能需要10-60秒）...

[之后没有任何日志！]

16:16:31 - [grid_problem_summary] Successfully executed ✅
16:16:33 - [executive_summary] Successfully executed ✅
16:16:40 - [optimization_recommendations] Successfully executed ✅
16:16:47 - [coverage_analysis] Successfully executed ✅

[但是 priority_assessment 永远没有完成或失败的日志]
[后续的模板渲染也没有执行]
```

---

## 问题根源

### 核心问题：AI 调用没有超时机制

**文件**: `backend/app/executors/ai.py` (修复前第135行)

```python
# 问题代码
raw_output = await llm.ainvoke(messages)
```

**问题分析**：
1. `llm.ainvoke(messages)` 是异步调用 LangChain LLM
2. **没有设置超时时间**
3. 如果 AI API 没有响应（网络问题、服务器问题等），会**永久等待**
4. 整个任务卡住，后续变量和报告渲染都无法执行

### 为什么会卡住？

可能的原因：
1. **API 服务器无响应**：硅基流动 API 可能临时故障
2. **网络问题**：连接超时但没有被检测到
3. **请求太大**：prompt 太长导致处理缓慢
4. **并发限制**：同时多个请求导致排队
5. **模型问题**：特定模型版本可能有 bug

### 影响范围

- ❌ 单个变量卡住导致整个任务卡住
- ❌ 前端永远等待，用户体验极差
- ❌ 后端资源（数据库连接、内存）无法释放
- ❌ 其他任务可能也受影响

---

## 修复方案

### 添加超时机制

**文件**: `backend/app/executors/ai.py` (第131-158行)

**修改前**：
```python
import time
start_time = time.time()

try:
    raw_output = await llm.ainvoke(messages)  # ← 无超时
    elapsed = time.time() - start_time
    
    logger.info(f"✅ AI响应完成，耗时: {elapsed:.2f}秒")
    logger.debug(f"响应对象类型: {type(raw_output)}")
    
except Exception as api_error:
    elapsed = time.time() - start_time
    logger.error(f"❌ AI API调用失败，耗时: {elapsed:.2f}秒")
    logger.error(f"错误类型: {type(api_error).__name__}")
    logger.error(f"错误详情: {str(api_error)}", exc_info=True)
    raise
```

**修改后**：
```python
import time
import asyncio
start_time = time.time()

try:
    # 设置超时时间：120秒（2分钟）
    raw_output = await asyncio.wait_for(
        llm.ainvoke(messages),
        timeout=120.0
    )
    elapsed = time.time() - start_time
    
    logger.info(f"✅ AI响应完成，耗时: {elapsed:.2f}秒")
    logger.debug(f"响应对象类型: {type(raw_output)}")
    
except asyncio.TimeoutError:
    elapsed = time.time() - start_time
    logger.error(f"❌ AI API调用超时（120秒），耗时: {elapsed:.2f}秒")
    raise AiGenerationError(
        self.variable_name,
        f"AI API call timed out after 120 seconds"
    )
except Exception as api_error:
    elapsed = time.time() - start_time
    logger.error(f"❌ AI API调用失败，耗时: {elapsed:.2f}秒")
    logger.error(f"错误类型: {type(api_error).__name__}")
    logger.error(f"错误详情: {str(api_error)}", exc_info=True)
    raise
```

### 关键改动

1. **导入 asyncio** (第132行)
   ```python
   import asyncio
   ```

2. **使用 asyncio.wait_for()** (第136-140行)
   ```python
   raw_output = await asyncio.wait_for(
       llm.ainvoke(messages),
       timeout=120.0  # 2分钟超时
   )
   ```

3. **捕获 TimeoutError** (第146-152行)
   ```python
   except asyncio.TimeoutError:
       elapsed = time.time() - start_time
       logger.error(f"❌ AI API调用超时（120秒），耗时: {elapsed:.2f}秒")
       raise AiGenerationError(
           self.variable_name,
           f"AI API call timed out after 120 seconds"
       )
   ```

---

## 技术细节

### asyncio.wait_for() 原理

```python
await asyncio.wait_for(coroutine, timeout)
```

**功能**：
- 等待协程完成，但最多等待 `timeout` 秒
- 如果超时，抛出 `asyncio.TimeoutError`
- 超时后会**取消**正在执行的协程

**优点**：
- ✅ 防止永久等待
- ✅ 自动取消超时任务
- ✅ 释放资源
- ✅ 提供明确的错误信息

### 超时时间的选择

**120 秒（2分钟）**

**考虑因素**：
1. **正常响应时间**：通常 5-30 秒
2. **最长响应时间**：某些复杂请求可能需要 60 秒
3. **安全边界**：120 秒足够宽松，避免误杀
4. **用户体验**：2 分钟是可接受的等待上限

**分级超时策略**：
```
0-30秒：正常（大部分请求）
30-60秒：较慢（复杂请求）
60-120秒：异常缓慢（可能有问题）
>120秒：超时（肯定有问题）
```

### 错误传播

```
AI API 超时
    ↓
asyncio.TimeoutError 抛出
    ↓
捕获并转换为 AiGenerationError
    ↓
Executor 返回失败
    ↓
Scheduler 记录变量失败
    ↓
WebSocket 广播 variable_failed
    ↓
前端显示变量失败
    ↓
用户看到明确错误信息
```

---

## 修复效果

### 修复前

**行为**：
- ✅ 调用 AI API
- ❌ 永久等待
- ❌ 无日志
- ❌ 任务卡住
- ❌ 前端永远等待
- ❌ 无错误提示

### 修复后

**成功场景**：
```
16:16:23 - 🚀 调用AI模型生成内容...
16:16:23 - ⏳ 请等待AI响应（可能需要10-60秒）...
16:16:33 - ✅ AI响应完成，耗时: 10.00秒
16:16:33 - ✅ JSON解析成功
16:16:33 - 🎉 AI变量 priority_assessment 执行成功
```

**超时场景**（新增）：
```
16:16:23 - 🚀 调用AI模型生成内容...
16:16:23 - ⏳ 请等待AI响应（可能需要10-60秒）...
[等待 120 秒]
16:18:23 - ❌ AI API调用超时（120秒），耗时: 120.00秒
16:18:23 - ❌ Variable 'priority_assessment' execution failed: AI generation failed: AI API call timed out after 120 seconds
```

**前端显示**：
- ✅ 变量标记为"失败"（不再一直"执行中"）
- ✅ 显示错误信息："AI API call timed out after 120 seconds"
- ✅ 其他变量继续执行
- ✅ 任务最终完成（部分变量失败）

---

## 相关修复历史

这是一系列修复的第三个：

### 修复 1：Jinja2 双重插值
**问题**: `context.interpolate_string()` 双重插值导致 JSON 被破坏  
**修复**: 改用 Jinja2 `template_renderer.render()`  
**结果**: ✅ 支持完整 Jinja2 语法

### 修复 2：LangChain 变量插值冲突
**问题**: `ChatPromptTemplate` 把 JSON 当作变量占位符  
**修复**: 直接使用 `SystemMessage` 和 `HumanMessage`  
**结果**: ✅ JSON 内容原样传递

### 修复 3：AI 调用超时（本次）
**问题**: `llm.ainvoke()` 没有超时机制  
**修复**: 使用 `asyncio.wait_for(timeout=120)`  
**结果**: ✅ 2分钟后自动超时并报错

---

## 验证步骤

### 1. 重启后端服务

后端服务已在 `--reload` 模式运行，应该自动重载。

如果需要手动重启：
```bash
cd /data/tao/code/xuqiu/backend
# 找到进程并重启
ps aux | grep uvicorn
```

### 2. 重新生成报告

使用之前失败的参数重新测试。

### 3. 观察日志

**正常场景**：
```
[priority_assessment] Starting execution
🚀 调用AI模型生成内容...
✅ AI响应完成，耗时: XX.XX秒
✅ JSON解析成功
🎉 AI变量 priority_assessment 执行成功
```

**超时场景**：
```
[priority_assessment] Starting execution
🚀 调用AI模型生成内容...
[等待 120 秒]
❌ AI API调用超时（120秒）
❌ Variable 'priority_assessment' execution failed
```

### 4. 检查前端

**正常**：
- ✅ 所有变量都完成（成功或失败）
- ✅ 报告生成完成

**超时**：
- ✅ 超时变量显示"失败"
- ✅ 显示错误信息
- ✅ 其他变量正常执行
- ✅ 任务最终完成（可能部分失败）

---

## 相关文件

### 已修改
- ✅ `backend/app/executors/ai.py` (第131-158行)
  - 添加 `import asyncio`
  - 使用 `asyncio.wait_for(timeout=120)`
  - 添加 `asyncio.TimeoutError` 处理

### 未修改（但相关）
- ⏺️ `backend/app/executors/vision_ai.py`
  - Vision AI 也需要类似修复（未来）
- ⏺️ `backend/app/executors/api.py`
  - API 调用也应该有超时（已有 timeout 配置）

---

## 后续优化建议

### 1. 可配置超时时间

允许用户在 `ai_config` 中配置超时：

```yaml
ai_config:
  model: THUDM/GLM-Z1-9B-0414
  timeout: 60  # 自定义超时（秒）
  max_tokens: 2000
```

实现：
```python
timeout = config.timeout or 120  # 默认 120 秒
raw_output = await asyncio.wait_for(
    llm.ainvoke(messages),
    timeout=float(timeout)
)
```

### 2. 重试机制

超时后自动重试：

```python
max_retries = 2
for attempt in range(max_retries + 1):
    try:
        raw_output = await asyncio.wait_for(
            llm.ainvoke(messages),
            timeout=120.0
        )
        break
    except asyncio.TimeoutError:
        if attempt < max_retries:
            logger.warning(f"重试 {attempt + 1}/{max_retries}...")
            await asyncio.sleep(5)  # 等待 5 秒后重试
        else:
            raise
```

### 3. Vision AI 也添加超时

`backend/app/executors/vision_ai.py` 也有类似的 AI 调用：

```python
# 第109行
response = await llm.ainvoke(messages)

# 应该改为
response = await asyncio.wait_for(
    llm.ainvoke(messages),
    timeout=120.0
)
```

### 4. 监控和告警

记录超时事件，如果频繁超时则告警：

```python
# 记录到数据库
if isinstance(e, asyncio.TimeoutError):
    record_timeout_event(
        variable_name=self.variable_name,
        model=config.model,
        timestamp=datetime.utcnow()
    )
```

### 5. 降级策略

如果 AI 调用失败，使用默认值：

```yaml
ai_config:
  fallback_value: []  # 失败时的默认值
```

---

## 常见问题

### Q1: 为什么设置 120 秒？

**A**: 
- 正常 AI 响应：5-30 秒
- 复杂请求：最多 60 秒
- 120 秒提供 2 倍安全边界
- 超过 120 秒基本肯定有问题

### Q2: 超时后会重试吗？

**A**: 
- 当前**不会自动重试**
- 用户可以手动重新生成报告
- 未来可以添加自动重试机制

### Q3: 超时会影响 API 费用吗？

**A**: 
- 取决于 API 提供商
- 大部分按实际使用计费
- 超时取消的请求通常不计费或只计算部分

### Q4: 如果所有 AI 变量都超时怎么办？

**A**: 
- 所有 AI 变量标记为失败
- 报告生成继续（使用其他变量）
- 用户看到明确的错误信息
- 可以检查 API 服务状态

### Q5: 能否为不同模型设置不同超时？

**A**: 
- 当前所有模型统一 120 秒
- 未来可以在 `ai_config` 中配置
- 或根据模型类型自动调整

---

## 总结

### 修复成果

✅ **解决了永久卡住问题**：AI 调用最多等待 120 秒  
✅ **明确的错误信息**：超时后抛出 `AiGenerationError`  
✅ **前端正确显示**：变量标记为失败，不再一直等待  
✅ **资源正确释放**：超时后任务继续执行  
✅ **用户体验改善**：知道出了问题，可以采取行动  

### 关键改进

1. ✅ 添加 `asyncio.wait_for(timeout=120)`
2. ✅ 捕获 `asyncio.TimeoutError`
3. ✅ 记录详细的超时日志
4. ✅ 转换为 `AiGenerationError` 传播

### 防止的问题

- ❌ 任务永久卡住
- ❌ 前端永远等待
- ❌ 资源无法释放
- ❌ 无错误提示

---

**修复完成** ✅

现在 AI 调用有了超时保护，即使 API 无响应，任务也会在 2 分钟后自动失败并继续执行！

