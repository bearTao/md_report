# 核心功能测试模块

系统核心功能的测试，包括执行上下文、任务调度和错误处理。

## 📦 测试文件说明

- **test_context.py** - 执行上下文测试
- **test_scheduler.py** - 任务调度器测试
- **test_error_formatting.py** - 错误格式化和处理测试

## 🎯 测试覆盖范围

### 执行上下文 (ExecutionContext)
- 上下文创建和初始化
- 变量存储和检索
- 上下文状态管理
- 上下文传递和继承
- 线程安全性

### 任务调度器 (Scheduler)
- 任务队列管理
- 异步任务调度
- 任务优先级处理
- 并发控制
- 任务超时处理
- 任务失败重试

### 错误处理
- 错误捕获和记录
- 错误信息格式化
- 用户友好的错误消息
- 错误堆栈追踪
- 错误分类和聚合

## 🚀 运行测试

```bash
# 运行所有核心功能测试
pytest tests/core/

# 运行特定测试文件
pytest tests/core/test_context.py

# 运行特定测试并显示详细输出
pytest tests/core/test_scheduler.py -v -s
```

## 📝 注意事项

### 执行上下文测试
- 注意上下文的生命周期管理
- 测试中避免上下文泄漏
- 验证上下文隔离性

### 调度器测试
- 异步测试需要使用 `@pytest.mark.asyncio`
- 测试可能涉及时间延迟
- 注意测试的并发安全性
- 清理测试后的任务队列

### 错误处理测试
- 验证各种异常场景
- 检查错误消息的准确性
- 确保敏感信息不会泄漏
- 测试错误恢复机制

## 🔍 测试示例

### 测试执行上下文
```python
@pytest.mark.asyncio
async def test_context_isolation():
    """测试上下文隔离"""
    context1 = ExecutionContext("task1", "template1", {}, {})
    context2 = ExecutionContext("task2", "template2", {}, {})
    
    context1.set_variable("var1", "value1")
    context2.set_variable("var1", "value2")
    
    assert context1.get_variable("var1") != context2.get_variable("var1")
```

### 测试任务调度
```python
@pytest.mark.asyncio
async def test_task_scheduling():
    """测试任务调度"""
    scheduler = TaskScheduler()
    task = await scheduler.schedule_task(
        task_type="report_generation",
        priority="high"
    )
    
    assert task.status == TaskStatus.PENDING
    await scheduler.process_tasks()
    assert task.status == TaskStatus.COMPLETED
```

### 测试错误格式化
```python
def test_error_formatting():
    """测试错误格式化"""
    error = ValueError("Invalid input")
    formatted = format_error(error, include_traceback=False)
    
    assert "ValueError" in formatted
    assert "Invalid input" in formatted
    assert "用户友好的错误描述" in formatted
```
