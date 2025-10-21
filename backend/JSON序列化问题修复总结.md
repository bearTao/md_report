# JSON序列化问题修复总结

## 问题描述

用户在前端执行报告生成时，后台报错：
```
TypeError: Object of type datetime is not JSON serializable
```

## 根本原因

SQL查询返回的结果包含 **datetime** 和 **Decimal** 等 Python 对象，这些对象无法直接序列化为 JSON格式，导致 API 返回失败。

## 修复方案

### 1. 修复数据库连接器 ✅

**文件:** `app/connectors/database.py`

**修改内容:**
- 添加 `_convert_to_serializable()` 方法，将不可序列化的对象转换为JSON兼容格式
- 在 `execute_query()` 方法中应用转换

**修复代码:**
```python
def _convert_to_serializable(self, obj: Any) -> Any:
    """将非JSON可序列化对象转换为可序列化格式"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()  # datetime -> ISO 8601 字符串
    elif isinstance(obj, Decimal):
        return float(obj)  # Decimal -> float
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    elif obj is None:
        return None
    else:
        return obj
```

**应用转换:**
```python
# 在 execute_query 中转换所有字段值
rows = []
for row in result:
    row_dict = {}
    for key, value in row._mapping.items():
        row_dict[key] = self._convert_to_serializable(value)
    rows.append(row_dict)
```

### 2. 修复模板中的日期格式化 ✅

**问题:** 
- 之前使用 `strftime()` 方法格式化日期
- 现在 datetime 已被转换为字符串（ISO格式）
- 需要使用字符串切片而不是 strftime()

**修复:**
```jinja2
<!-- 之前（错误） -->
{{ overview.starttime.strftime('%Y-%m-%d') if overview.starttime else '-' }}

<!-- 现在（正确） -->
{{ overview.starttime[:10] if overview.starttime else '-' }}
```

### 3. 修复 API 返回的 datetime 字段 ✅

**文件:** `app/api/reports.py`

**问题:** 
- 数据库中的 `created_at` 和 `updated_at` 可能存储为字符串
- Pydantic schema 期望 datetime 对象
- 需要手动转换

**修复代码:**
```python
# 在 list_reports 和 get_report 中添加转换
if isinstance(created_at, str):
    try:
        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        created_at = datetime.utcnow()
```

### 4. 修复数据库混淆问题 ✅

**发现的问题:**
- API 使用 **MySQL 数据库** (`md_agent`)
- 测试脚本直接写入 **SQLite 文件** (`reports.db`)
- 两个不同的数据库导致 API 查询不到测试生成的报告

**解决方案:**
修改测试脚本使用 SQLAlchemy 和 MySQL：
```python
# 使用 SQLAlchemy ORM 而不是直接写 SQLite
from app.database import SessionLocal
from app.models.db_models import Report, ReportStatus

db = SessionLocal()
report = Report(
    id=report_id,
    template_id="tpl_21c2afbe565c",
    task_id=task_id,
    title=f"微网格预分析-{user_inputs['wgid']}",
    status=ReportStatus.SUCCESS,
    markdown_content=markdown_content,
    duration_ms=sum(v.duration_ms for v in results.values()),
    created_at=datetime.now(),
    updated_at=datetime.now()
)
db.add(report)
db.commit()
```

## 测试验证

### ✅ 1. 数据库查询测试
```bash
# SQL查询返回的数据现在都是JSON可序列化的
curl "http://localhost:8000/api/reports/?template_id=tpl_21c2afbe565c"
```

**结果:**
```json
{
    "items": [
        {
            "id": "rpt_233d05e4b1d1",
            "template_id": "tpl_21c2afbe565c",
            "title": "微网格预分析-ZQGY0174",
            "status": "success",
            "created_at": "2025-10-17T10:55:27"
        }
    ],
    "total": 1
}
```

### ✅ 2. 报告详情查询测试
```bash
curl "http://localhost:8000/api/reports/rpt_233d05e4b1d1"
```

**结果:** 成功返回完整报告（8575字符），包含所有字段

### ✅ 3. 报告生成测试
```bash
python generate_microgrid_report_direct.py
```

**结果:** 
- ✅ 所有17个变量执行成功
- ✅ 模板渲染成功（8575字符）
- ✅ 报告保存到MySQL成功
- ✅ 可通过API查询到报告

## 修复的文件清单

1. **`app/connectors/database.py`** - 添加类型转换方法
2. **`app/api/reports.py`** - 修复datetime字段处理
3. **模板 `tpl_21c2afbe565c`** - 修正日期格式化语法
4. **`generate_microgrid_report_direct.py`** - 改用SQLAlchemy存储

## 数据类型转换映射

| Python类型 | JSON类型 | 转换方法 |
|-----------|---------|---------|
| `datetime` | `string` | `.isoformat()` → ISO 8601格式 |
| `date` | `string` | `.isoformat()` → YYYY-MM-DD |
| `Decimal` | `number` | `float()` |
| `bytes` | `string` | `.decode('utf-8')` |
| `None` | `null` | 保持不变 |

## API使用示例

### 生成报告
```bash
curl -X POST "http://localhost:8000/api/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{"template_id": "tpl_21c2afbe565c", "inputs": {"wgid": "ZQGY0174"}}'
```

### 查询报告列表
```bash
curl "http://localhost:8000/api/reports/?template_id=tpl_21c2afbe565c&page=1&page_size=10"
```

### 查询单个报告
```bash
curl "http://localhost:8000/api/reports/{report_id}"
```

## 关键要点

1. **数据库查询返回值** 必须是JSON可序列化的
2. **datetime对象** 应转换为ISO 8601字符串
3. **Decimal对象** 应转换为float
4. **API和测试脚本** 必须使用相同的数据库
5. **模板中的日期操作** 要根据实际数据类型调整

## 验证标准

✅ **修复成功的标志：**
- 能够通过API查询到生成的报告
- API返回完整的JSON数据（无序列化错误）
- 报告内容完整且格式正确
- 所有datetime字段正确显示为ISO 8601格式

---

**修复完成时间:** 2025-10-17  
**测试报告ID:** `rpt_233d05e4b1d1`  
**测试用例:** ZQGY0174  
**修复状态:** ✅ 所有问题已解决

