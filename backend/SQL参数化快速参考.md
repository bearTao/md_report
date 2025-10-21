# SQL参数化查询 - 快速参考卡片

## 一句话总结
**SQL结构用插值，数据值用参数化**

---

## 语法对照

| 场景 | ❌ 错误写法 | ✅ 正确写法 | 说明 |
|------|-----------|------------|------|
| **字符串值** | `WHERE id = {{id}}` | `WHERE id = :id` | 自动加引号 |
| **数字值** | `WHERE amount > {{min}}` | `WHERE amount > :min` | 保持数字格式 |
| **日期值** | `WHERE date = {{date}}` | `WHERE date = :date` | 自动格式化 |
| **IN列表** | `WHERE id IN {{ids}}` | `WHERE id IN :ids` | 自动展开数组 |
| **动态表名** | `FROM :table_name` | `FROM {{table_name}}` | 用插值 |
| **动态列名** | `SELECT :columns` | `SELECT {{columns}}` | 用插值 |
| **动态排序** | `ORDER BY :field` | `ORDER BY {{field}} {{order}}` | 用插值 |

---

## 配置模板

### 基础参数化查询
```yaml
my_variable:
  type: array
  source: sql
  dependencies:
    - param1
  sql_config:
    query: "SELECT * FROM table WHERE field = :param1"
    parameters:
      - param1
    connection: db_name
    result_mode: all_rows
```

### 混合场景（推荐）
```yaml
my_variable:
  type: array
  source: sql
  dependencies:
    - table_suffix    # 用于插值
    - user_id         # 用于参数化
  sql_config:
    query: |
      SELECT * FROM data_{{table_suffix}}
      WHERE user_id = :user_id
        AND status = :status
      ORDER BY {{sort_field}}
    parameters:
      - user_id
      - status
    connection: db_name
    result_mode: all_rows
```

---

## 类型自动转换

```python
# Python → SQL
"text"         → 'text'           # 字符串加引号
123            → 123              # 数字原样
True           → 1                # 布尔转数字
None           → NULL             # NULL值
[1, 2, 3]      → (1, 2, 3)        # IN列表展开
```

---

## 常见错误

### ❌ 错误1：字符串值缺少引号
```yaml
query: "WHERE wgid = {{wgid}}"  # ❌ 结果: WHERE wgid = ABC123 (语法错误)
```
**修复**：
```yaml
query: "WHERE wgid = :wgid"     # ✅ 结果: WHERE wgid = 'ABC123'
parameters: [wgid]
```

### ❌ 错误2：忘记声明参数
```yaml
query: "WHERE id = :id"         # 使用了 :id
parameters: []                  # ❌ 但忘记声明
```
**修复**：
```yaml
query: "WHERE id = :id"
parameters: [id]                # ✅ 声明参数
```

### ❌ 错误3：对表名使用参数化
```yaml
query: "SELECT * FROM :table_name"  # ❌ 表名不能参数化
```
**修复**：
```yaml
query: "SELECT * FROM {{table_name}}"  # ✅ 使用插值
```

---

## 安全性

### SQL注入防护
```python
# 恶意输入
user_input = "'; DROP TABLE users; --"

# ❌ 插值（危险）
query = "WHERE name = {{name}}"
# 结果: WHERE name = '; DROP TABLE users; --  ⚠️ 会执行DROP！

# ✅ 参数化（安全）
query = "WHERE name = :name"
# 结果: WHERE name = '''; DROP TABLE users; --'  ✅ 当作字符串
```

---

## 测试运行

```bash
# 运行完整测试套件
cd /data/tao/code/xuqiu/backend
python -m pytest tests/test_sql_hybrid_queries.py -v

# 运行特定测试
pytest tests/test_sql_hybrid_queries.py::test_parameterized_query_with_string -v
```

---

## 记住这些规则

1. ✅ **WHERE条件的值** → 必须参数化 (`:param`)
2. ✅ **IN列表** → 必须参数化 (`:list`)
3. ✅ **LIMIT值** → 建议参数化 (`:limit`)
4. ❌ **表名/列名** → 不能参数化，用插值 (`{{name}}`)
5. ❌ **ORDER BY字段** → 不能参数化，用插值 (`{{field}}`)
6. ⚠️  **声明参数** → 在 `parameters` 数组中列出

---

## 快速检查清单

在配置SQL变量时，问自己：

- [ ] 这是数据值吗？ → 用 `:param`
- [ ] 这是SQL结构吗？ → 用 `{{var}}`
- [ ] 我声明参数了吗？ → 检查 `parameters` 数组
- [ ] 会有特殊字符吗？ → 必须参数化，防注入

---

**文档版本**: 1.0  
**更新日期**: 2025-10-17  
**相关文档**: [SQL参数化查询修复说明.md](./SQL参数化查询修复说明.md)

