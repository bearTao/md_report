# SQL参数化查询修复说明

## 问题背景

### 原始问题

在之前的实现中，SQL查询中的变量都是通过字符串插值直接替换的，这导致了以下问题：

```yaml
# 问题配置
sql_config:
  query: "SELECT * FROM table WHERE wgid = {{wgid}}"
  parameters:
    - wgid
```

**问题表现**：
- 当 `wgid = "ZQGY0174"` 时，生成的SQL是：`WHERE wgid = ZQGY0174` ❌
- 缺少引号导致SQL语法错误
- 存在SQL注入风险

### 根本原因

直接使用字符串插值（`{{variable}}`）来替换数据值，数据库驱动无法识别这是一个字符串参数，因此不会自动添加引号或进行类型转换。

---

## 解决方案

### 核心思路：混合场景支持

支持两种占位符语法，各司其职：

| 占位符类型 | 语法 | 用途 | 示例 |
|----------|------|------|------|
| **字符串插值** | `{{variable}}` | SQL结构：表名、列名、JOIN、ORDER BY | `SELECT * FROM {{table_name}}` |
| **参数化查询** | `:param_name` | 数据值：WHERE条件、VALUES | `WHERE wgid = :wgid` |

### 修改内容

#### 1. 更新 `sql.py`

修改了 `SqlExecutor._execute_impl()` 方法，支持混合场景：

```python
async def _execute_impl(self) -> Any:
    """
    Execute SQL query and return results based on result_mode
    
    Supports hybrid scenarios:
    - {{variable}}: String interpolation for SQL structure (table names, columns, etc.)
    - :param_name: Parameterized queries for data values (safe, prevents SQL injection)
    """
    config = self.metadata.sql_config
    
    # Step 1: Interpolate {{variable}} patterns for SQL structure
    query = self.context.interpolate_string(config.query)
    
    # Step 2: Prepare parameters for :param_name placeholders
    parameters = {}
    if config.parameters:
        for param_name in config.parameters:
            if self.context.has_variable(param_name):
                parameters[param_name] = self.context.get_variable(param_name)
    
    # Step 3: Execute query with both interpolated SQL and parameters
    results = await db_connector.execute_query(
        connection_name=config.connection,
        query=query,
        parameters=parameters,
        timeout=config.timeout or 10
    )
    # ... 后续处理
```

---

## 使用指南

### 场景1：纯参数化查询（推荐）

**问题场景的正确修复**：

```yaml
plan_sites:
  type: array
  source: sql
  dependencies:
    - wgid
  sql_config:
    query: |
      SELECT 
        site_name,
        site_type,
        longitude,
        latitude,
        plan_status,
        is_related_problem
      FROM microgrid.micro_grid_plan_w
      WHERE wgid = :wgid              -- ✅ 使用 :wgid 占位符
      ORDER BY 
        CASE WHEN is_related_problem THEN 1 ELSE 2 END,
        site_name
    parameters:
      - wgid                          -- ✅ 声明参数
    connection: microgrid_db
    result_mode: all_rows
```

**执行结果**：
- 当 `wgid = "ZQGY0174"` 时
- 实际SQL：`WHERE wgid = 'ZQGY0174'` ✅（自动加引号）

### 场景2：混合查询 - 动态表名 + 参数化条件

```yaml
user_data:
  type: object
  source: sql
  dependencies:
    - table_name    # 用于插值
    - user_id       # 用于参数化
  sql_config:
    query: |
      SELECT id, name, email
      FROM {{table_name}}             -- 插值：动态表名
      WHERE id = :user_id             -- 参数化：数据值
    parameters:
      - user_id                       -- 只声明参数化的变量
    connection: user_db
    result_mode: first_row
```

**执行过程**：
1. `table_name = "users_2025"` → `FROM users_2025`（插值）
2. `user_id = 12345` → `WHERE id = 12345`（参数化，数字无引号）

### 场景3：混合查询 - 动态列 + 多参数条件

```yaml
employee_list:
  type: array
  source: sql
  dependencies:
    - extra_columns   # 用于插值
  sql_config:
    query: |
      SELECT 
        id, 
        name, 
        {{extra_columns}}             -- 插值：动态列
      FROM employees
      WHERE status = :status           -- 参数化：字符串
        AND department = :dept         -- 参数化：字符串
        AND salary > :min_salary       -- 参数化：数字
      ORDER BY id
    parameters:
      - status
      - dept
      - min_salary
    connection: hr_db
    result_mode: all_rows
```

**执行过程**：
1. `extra_columns = "department, salary"` → `SELECT id, name, department, salary`
2. `status = "active"` → `WHERE status = 'active'`
3. `dept = "Engineering"` → `AND department = 'Engineering'`
4. `min_salary = 80000` → `AND salary > 80000`

### 场景4：混合查询 - 动态ORDER BY + 参数化过滤

```yaml
products:
  type: array
  source: sql
  dependencies:
    - sort_field      # 用于插值
    - sort_order      # 用于插值
  sql_config:
    query: |
      SELECT id, name, price, stock
      FROM products
      WHERE category = :category      -- 参数化
        AND price > :min_price        -- 参数化
      ORDER BY {{sort_field}} {{sort_order}}  -- 插值
      LIMIT :limit_count              -- 参数化
    parameters:
      - category
      - min_price
      - limit_count
    connection: product_db
    result_mode: all_rows
```

---

## 参数类型自动处理

参数化查询会根据数据类型自动处理：

| Python类型 | SQL处理 | 示例 |
|-----------|---------|------|
| `str` | 自动加单引号 | `'ZQGY0174'` |
| `int/float` | 保持原样 | `12345` |
| `bool` | 转换为0/1 | `1` or `0` |
| `None` | 转换为NULL | `NULL` |
| `datetime` | 格式化为字符串 | `'2025-10-17 10:30:00'` |
| `list` (IN) | 展开为列表 | `('val1', 'val2', 'val3')` |

---

## 安全性优势

### SQL注入防护

**恶意输入测试**：
```python
wgid = "'; DROP TABLE users; --"  # 恶意SQL注入尝试
```

**使用字符串插值（❌ 不安全）**：
```sql
WHERE wgid = {{wgid}}
-- 结果：WHERE wgid = '; DROP TABLE users; --
-- ❌ 会执行DROP TABLE命令！
```

**使用参数化查询（✅ 安全）**：
```sql
WHERE wgid = :wgid
-- 结果：WHERE wgid = '''; DROP TABLE users; --'
-- ✅ 恶意代码被当作普通字符串处理
```

---

## 测试覆盖

已创建完整的测试套件 `tests/test_sql_hybrid_queries.py`，覆盖以下场景：

1. ✅ **纯参数化查询 - 字符串类型** (`test_parameterized_query_with_string`)
2. ✅ **纯参数化查询 - 数字类型** (`test_parameterized_query_with_number`)
3. ✅ **混合场景 - 动态表名 + 参数化WHERE** (`test_hybrid_dynamic_table_with_params`)
4. ✅ **混合场景 - 动态列名 + 参数化过滤** (`test_hybrid_dynamic_columns_with_params`)
5. ✅ **混合场景 - 动态ORDER BY + 参数化WHERE** (`test_hybrid_dynamic_order_with_params`)
6. ✅ **混合场景 - 动态WHERE子句 + 参数化值** (`test_hybrid_dynamic_where_clause_with_params`)
7. ✅ **SQL注入防护测试** (`test_sql_injection_prevention`)
8. ✅ **多参数同时使用** (`test_multiple_params_same_query`)

**运行测试**：
```bash
cd /data/tao/code/xuqiu/backend
python -m pytest tests/test_sql_hybrid_queries.py -v
```

**测试结果**：
```
============================= test session starts ==============================
8 passed, 10 warnings in 0.53s
```

---

## 迁移指南

### 需要修改的配置

如果你的现有配置使用了字符串插值来传递数据值，需要修改为参数化查询：

#### ❌ 修改前（错误）

```yaml
sql_config:
  query: "SELECT * FROM sites WHERE wgid = {{wgid}} AND status = {{status}}"
  parameters: []
```

#### ✅ 修改后（正确）

```yaml
sql_config:
  query: "SELECT * FROM sites WHERE wgid = :wgid AND status = :status"
  parameters:
    - wgid
    - status
```

### 不需要修改的配置

以下场景仍然使用字符串插值（`{{variable}}`）：

- 动态表名：`FROM {{table_name}}`
- 动态列名：`SELECT {{columns}}`
- 动态JOIN：`{{join_clause}}`
- 动态ORDER BY：`ORDER BY {{sort_field}} {{order}}`
- 动态WHERE子句：`WHERE 1=1 {{extra_conditions}}`

---

## 最佳实践

### ✅ 推荐做法

1. **数据值使用参数化**：所有WHERE条件、VALUES中的数据值都使用 `:param_name`
2. **结构使用插值**：表名、列名、JOIN、ORDER BY等SQL结构使用 `{{variable}}`
3. **明确声明参数**：在 `parameters` 数组中列出所有参数化的变量
4. **使用命名参数**：使用 `:param_name` 而不是 `?`，可读性更好

### ❌ 避免的做法

1. **不要对数据值使用插值**：`WHERE id = {{id}}` ❌ → 使用 `WHERE id = :id` ✅
2. **不要混淆两种语法**：`WHERE id = {{:id}}` ❌
3. **不要忘记声明参数**：使用了 `:param` 但没有在 `parameters` 中声明

---

## 总结

### 问题
- 字符串插值导致字符串类型缺少引号，SQL语法错误
- 存在SQL注入安全风险

### 解决方案
- 支持混合场景：插值（SQL结构）+ 参数化（数据值）
- 使用 `:param_name` 语法进行参数化查询
- 数据库驱动自动处理类型转换和安全转义

### 优势
- ✅ 自动类型处理（字符串加引号、数字保持原样）
- ✅ 防止SQL注入
- ✅ 更好的性能（查询计划缓存）
- ✅ 代码可读性更好

### 向后兼容
- ✅ 原有的纯插值查询仍然可用（不推荐）
- ✅ 原有的测试全部通过
- ✅ 新增8个测试用例覆盖混合场景

---

**修复完成日期**: 2025-10-17  
**测试状态**: 全部通过 ✅  
**安全性**: 已防护SQL注入 ✅

