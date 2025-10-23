# Jinja2 测试函数和渲染错误显示修复总结

## 修复日期
2025-10-22

## 修复内容

本次修复解决了两个关键问题：
1. **Jinja2 3.x 缺少 search/match 测试函数**
2. **模板渲染错误在前端不可见**

---

## 问题 1: search 测试函数不存在

### 问题描述

**错误信息**：
```
Template rendering failed: No test named 'search'.
jinja2.exceptions.TemplateRuntimeError: No test named 'search'.
```

**根本原因**：
- Jinja2 3.x 移除了 `search` 和 `match` 测试函数
- 模板使用了 `selectattr('site_type', 'search', '室分|室内')`
- `jinja2.tests.TESTS` 字典中不包含这些函数
- 需要手动实现

### 修复方案

#### 文件: `backend/app/services/renderer.py`

**添加自定义测试函数**：

```python
def __init__(self):
    # Use SandboxedEnvironment for security
    self.env = SandboxedEnvironment(
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    # Register all Jinja2 built-in tests
    self.env.tests.update(jinja2_tests.TESTS)
    
    # Add custom tests for regex matching (removed in Jinja2 3.x)
    self.env.tests['search'] = self._test_search
    self.env.tests['match'] = self._test_match
    
    # Register custom filters
    self.env.filters['json'] = self._json_filter

def _test_search(self, value, pattern, ignorecase=False):
    """Test if value contains pattern (regex search)"""
    import re
    flags = re.IGNORECASE if ignorecase else 0
    return bool(re.search(pattern, str(value), flags))

def _test_match(self, value, pattern, ignorecase=False):
    """Test if value matches pattern from start (regex match)"""
    import re
    flags = re.IGNORECASE if ignorecase else 0
    return bool(re.match(pattern, str(value), flags))
```

**使用示例**：
```jinja2
{# 筛选包含"室分"或"室内"的站点 #}
{% for site in sites | selectattr('site_type', 'search', '室分|室内') %}
  - {{ site.name }}
{% endfor %}

{# 筛选以"高大"开头的类型 #}
{% for item in items | selectattr('type', 'match', '^高大') %}
  - {{ item.name }}
{% endfor %}
```

---

## 问题 2: 渲染错误在前端不可见

### 问题描述

当模板渲染失败时：
- ✅ 后端日志有错误信息
- ❌ 前端只显示"报告生成失败"
- ❌ 前端看不到具体的渲染错误原因
- ❌ 无法区分是变量执行失败还是渲染失败

### 修复方案

#### 1. 数据库模型 - 添加 render_error 字段

**文件**: `backend/app/models/db_models.py`

```python
class GenerationTask(Base):
    """Report generation task"""
    __tablename__ = "generation_tasks"
    
    id = Column(String(50), primary_key=True)
    template_id = Column(String(50), nullable=False)
    status = Column(SQLEnum(ReportStatus), nullable=False, default=ReportStatus.PENDING)
    inputs_json = Column(JSON, nullable=False)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    render_error = Column(JSON, nullable=True)  # 新增：模板渲染错误信息
```

#### 2. 数据库迁移

**执行的 SQL**：
```sql
ALTER TABLE generation_tasks ADD COLUMN render_error JSON NULL;
```

**验证**：
```bash
✅ 数据库迁移成功：添加了 render_error 列
```

#### 3. 后端错误处理 - 捕获渲染错误

**文件**: `backend/app/api/reports.py`

在 `execute_report_generation` 函数中添加渲染错误处理：

```python
# 第374-405行
try:
    all_variables = context.get_all_variables()
    markdown_content = template_renderer.render(template_content, all_variables)
except TemplateRenderError as e:
    # 渲染错误 - 保存到任务记录并广播
    print(f"Template rendering failed for task {task_id}: {str(e)}")
    
    # 保存渲染错误到数据库
    task = db_session.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    if task:
        task.render_error = {
            "error_type": "TemplateRenderError",
            "error_message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
        task.status = ReportStatus.FAILED
        task.finished_at = datetime.utcnow()
        db_session.commit()
    
    # 广播渲染错误事件
    await ws_manager.broadcast_render_failed(
        task_id=task_id,
        error={
            "code": "TEMPLATE_RENDER_ERROR",
            "message": str(e),
            "details": "模板渲染失败，请检查模板语法"
        }
    )
    
    db_session.close()
    return  # 提前返回
```

#### 4. WebSocket 广播 - 添加渲染失败事件

**文件**: `backend/app/services/websocket_manager.py`

**添加事件类型**：
```python
class WSEventType(str, Enum):
    """WebSocket event types"""
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    RENDER_FAILED = "render_failed"  # 新增
    VARIABLE_STARTED = "variable_started"
    VARIABLE_PROGRESS = "variable_progress"
    VARIABLE_COMPLETED = "variable_completed"
    VARIABLE_FAILED = "variable_failed"
    HEARTBEAT = "heartbeat"
```

**添加广播方法**：
```python
async def broadcast_render_failed(self, task_id: str, error: Dict[str, Any]):
    """Broadcast template render failure"""
    await self.send_event(task_id, WSEventType.RENDER_FAILED, {
        "error": error
    })
```

#### 5. 前端类型定义 - 更新 WebSocket 事件

**文件**: `frontend/src/hooks/useWebSocket.ts`

```typescript
export interface WSEvent {
  type: 'task_started' | 'task_completed' | 'task_failed' | 
        'render_failed' |  // 新增
        'variable_started' | 'variable_completed' | 'variable_failed' | 
        'variable_progress' | 'heartbeat';
  task_id: string;
  timestamp: string;
  error?: {
    code: string;
    message: string;
    details?: string;
  };
  [key: string]: any;
}
```

#### 6. 前端显示 - 处理渲染错误事件

**文件**: `frontend/src/pages/generate/ReportProgress.tsx`

**处理 WebSocket 事件**：
```typescript
const { isConnected, latestEvent } = useWebSocket(taskId || null, {
  onMessage: (event: WSEvent) => {
    console.log('WebSocket event:', event);
    
    // 处理任务完成事件
    if (event.type === 'task_completed' && event.report_id) {
      setReportId(event.report_id);
      refetch();
    }
    
    // 处理渲染失败事件 - 新增
    if (event.type === 'render_failed') {
      message.error('模板渲染失败');
      refetch();
    }
    
    // ... 其他事件处理
  },
});
```

**在日志中显示渲染错误**：
```typescript
{/* 渲染日志 */}
{taskStatus.render_error && (
  <Timeline.Item color="red" dot={<CloseCircleOutlined />}>
    <div>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space>
          <strong>模板渲染</strong>
          <Tag color="red">失败</Tag>
        </Space>
        <div style={{ marginTop: 8, color: '#ff4d4f' }}>
          错误: {taskStatus.render_error.error_message}
        </div>
        {taskStatus.render_error.timestamp && (
          <div style={{ color: '#999', fontSize: '12px' }}>
            时间: {dayjs(taskStatus.render_error.timestamp).format('YYYY-MM-DD HH:mm:ss')}
          </div>
        )}
      </Space>
    </div>
  </Timeline.Item>
)}

{/* 渲染成功提示 */}
{isCompleted && !taskStatus.render_error && taskStatus.variables.length > 0 && (
  <Timeline.Item color="green" dot={<CheckCircleOutlined />}>
    <div>
      <Space>
        <strong>模板渲染</strong>
        <Tag color="green">成功</Tag>
      </Space>
    </div>
  </Timeline.Item>
)}
```

---

## 修改的文件清单

### 后端

1. ✅ **backend/app/services/renderer.py**
   - 添加 `_test_search` 和 `_test_match` 方法
   - 注册自定义测试函数

2. ✅ **backend/app/models/db_models.py**
   - 在 `GenerationTask` 模型中添加 `render_error` 字段

3. ✅ **backend/app/api/reports.py**
   - 在渲染部分添加 try-except 捕获 `TemplateRenderError`
   - 保存错误到数据库
   - 广播渲染失败事件

4. ✅ **backend/app/services/websocket_manager.py**
   - 添加 `RENDER_FAILED` 事件类型
   - 添加 `broadcast_render_failed` 方法

### 前端

5. ✅ **frontend/src/hooks/useWebSocket.ts**
   - 更新 `WSEvent` 类型定义
   - 添加 `render_failed` 事件类型
   - 添加 `error` 字段定义

6. ✅ **frontend/src/pages/generate/ReportProgress.tsx**
   - 处理 `render_failed` WebSocket 事件
   - 在日志 Timeline 中显示渲染错误
   - 显示渲染成功提示

### 数据库

7. ✅ **数据库迁移**
   - 执行 `ALTER TABLE generation_tasks ADD COLUMN render_error JSON NULL`

---

## 验证步骤

### 1. 重新生成报告

使用之前失败的参数：
- 模板 ID: `tpl_86b6a5129a4d`
- 用户输入: `ZQGY0174`

### 2. 预期结果

#### 成功场景

**后端日志**：
```
[task_xxx] [wgid] Successfully executed variable 'wgid' in 2ms
[task_xxx] [generation_info] Successfully executed variable 'generation_info' in 2ms
...
Report saved with ID: rpt_xxx
Task completed: task_xxx
```

**前端显示**：
- ✅ 所有变量执行成功（绿色勾）
- ✅ "模板渲染 - 成功"（绿色）
- ✅ 顶部显示"报告生成成功"
- ✅ 出现"查看报告"按钮

#### 失败场景（如果仍有其他错误）

**后端日志**：
```
Template rendering failed for task task_xxx: Template rendering failed: <具体错误>
```

**前端显示**：
- ✅ 所有成功的变量显示绿色勾
- ✅ 失败的变量显示红色叉
- ✅ "模板渲染 - 失败"（红色）
- ✅ 显示具体的错误信息
- ✅ 顶部显示"报告生成失败"

---

## 技术亮点

### 1. 自定义 Jinja2 测试函数

通过实现 `_test_search` 和 `_test_match`，恢复了 Jinja2 2.x 的功能：

```python
def _test_search(self, value, pattern, ignorecase=False):
    """Test if value contains pattern (regex search)"""
    import re
    flags = re.IGNORECASE if ignorecase else 0
    return bool(re.search(pattern, str(value), flags))
```

**优点**：
- ✅ 兼容旧版 Jinja2 模板
- ✅ 支持正则表达式匹配
- ✅ 支持大小写不敏感选项
- ✅ 保持沙箱安全性

### 2. 错误信息传播链

```
模板渲染异常
  ↓ 捕获 TemplateRenderError
  ↓ 保存到数据库 (render_error 字段)
  ↓ WebSocket 广播 (render_failed 事件)
  ↓ 前端接收并显示
  ↓ 用户看到详细错误
```

**优点**：
- ✅ 完整的错误追踪
- ✅ 实时错误通知
- ✅ 错误持久化存储
- ✅ 前端友好展示

### 3. 日志分层显示

前端日志现在分为两个层次：

1. **变量执行日志**
   - 每个变量的执行状态
   - 执行时间
   - 错误信息（如果有）

2. **模板渲染日志**
   - 渲染成功/失败状态
   - 渲染错误详情（如果有）
   - 错误时间戳

---

## 常见问题

### Q1: search 测试和 match 测试有什么区别？

**A**: 
- `search`: 在字符串中查找匹配（任意位置）
- `match`: 从字符串开头匹配

```jinja2
{# search - 在任意位置查找 #}
{% if '室分站点' is search('室分') %}  {# True #}

{# match - 从开头匹配 #}
{% if '室分站点' is match('室分') %}  {# True #}
{% if '室分站点' is match('站点') %}  {# False #}
```

### Q2: 为什么要单独处理渲染错误？

**A**: 
- 变量执行错误：数据问题（SQL、API、AI 等）
- 渲染错误：模板语法问题（Jinja2 语法、逻辑错误等）

分开处理可以：
- ✅ 快速定位问题类型
- ✅ 提供更精确的错误信息
- ✅ 区分责任（数据 vs 模板）

### Q3: render_error 字段的数据结构是什么？

**A**:
```json
{
  "error_type": "TemplateRenderError",
  "error_message": "Template rendering failed: No test named 'search'.",
  "timestamp": "2025-10-22T10:15:30.123456"
}
```

### Q4: 为什么在前端同时显示渲染成功？

**A**: 
- 让用户清楚看到完整的执行流程
- 确认模板渲染这一步已完成
- 与变量执行日志形成完整的时间线

---

## 后续优化建议

### 1. 添加更多自定义测试函数

```python
# 大小写不敏感的包含测试
def _test_contains(self, value, substring):
    return substring.lower() in str(value).lower()

# 数值范围测试
def _test_between(self, value, min_val, max_val):
    return min_val <= value <= max_val

# 注册
self.env.tests['contains'] = self._test_contains
self.env.tests['between'] = self._test_between
```

### 2. 渲染错误详情扩展

```python
task.render_error = {
    "error_type": "TemplateRenderError",
    "error_message": str(e),
    "error_line": get_error_line(e),  # 错误行号
    "error_context": get_error_context(e),  # 错误上下文
    "timestamp": datetime.utcnow().isoformat()
}
```

### 3. 前端错误定位

在前端显示错误行号，甚至高亮错误位置：

```typescript
{taskStatus.render_error && (
  <Alert
    type="error"
    message="模板渲染失败"
    description={
      <div>
        <p>错误: {taskStatus.render_error.error_message}</p>
        {taskStatus.render_error.error_line && (
          <p>位置: 第 {taskStatus.render_error.error_line} 行</p>
        )}
      </div>
    }
  />
)}
```

---

## 总结

本次修复解决了两个关键问题：

1. **Jinja2 3.x 兼容性**
   - ✅ 实现了 `search` 和 `match` 测试函数
   - ✅ 保持向后兼容性
   - ✅ 支持正则表达式匹配

2. **前端错误可见性**
   - ✅ 渲染错误保存到数据库
   - ✅ 通过 WebSocket 实时广播
   - ✅ 前端清晰显示错误详情
   - ✅ 完整的日志时间线

**修复完成** ✅

现在用户可以：
- 使用包含 `search`/`match` 的模板
- 在前端清楚看到渲染错误
- 区分变量执行错误和模板渲染错误
- 快速定位和解决问题

