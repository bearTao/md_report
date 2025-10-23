# 报告生成失败和WebSocket无限重连修复总结

## 修复日期
2025-10-22

## 问题描述

### 问题1：报告生成任务挂起
**症状**：
- 所有变量执行成功
- 任务状态永久停留在 RUNNING
- 前端显示"报告生成失败"
- 后端日志没有报告渲染或保存记录

**根本原因**：
`execute_report_generation` 函数定义为 `async def`，但通过 FastAPI 的 `BackgroundTasks.add_task()` 调用。`BackgroundTasks` 不支持异步函数，导致：
- 所有 `await` 语句被忽略
- 变量执行器的 `await scheduler.execute_all()` 无法正确执行
- WebSocket 广播的 `await ws_manager.broadcast_*()` 无法发送
- 任务挂起，永不完成

### 问题2：WebSocket无限重连
**症状**：
- WebSocket 连接数持续增长（245+）
- 连接不断建立和断开
- 刷新页面后问题加剧

**根本原因**：
`useWebSocket` Hook 使用 `useCallback` 包装 `connect` 和 `disconnect` 函数，依赖项包含所有回调函数。这导致：
1. 每次回调函数引用改变时，`connect` 函数重新创建
2. `useEffect` 依赖 `connect`，触发重新执行
3. 重新执行导致断开旧连接，建立新连接
4. 新连接触发状态更新，导致组件重新渲染
5. 重新渲染又触发回调函数引用改变，形成无限循环

## 修复方案

### 修复1：后端 - 使用 asyncio.create_task()

**文件**：`backend/app/api/reports.py`

**修改内容**：

```python
# 修改前（第486-495行）
background_tasks.add_task(
    execute_report_generation,
    task_id=task_id,
    template_id=request.template_id,
    template_content=template.template_content,
    metadata=template.metadata_json,
    user_inputs=request.inputs,
    openai_api_key=openai_api_key,
    openai_api_base=openai_api_base
)

# 修改后
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

同时移除了 `generate_report` 函数中不再需要的 `background_tasks: BackgroundTasks` 参数。

**技术原理**：
- `asyncio.create_task()` 在当前事件循环中正确调度异步任务
- 所有 `await` 语句正常工作
- 变量执行、模板渲染、WebSocket 广播都能正确执行
- 任务完成后正确保存报告和更新状态

### 修复2：前端 - 重写 WebSocket Hook

**文件**：`frontend/src/hooks/useWebSocket.ts`

**主要改动**：

1. **移除 useCallback 包装**
   - 不再使用 `useCallback` 包装 `connect` 和 `disconnect`
   - 直接在 `useEffect` 内部定义连接逻辑

2. **简化依赖链**
   - 主 `useEffect` 只依赖 `[taskId, reconnect, reconnectInterval, maxReconnectAttempts]`
   - 使用 refs 存储回调函数，避免依赖它们

3. **改进清理逻辑**
   - 添加 `unmounted` 标志防止组件卸载后的状态更新
   - 正确清理定时器和连接
   - 防止内存泄漏

4. **稳定的导出函数**
   - 使用 refs 存储 `sendMessage` 和 `clearEvents`
   - 返回稳定的函数引用

**核心代码结构**：

```typescript
useEffect(() => {
  if (!taskId) return;

  let ws: WebSocket | null = null;
  let reconnectAttempts = 0;
  let reconnectTimeout: NodeJS.Timeout | undefined;
  let unmounted = false;

  const connect = () => {
    // 连接逻辑
  };

  connect();

  return () => {
    unmounted = true;
    // 清理逻辑
  };
}, [taskId, reconnect, reconnectInterval, maxReconnectAttempts]);
```

**技术原理**：
- 将所有逻辑封装在单个 `useEffect` 中
- 使用闭包变量而非 refs 管理连接状态
- 通过 `unmounted` 标志防止竞态条件
- 依赖项最小化，避免不必要的重新连接

## 测试验证

### 验证步骤

1. **重启后端服务**
   ```bash
   cd backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **启动前端服务**
   ```bash
   cd frontend
   npm run dev
   ```

3. **创建报告生成任务**
   - 访问 http://10.10.20.10:5173/templates
   - 选择模板并填写参数
   - 点击"生成报告"

4. **观察行为**
   - 查看后端日志，确认任务执行流程
   - 查看前端进度页面，确认实时更新
   - 查看浏览器控制台，确认 WebSocket 连接

### 验证检查点

#### 后端验证
- ✅ 所有变量执行成功
- ✅ 看到模板渲染日志
- ✅ 看到报告保存日志
- ✅ 看到 `broadcast_task_completed` 日志
- ✅ 任务状态从 PENDING → RUNNING → SUCCESS
- ✅ `Database session closed` 日志正常

#### 前端验证
- ✅ WebSocket 连接稳定在 1 个
- ✅ 实时收到变量执行进度
- ✅ 所有变量完成后收到 `task_completed` 事件
- ✅ 页面顶部显示"报告生成成功"
- ✅ 出现"查看报告"按钮
- ✅ 点击按钮可以预览报告

#### WebSocket 验证
- ✅ 连接建立后不会无故断开
- ✅ 刷新页面后只建立 1 个新连接
- ✅ 后端日志显示连接数稳定
- ✅ 浏览器控制台无重连日志风暴

## 预期结果

### 任务执行流程

```
1. 用户提交报告生成请求
2. 后端创建任务 (状态: PENDING)
3. asyncio.create_task() 启动异步任务
4. 任务状态更新为 RUNNING
5. 变量按依赖顺序执行
   - 每个变量开始: broadcast_variable_started
   - 每个变量完成: broadcast_variable_completed
6. 所有变量执行完成
7. 模板渲染生成 Markdown
8. 保存报告到数据库
9. 任务状态更新为 SUCCESS
10. broadcast_task_completed 通知前端
11. 前端显示成功并提供查看按钮
```

### WebSocket 连接行为

```
1. 进入进度页面
2. 建立 1 个 WebSocket 连接
3. 接收实时进度事件
4. 任务完成后连接保持（除非用户离开页面）
5. 刷新页面：
   - 旧连接断开
   - 新连接建立（仅 1 个）
   - 无重连循环
```

## 技术要点

### FastAPI 后台任务最佳实践

**BackgroundTasks vs asyncio.create_task**

| 特性 | BackgroundTasks | asyncio.create_task |
|-----|-----------------|---------------------|
| 支持同步函数 | ✅ | ❌ |
| 支持异步函数 | ❌ | ✅ |
| 等待响应返回后执行 | ✅ | ❌（立即执行） |
| 适用场景 | 简单后台任务 | 复杂异步流程 |

**使用建议**：
- 简单的同步任务（发邮件、记日志）：使用 `BackgroundTasks`
- 需要 await 的异步任务：使用 `asyncio.create_task()`
- 长时间运行的任务：考虑使用 Celery 等任务队列

### React Hook 依赖管理

**避免无限循环的原则**：

1. **最小化依赖项**
   - 只包含真正需要响应的值
   - 不包含每次渲染都变化的回调函数

2. **使用 refs 存储函数**
   - 对于不需要触发重新执行的回调
   - 通过 ref 存储最新版本

3. **useEffect 内部定义函数**
   - 避免 useCallback 的依赖链问题
   - 利用闭包访问最新的 props/state

4. **添加清理标志**
   - 使用 `unmounted` 防止组件卸载后的状态更新
   - 防止内存泄漏和警告

## 相关文件

### 已修改文件
- ✅ `backend/app/api/reports.py` - 修改异步任务调用方式
- ✅ `frontend/src/hooks/useWebSocket.ts` - 重写 WebSocket Hook

### 相关文件
- `backend/app/services/websocket_manager.py` - WebSocket 管理器
- `backend/app/services/scheduler.py` - 变量执行调度器
- `frontend/src/pages/generate/ReportProgress.tsx` - 进度页面

## 后续优化建议

### 可选改进

1. **添加任务超时机制**
   - 设置最大执行时间（如 5 分钟）
   - 超时自动取消任务

2. **改进错误处理**
   - 区分不同类型的错误
   - 提供更详细的错误信息

3. **添加任务队列**
   - 限制并发任务数量
   - 防止资源耗尽

4. **优化 WebSocket 重连**
   - 使用指数退避算法
   - 添加连接质量检测

5. **添加任务优先级**
   - 支持高优先级任务插队
   - 资源分配优化

## 问题排查指南

### 如果报告生成仍然失败

1. **检查后端日志**
   ```bash
   tail -f backend/logs/app.log
   ```
   查找：
   - 变量执行错误
   - 模板渲染错误
   - 数据库错误

2. **检查任务状态**
   ```sql
   SELECT * FROM generation_tasks ORDER BY created_at DESC LIMIT 5;
   SELECT * FROM generation_task_variables WHERE task_id = 'task_xxx';
   ```

3. **检查 asyncio 事件循环**
   - 确认使用 `uvicorn` 启动（不是 `gunicorn`）
   - `uvicorn` 自动管理事件循环

### 如果 WebSocket 仍然重连

1. **检查浏览器控制台**
   - 查看 WebSocket 连接日志
   - 确认没有多个进度页面标签

2. **检查网络配置**
   - 确认防火墙允许 WebSocket
   - 确认代理不中断长连接

3. **检查前端代码**
   - 确认没有手动调用 `connect()`
   - 确认 `taskId` 没有频繁变化

---

**修复完成** ✅

现在报告生成应该能正常完成，WebSocket 连接也应该稳定了！

