# Example Usage 示例说明

## 文件位置
`backend/example_usage.py`

## 示例概述

### 示例1: 简单的项目报告生成 (`example_simple_report`)
- **功能**: 演示基础的报告生成流程
- **涉及变量类型**: 
  - USER_INPUT: 用户输入变量
  - SYSTEM: 系统生成变量（时间、UUID、常量）
- **特点**: 展示最基本的变量定义和模板渲染

### 示例2: 带依赖关系的变量执行 (`example_with_dependencies`)
- **功能**: 演示变量间的依赖关系和DAG执行
- **涉及变量类型**:
  - USER_INPUT: 基础输入
  - SYSTEM: 依赖其他变量的系统变量
- **特点**: 展示变量依赖、批次执行、插值功能

### 示例3: SQL变量所有ResultMode类型演示 (`example_sql_result_modes`) ⭐ 新增
- **功能**: 完整展示所有5种SQL result_mode的配置方式和使用场景
- **涉及变量类型**: SQL变量的所有返回模式
- **特点**: 这是一个配置参考示例，实际运行需要数据库连接

## 示例3详细说明

### 📋 包含的SQL ResultMode类型

#### 1. FIRST_ROW模式
**变量**: `user_profile`
```python
result_mode=SqlResultMode.FIRST_ROW
```
- **说明**: 返回第一行作为对象
- **返回格式**: `{id: 1, name: "Alice", email: "...", ...}`
- **适用场景**: 查询单条完整记录（用户详情、商品详情等）

#### 2. ALL_ROWS模式
**变量**: `team_members`
```python
result_mode=SqlResultMode.ALL_ROWS
```
- **说明**: 返回所有行作为数组
- **返回格式**: `[{row1}, {row2}, ...]`
- **适用场景**: 查询多条完整记录（订单列表、用户列表等）

#### 3. FIRST_VALUE模式
**变量**: `total_sales`, `active_user_count`
```python
result_mode=SqlResultMode.FIRST_VALUE
```
- **说明**: 返回第一行第一列的标量值
- **返回格式**: `12345.67` 或 `156`
- **适用场景**: 统计聚合结果（SUM、COUNT、AVG、MAX等）

#### 4. FIRST_COLUMN模式
**变量**: `product_ids`, `top_customer_names`
```python
result_mode=SqlResultMode.FIRST_COLUMN
```
- **说明**: 返回第一列的所有值
- **返回格式**: `[101, 102, 103, ...]` 或 `["Customer A", "Customer B", ...]`
- **适用场景**: 仅需ID列表、名称列表等单列数据

#### 5. AUTO模式（默认）
**变量**: `company_info`, `recent_orders`
```python
result_mode=SqlResultMode.AUTO  # 可省略，这是默认值
```
- **说明**: 根据变量的`type`和实际数据智能判断返回格式
- **智能规则**:
  - `type="object"` + 单行 → 返回对象
  - `type="object"` + 多行 → 返回数组（避免数据丢失）
  - `type="array"` → 返回所有行
  - `type="string/number/boolean"` → 返回第一行第一列
- **适用场景**: 大多数常规场景

### 📊 示例中的完整配置

示例3包含：
- **8个SQL变量** - 涵盖所有5种result_mode
- **5个用户输入变量** - 作为SQL查询参数
- **1个系统变量** - 报告日期
- **1个复杂的Markdown模板** - 展示如何在模板中使用不同类型的SQL结果

### 🎯 模板特色

生成的Markdown模板展示了：
1. **对象访问**: `{{user_profile.name}}`
2. **数组遍历**: `{% for member in team_members %}`
3. **标量值使用**: `{{total_sales|round(2)}}`
4. **列表长度**: `{{team_members|length}}`
5. **数组切片**: `{{recent_orders[:5]}}`
6. **表格生成**: 使用Jinja2循环创建Markdown表格

### 📄 模板结构

模板包含5个主要部分：
1. **用户分析** - 演示FIRST_ROW和ALL_ROWS
2. **业务指标** - 演示FIRST_VALUE
3. **产品信息** - 演示FIRST_COLUMN
4. **综合信息** - 演示AUTO模式
5. **选择指南** - ResultMode使用建议表格

## 运行示例

### 运行所有示例
```bash
cd backend
python3 example_usage.py
```

### 查看示例3输出
```bash
cd backend
python3 example_usage.py 2>&1 | grep -A 100 "示例3"
```

## 输出示例

运行示例3时，你会看到：
```
============================================================
示例3: SQL变量ResultMode完整演示
============================================================

本示例展示所有5种SQL result_mode的配置方式
注意：这是配置示例，实际运行需要配置数据库连接

📋 变量配置概览:

FIRST_ROW (返回第一行对象):
  • user_profile: 用户档案信息（单个对象）
    SQL: SELECT id, name, email, department, role, hire_date FROM use...

ALL_ROWS (返回所有行数组):
  • team_members: 团队成员列表（数组）
    SQL: SELECT id, name, email, role, performance_score ...

... (更多输出)

✅ SQL ResultMode完整示例配置展示完成

💡 提示:
1. 实际使用时需要先配置数据库连接: db_connector.register_connection()
2. 根据实际数据表结构调整SQL查询语句
3. AUTO模式是默认值，适合大多数场景
4. 选择明确的模式可以提高代码可读性和可维护性
```

## 实际使用指南

虽然示例3是一个配置参考，但你可以通过以下步骤让它实际运行：

### 步骤1: 准备测试数据库
```sql
-- 创建测试表
CREATE TABLE users (...);
CREATE TABLE sales (...);
CREATE TABLE products (...);
-- 等等
```

### 步骤2: 注册数据库连接
```python
from app.connectors.database import db_connector

db_connector.register_connection(
    "user_db",
    "mysql+pymysql://user:pass@host:port/dbname"
)
```

### 步骤3: 提供用户输入
```python
user_inputs = {
    "user_id": 1,
    "department_id": 10,
    "category_id": 5,
    "start_date": "2025-01-01",
    "end_date": "2025-03-31"
}
```

### 步骤4: 执行变量和渲染模板
```python
context = ExecutionContext(
    task_id="demo_task_003",
    template_id="demo_template_003",
    user_inputs=user_inputs,
    metadata=metadata
)

scheduler = ExecutionScheduler()
results = await scheduler.execute_all(context)

markdown = template_renderer.render(
    template_content, 
    context.get_all_variables()
)
```

## 总结

示例3提供了一个完整的、生产级的SQL变量配置参考，涵盖了所有5种result_mode的实际使用场景。开发者可以：
1. 快速理解每种模式的用途
2. 复制相应的配置代码
3. 参考模板中的变量使用方式
4. 根据实际需求调整SQL查询

这个示例是学习和使用SQL result_mode功能的最佳起点！🎯


