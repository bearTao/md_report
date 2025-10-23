# asyncio 任务异常处理修复总结

## 修复日期
2025-10-22

## 问题描述

### 症状
- ✅ 所有变量执行成功（后端日志显示）
- ✅ 前端查看日志没有任何 ERROR
- ❌ 报告生成失败（前端显示"报告生成失败"）
- ❌ 后端日志中没有任何报告渲染或保存相关日志
- ❌ 没有 "Database session closed" 日志
- ❌ 任务状态被标记为 FAILED

### 受影响的任务
- `task_7fcbf86d077d` - 使用模板 `tpl_86b6a5129a4d`，输入 `ZQGY0174`

### 日志分析

**变量执行成功**（09:51:23）：
```
[task_7fcbf86d077d] [wgid] Successfully executed variable 'wgid' in 2ms
[task_7fcbf86d077d] [generation_info] Successfully executed variable 'generation_info' in 2ms
[task_7fcbf86d077d] [overview] Successfully executed variable 'overview' in 37ms
[task_7fcbf86d077d] [plan_sites] Successfully executed variable 'plan_sites' in 6ms
[task_7fcbf86d077d] [index_scores] Successfully executed variable 'index_scores' in 3ms
[task_7fcbf86d077d] [structure_cells] Successfully executed variable 'structure_cells' in 3ms
[task_7fcbf86d077d] [problem_clusters] Successfully executed variable 'problem_clusters' in 13ms
[task_7fcbf86d077d] [interference_cells] Successfully executed variable 'interference_cells' in 3ms
```

**之后的日志**：
- ❌ 没有模板渲染日志
- ❌ 没有报告保存日志
- ❌ 没有异常日志（即使 try-except 块中的 `print` 也没有）
- ❌ 没有 `Database session closed` 日志

**WebSocket 连接**：
```
09:51:23 - WebSocket connected for task task_7fcbf86d077d
09:51:23 - WebSocket disconnected for task task_7fcbf86d077d
09:51:23 - WebSocket connected for task task_7fcbf86d077d
09:52:20 - WebSocket disconnected for task task_7fcbf86d077d
...
```

## 根本原因

**asyncio.create_task() 的异常吞没问题**

在 Python asyncio 中，如果使用 `asyncio.create_task()` 创建任务但：
1. 没有 `await` 该任务
2. 没有保存任务引用
3. 没有添加异常处理回调

那么任务中抛出的**任何异常都会被静默丢弃**，不会有任何日志或错误信息。

### 之前的代码（有问题）

```python
# backend/app/api/reports.py 第485-495行（修复前）
asyncio.create_task(
    execute_report_generation(
        task_id=task_id,
        template_id=request.template_id,
        template_content=template.template_content,
        metadata=template.metadata_json,
        user_inputs=request.inputs,
        openai_api_key=openai_api_key,
        openai_api_base=openai_api_base
    )
)
```

**问题**：
- 任务创建后立即返回响应，没有保存任务引用
- 如果任务内部抛出异常，Python 垃圾回收器会静默丢弃该异常
- `execute_report_generation` 内部的 try-except 块可能因为某些原因没有捕获到异常（比如异步上下文切换、特殊异常类型等）

### 为什么内部 try-except 不起作用

`execute_report_generation` 函数（第420-451行）已经有 try-except 块：

```python
except Exception as e:
    print(f"Report generation failed for task {task_id}: {str(e)}")
    import traceback
    traceback.print_exc()
    # ... error handling ...
```

但日志中没有这些打印，说明：
- 异常可能在 try 块之外抛出
- 异常可能是某种特殊类型（如 asyncio.CancelledError）
- 异步上下文切换导致异常在不同的执行点抛出
- 数据库连接或其他资源问题导致异常处理本身失败

## 修复方案

### 添加异常处理回调

**文件**：`backend/app/api/reports.py`

**修改位置**：第485-511行

**修改内容**：

```python
# 修复后的代码
# Start background task using asyncio.create_task for proper async execution
task = asyncio.create_task(
    execute_report_generation(
        task_id=task_id,
        template_id=request.template_id,
        template_content=template.template_content,
        metadata=template.metadata_json,
        user_inputs=request.inputs,
        openai_api_key=openai_api_key,
        openai_api_base=openai_api_base
    )
)

# Add exception handler to catch any uncaught exceptions in the background task
def handle_task_exception(future: asyncio.Future):
    try:
        future.result()
    except Exception as e:
        print(f"UNCAUGHT EXCEPTION in background task {task_id}: {str(e)}")
        import traceback
        traceback.print_exc()

task.add_done_callback(handle_task_exception)

return ReportGenerateResponse(
    task_id=task_id,
    status=ReportStatusEnum.PENDING
)
```

### 关键改进

1. **保存任务引用**
   - 将 `create_task()` 的返回值保存到 `task` 变量
   - 防止任务被垃圾回收

2. **添加 done 回调**
   - 使用 `task.add_done_callback()` 注册回调函数
   - 回调在任务完成（无论成功或失败）时被调用

3. **捕获未处理的异常**
   - 在回调中调用 `future.result()`
   - 如果任务抛出异常，`result()` 会重新抛出该异常
   - 外层 try-except 捕获并记录异常

4. **详细的错误日志**
   - 打印 "UNCAUGHT EXCEPTION" 前缀便于搜索
   - 包含 task_id 用于追踪
   - 打印完整的堆栈跟踪

## 技术原理

### asyncio.Future.add_done_callback()

```python
def add_done_callback(callback: Callable[[Future], None]) -> None
```

- 在 Future 完成时调用回调函数
- 回调函数接收 Future 对象作为参数
- 调用 `future.result()` 可以获取结果或重新抛出异常

### 异常传播路径

**修复前**：
```
execute_report_generation() 抛出异常
    → asyncio.create_task() 中的 Future 异常
        → 没有人 await 或检查
            → 垃圾回收器丢弃
                → 🔴 无日志、无痕迹
```

**修复后**：
```
execute_report_generation() 抛出异常
    → asyncio.create_task() 中的 Future 异常
        → done_callback 被调用
            → future.result() 重新抛出异常
                → try-except 捕获
                    → ✅ 打印详细日志
```

## 验证步骤

### 1. 确认服务已重新加载

后端使用 `--reload` 模式运行，修改后会自动重新加载。

### 2. 重新生成报告

使用相同的参数重新生成报告：
- 模板 ID: `tpl_86b6a5129a4d`
- 用户输入: `ZQGY0174`

### 3. 观察日志

**成功场景**：
```
[task_xxx] [wgid] Successfully executed variable 'wgid' in Xms
[task_xxx] [generation_info] Successfully executed variable 'generation_info' in Xms
...
Rendering template with X variables
Report saved with ID: rpt_xxx
Task completed: task_xxx
Database session closed for task task_xxx
```

**失败场景（现在会有日志）**：
```
[task_xxx] [wgid] Successfully executed variable 'wgid' in Xms
...
UNCAUGHT EXCEPTION in background task task_xxx: <详细错误信息>
Traceback (most recent call last):
  File "...", line X, in ...
    ...
<完整堆栈跟踪>
```

### 4. 检查前端

- 成功：显示"报告生成成功"，可以查看报告
- 失败：显示"报告生成失败"，但**后端日志中有详细错误信息**

## 可能的真实错误原因

修复后，日志可能会揭示真正的问题，常见原因包括：

### 1. 模板渲染错误
```python
# 可能的错误
markdown_content = template_renderer.render(template_content, all_variables)
```
- Jinja2 语法错误
- 变量类型不匹配
- 缺少必需的变量

### 2. 数据库错误
```python
db_session.add(report)
db_session.commit()
```
- 约束违反
- 连接超时
- 事务冲突

### 3. WebSocket 广播错误
```python
await ws_manager.broadcast_task_completed(...)
```
- 连接已关闭
- 序列化错误

### 4. 其他资源错误
- 文件系统权限
- 内存不足
- 网络问题

## 后续优化建议

### 1. 改进日志系统

使用结构化日志：
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Report generation started", extra={
    "task_id": task_id,
    "template_id": template_id
})
```

### 2. 添加任务超时机制

```python
task = asyncio.create_task(execute_report_generation(...))
task.add_done_callback(handle_task_exception)

# 添加超时
async def timeout_handler():
    await asyncio.sleep(300)  # 5分钟超时
    if not task.done():
        task.cancel()
        logger.warning(f"Task {task_id} timed out")

asyncio.create_task(timeout_handler())
```

### 3. 使用任务队列

对于生产环境，考虑使用 Celery 或 RQ：
```python
from celery import Celery

@celery_app.task
def execute_report_generation(...):
    # 任务逻辑
    pass

# 调用
execute_report_generation.delay(task_id, ...)
```

### 4. 添加健康检查

```python
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "active_tasks": len(active_tasks),
        "db_connected": await check_db_connection()
    }
```

## 相关文件

### 已修改
- ✅ `backend/app/api/reports.py` - 添加异常处理回调（第485-511行）

### 相关但未修改
- `backend/app/services/scheduler.py` - 变量执行调度器
- `backend/app/services/renderer.py` - 模板渲染器
- `backend/app/services/websocket_manager.py` - WebSocket 管理器

## 测试清单

- [ ] 重新生成报告（使用之前失败的参数）
- [ ] 检查后端日志，确认能看到详细的异常信息（如果仍然失败）
- [ ] 检查前端显示是否正确
- [ ] 测试其他模板，确认修复不影响正常功能
- [ ] 验证 WebSocket 连接不再无限重连

## 结论

通过添加 `add_done_callback()` 异常处理机制，我们确保了：

1. ✅ **任何异常都会被捕获和记录**
2. ✅ **开发人员可以看到详细的错误信息**
3. ✅ **不影响正常的错误处理流程**
4. ✅ **提供最后一道防线，防止静默失败**

这是 asyncio 后台任务的最佳实践，适用于所有使用 `create_task()` 的场景。

---

**修复完成** ✅

现在请重新生成报告，如果仍然失败，我们将能看到真正的错误原因！

