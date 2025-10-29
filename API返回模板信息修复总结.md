# API返回模板信息修复总结

## 问题描述

用户报告虽然数据库中有子模板的变量执行记录和日志，但前端页面无法正确显示：

1. **`/generate/task_xxx` 页面**: 没有看到子模板的变量执行情况
2. **`/logs/task_xxx` 页面**: "所属模板"列都显示为主模板

## 问题根本原因

### 原因：后端API未返回 template_id 和 template_path 字段

虽然数据库中正确存储了这些字段，但后端API在查询和返回数据时遗漏了它们。

#### 问题1: `/api/reports/tasks/{task_id}/status` API

**文件**: `backend/app/api/reports.py` (第952-980行)

**问题SQL查询**:
```sql
SELECT variable_name, source, status, started_at, finished_at, 
       duration_ms, error_message, result_preview
FROM generation_task_variables
WHERE task_id = :task_id
```

❌ **缺少** `template_id` 和 `template_path` 字段

**问题代码**:
```python
variable_details = [
    TaskVariableDetail(
        variable_name=var[0],
        source=var[1],
        status=VariableStatusEnum(var[2]),
        started_at=var[3],
        finished_at=var[4],
        duration_ms=var[5],
        error_message=var[6],
        result_preview=var[7]
        # ❌ 缺少 template_id 和 template_path
    )
    for var in vars_result
]
```

#### 问题2: `/api/reports/tasks/{task_id}/logs` API

**文件**: `backend/app/api/reports.py` (第1423-1436行)

**问题代码**:
```python
log_items = [
    ExecutionLogItem(
        id=log.id,
        task_id=log.task_id,
        variable_name=log.variable_name,
        level=log.level.value,
        message=log.message,
        context=log.context_json,
        created_at=log.created_at
        # ❌ 缺少 template_id 和 template_path
    )
    for log in logs
]
```

## 解决方案

### 修复1: 任务状态API

**修改SQL查询**:
```sql
SELECT variable_name, source, status, started_at, finished_at, 
       duration_ms, error_message, result_preview, template_id, template_path
FROM generation_task_variables
WHERE task_id = :task_id
```

**修改返回数据构造**:
```python
variable_details = [
    TaskVariableDetail(
        variable_name=var[0],
        source=var[1],
        status=VariableStatusEnum(var[2]),
        started_at=var[3],
        finished_at=var[4],
        duration_ms=var[5],
        error_message=var[6],
        result_preview=var[7],
        template_id=var[8],      # ✅ 添加 template_id
        template_path=var[9]     # ✅ 添加 template_path
    )
    for var in vars_result
]
```

### 修复2: 日志API

**修改返回数据构造**:
```python
log_items = [
    ExecutionLogItem(
        id=log.id,
        task_id=log.task_id,
        variable_name=log.variable_name,
        level=log.level.value,
        message=log.message,
        context=log.context_json,
        created_at=log.created_at,
        template_id=log.template_id,      # ✅ 添加 template_id
        template_path=log.template_path   # ✅ 添加 template_path
    )
    for log in logs
]
```

## 验证结果

### 测试任务: task_11b76cd0d729

#### 1. 任务状态API (`/api/reports/tasks/{task_id}/status`)

**请求**:
```bash
GET http://localhost:8000/api/reports/tasks/task_11b76cd0d729/status
```

**返回结果**:
```json
{
  "variables": [
    {
      "variable_name": "title",
      "template_id": "tpl_8d46934e172c",
      "template_path": "模板嵌套测试"
    },
    {
      "variable_name": "content",
      "template_id": "tpl_8d46934e172c",
      "template_path": "模板嵌套测试"
    },
    {
      "variable_name": "title1",
      "template_id": "tpl_e710aea7c613",
      "template_path": "模板嵌套测试 > 子模版1"
    },
    {
      "variable_name": "content1",
      "template_id": "tpl_e710aea7c613",
      "template_path": "模板嵌套测试 > 子模版1"
    }
  ]
}
```

✅ **结果**: 所有变量都正确包含 `template_id` 和 `template_path`

#### 2. 日志API (`/api/reports/tasks/{task_id}/logs`)

**请求**:
```bash
GET http://localhost:8000/api/reports/tasks/task_11b76cd0d729/logs?limit=20
```

**返回结果示例**:
```
title           - template_id=tpl_8d46934e172c     path=模板嵌套测试
title           - template_id=tpl_8d46934e172c     path=模板嵌套测试
content         - template_id=tpl_8d46934e172c     path=模板嵌套测试
content         - template_id=tpl_8d46934e172c     path=模板嵌套测试
title1          - template_id=tpl_e710aea7c613     path=模板嵌套测试 > 子模版1
title1          - template_id=tpl_e710aea7c613     path=模板嵌套测试 > 子模版1
content1        - template_id=tpl_e710aea7c613     path=模板嵌套测试 > 子模版1
content1        - template_id=tpl_e710aea7c613     path=模板嵌套测试 > 子模版1
[渲染引擎]         - template_id=tpl_e710aea7c613     path=模板嵌套测试 > 子模版1
[渲染引擎]         - template_id=tpl_8d46934e172c     path=模板嵌套测试
```

✅ **结果**: 所有日志都正确包含 `template_id` 和 `template_path`

## 前端显示效果

### `/generate/task_xxx` 页面

现在前端会收到完整的变量信息，包括：
- ✅ 主模板变量（title, content）
- ✅ 子模板变量（title1, content1）
- ✅ 每个变量的 template_id 和 template_path

前端可以根据 `template_path` 进行分组显示。

### `/logs/task_xxx` 页面

"所属模板"列现在会正确显示：
- ✅ 主模板日志: "模板嵌套测试"
- ✅ 子模板日志: "模板嵌套测试 > 子模版1"
- ✅ 系统日志: 无模板信息（显示"主模板"或空）

## 修改的文件

### 后端文件
1. **`backend/app/api/reports.py`**
   - 第952-980行: 修改任务状态API的SQL查询和数据构造
   - 第1423-1436行: 修改日志API的数据构造

### 前端文件
无需修改（前端的类型定义已经包含了这些字段）

## 技术要点

### 1. SQL查询字段顺序
修改SQL查询时，必须按照正确的顺序添加字段，并在构造对象时使用正确的索引：
```python
# SQL: field1, field2, field3, field4, field5
# 访问: var[0], var[1], var[2], var[3], var[4]
```

### 2. ORM vs 原生SQL
- 任务状态API使用原生SQL查询（性能优化）
- 日志API使用SQLAlchemy ORM查询

对于原生SQL，需要手动添加字段到SELECT语句；
对于ORM查询，可以直接访问模型的属性（如 `log.template_id`）。

### 3. 可选字段处理
`template_id` 和 `template_path` 是可选字段（nullable=True），前端需要处理：
- 如果为 null，显示为"主模板"或空
- 如果有值，显示完整的层级路径

## 部署状态

- ✅ 后端代码已修改
- ✅ 后端服务已重启
- ✅ API返回数据已验证
- ✅ 数据库中已有正确的数据
- ✅ 前端无需修改（类型定义已包含这些字段）

## 测试建议

请用户在前端进行以下测试：

1. **打开已完成的任务**:
   - 使用任务 `task_11b76cd0d729`（最新的测试任务）
   - 或创建新的嵌套模板任务

2. **检查 `/generate/task_xxx` 页面**:
   - 应该能看到所有变量（主模板 + 子模板）
   - 变量应该显示所属的模板信息

3. **检查 `/logs/task_xxx` 页面**:
   - "所属模板"列应该正确显示模板层级
   - 可以按模板路径筛选日志

4. **验证实时更新**:
   - 创建新的嵌套模板任务
   - 观察 WebSocket 实时更新是否包含所有变量

---

**修复完成时间**: 2025-10-29 09:25
**状态**: ✅ 已完成、已测试、已部署
**测试结果**: 🎉 API返回数据完全正确！

