# 变量重试Context加载修复说明

**修复日期**: 2025-10-23  
**版本**: v1.0

---

## 问题背景

### 发现的错误

在变量重试成功后自动重新生成报告时，出现两个错误：

#### 错误1：模板渲染失败
```
Error continuing report generation: Template rendering failed: 'dict object' has no attribute 'wgid_score'
jinja2.exceptions.UndefinedError: 'dict object' has no attribute 'wgid_score'
```

**原因**：模板引用了`index_scores.wgid_score`，但`index_scores`变量未正确加载到context中。

#### 错误2：Pydantic验证错误
```
ValidationError: 1 validation error for TaskVariableDetail
result_preview
  Input should be a valid dictionary [type=dict_type, input_value=[{...}], input_type=list]
```

**原因**：`result_preview`字段定义只接受dict，但某些变量（如`coverage_analysis`）返回的是list。

### 根本原因

1. **不完整的值保存**：
   - 主执行流程中，`result_preview`只保存前500字符的预览字符串
   - 格式：`{"preview": "前500字符..."}`
   - 导致重试时无法获得完整的变量值

2. **Context加载不完整**：
   - 在`continue_report_generation`中直接使用传入的context
   - 该context在重试开始时创建，不包含刚刚重试成功的变量
   - 导致模板渲染时找不到某些变量

---

## 修复方案

### 修复1：保存完整的变量值

**文件**：`/data/tao/code/xuqiu/backend/app/api/reports.py`

**修改位置**：主执行流程（约第348-351行）

**修改前**：
```python
# Store preview of result (limit size)
if result.value is not None:
    import json
    preview = json.dumps(result.value, ensure_ascii=False)[:500]
    var_record.result_preview = {"preview": preview}
```

**修改后**：
```python
# Store complete result value for context reuse (e.g., in retry scenarios)
# JSON field can store dict, list, str, int, float, bool, None
if result.value is not None:
    var_record.result_preview = result.value
```

**说明**：
- 保存完整的变量值，而不是前500字符的预览
- PostgreSQL的JSON字段可以存储任何JSON类型的数据
- 确保重试时能获得完整的变量值用于模板渲染

### 修复2：重试流程保持一致

**文件**：同上

**修改位置**：重试执行函数（约第940-943行）

**修改前**：
```python
if result.status == VariableStatus.SUCCESS:
    var_record.result_preview = result.value if isinstance(result.value, (dict, list)) else None
    db_session.commit()
```

**修改后**：
```python
if result.status == VariableStatus.SUCCESS:
    # Store complete result value consistent with main execution flow
    # JSON field can store dict, list, str, int, float, bool, None
    var_record.result_preview = result.value
    db_session.commit()
```

**说明**：
- 与主执行流程保持一致
- 不再区分dict/list，直接保存原始值
- 支持所有JSON兼容的数据类型

### 修复3：重新加载所有成功变量

**文件**：同上

**修改位置**：`continue_report_generation`函数（约第1015-1024行）

**修改前**：
```python
async def continue_report_generation(task_id: str, context: ExecutionContext, db_session: Session):
    try:
        # Get task and template
        task = db_session.query(GenerationTask).filter_by(id=task_id).first()
        template = db_session.query(Template).filter_by(id=task.template_id).first()
        
        # Render template
        markdown_content = template_renderer.render(
            template_content=template.template_content,
            variables=context.get_all_variables()
        )
```

**修改后**：
```python
async def continue_report_generation(task_id: str, context: ExecutionContext, db_session: Session):
    try:
        # Get task and template
        task = db_session.query(GenerationTask).filter_by(id=task_id).first()
        template = db_session.query(Template).filter_by(id=task.template_id).first()
        
        # Reload ALL successful variables into context to ensure we have complete data
        # This is important because the context might have been created before the retry
        successful_vars = db_session.query(GenerationTaskVariable).filter(
            GenerationTaskVariable.task_id == task_id,
            GenerationTaskVariable.status == VariableStatusType.SUCCESS
        ).all()
        
        for var in successful_vars:
            if var.result_preview is not None:
                context.set_variable(var.variable_name, var.result_preview)
        
        # Render template
        markdown_content = template_renderer.render(
            template_content=template.template_content,
            variables=context.get_all_variables()
        )
```

**说明**：
- 在渲染模板前，重新加载所有成功的变量
- 确保context包含最新的所有变量（包括刚刚重试成功的）
- 解决了context过时的问题

---

## 修复效果

### 修复前的流程
```
主执行 → 保存预览（前500字符） → 重试 → context只有旧变量 → 渲染失败 ❌
```

### 修复后的流程
```
主执行 → 保存完整值 → 重试 → 重新加载所有变量 → 渲染成功 ✅
```

### 解决的问题

1. ✅ **模板渲染失败**：所有变量现在都能正确加载到context
2. ✅ **数据不完整**：保存完整值而不是预览
3. ✅ **Context过时**：渲染前重新加载最新数据
4. ✅ **支持所有类型**：dict、list、str、int、float、bool、None都能正确保存和加载

---

## 注意事项

### 1. 数据库大小

**影响**：
- 修改前：每个变量最多保存500字符的预览
- 修改后：保存完整的变量值

**建议**：
- 对于特别大的变量值（如大量数据的数组），考虑在变量定义时进行数据聚合
- PostgreSQL的JSON字段可以高效存储和查询JSON数据
- 定期清理旧的任务记录以控制数据库大小

### 2. API响应

**现有问题**：
- `result_preview`字段的schema定义为`Optional[Dict[str, Any]]`
- 但现在可能包含list、str等其他类型

**临时解决**：
- 用户选择不修改schema（第一个修复方案被跳过）
- 如果API返回list类型会导致验证错误

**长期建议**：
- 修改schema定义为`Optional[Union[Dict[str, Any], List[Any], str, int, float, bool]]`
- 或使用`Optional[Any]`

### 3. 向后兼容性

**旧数据**：
- 旧的任务记录可能还保存着`{"preview": "..."}`格式
- 新代码会将其作为普通dict加载到context
- 可能导致模板无法正确访问数据

**处理方式**：
- 旧任务在重试时会重新保存为完整值
- 新任务直接使用新格式
- 如果需要，可以写脚本清理旧数据

---

## 测试验证

### 测试步骤

1. **生成新报告**
   - 创建包含多种类型变量的模板（dict、list、jinja_expression）
   - 生成报告，让某个AI变量失败
   
2. **测试重试**
   - 点击失败变量的"重试"按钮
   - 等待变量执行成功
   
3. **验证结果**
   - ✅ 所有变量都成功执行
   - ✅ 自动触发报告生成
   - ✅ 报告渲染成功，无模板错误
   - ✅ 报告内容包含所有变量的数据

### 测试用例

#### 用例1：dict类型变量
```yaml
variable_name: index_scores
source: jinja_expression
expression: |
  {
    "wgid_score": 75.5,
    "coverage_score": 82.3
  }
```
**验证**：重试后能访问`index_scores.wgid_score`

#### 用例2：list类型变量
```yaml
variable_name: coverage_analysis
source: ai_generation
schema:
  type: array
```
**验证**：重试后list完整保存和加载

#### 用例3：混合场景
- 多个变量，部分成功，部分失败
- 重试失败变量
- 验证报告包含所有变量数据

---

## 相关文件

- **后端代码**: `/data/tao/code/xuqiu/backend/app/api/reports.py`
- **数据模型**: `/data/tao/code/xuqiu/backend/app/models/db_models.py`
- **API Schema**: `/data/tao/code/xuqiu/backend/app/schemas/api_schemas.py`

---

## 更新日志

### v1.0 (2025-10-23)

**修复**:
- ✅ 修改主执行流程，保存完整变量值
- ✅ 修改重试流程，保持与主流程一致
- ✅ 修改`continue_report_generation`，重新加载所有成功变量

**改进**:
- ✅ 支持所有JSON兼容的数据类型
- ✅ 确保context始终包含最新的完整数据
- ✅ 解决模板渲染失败问题

---

**最后更新**: 2025-10-23

