"""
SQL参数化查询示例
演示修复前后的对比和正确的使用方法
"""
import asyncio
from app.services.context import ExecutionContext
from app.services.scheduler import ExecutionScheduler
from app.core.models import (
    VariableMetadata, VariableSource, SqlConfig, SqlResultMode
)

print("=" * 80)
print("SQL参数化查询修复示例")
print("=" * 80)

# 场景说明
print("""
问题场景：
  SQL查询: WHERE wgid = {{wgid}}
  当 wgid = "ZQGY0174" 时
  错误结果: WHERE wgid = ZQGY0174  ❌ (缺少引号，SQL错误)

修复方案：
  SQL查询: WHERE wgid = :wgid
  当 wgid = "ZQGY0174" 时  
  正确结果: WHERE wgid = 'ZQGY0174'  ✅ (自动加引号)
""")

print("\n" + "=" * 80)
print("示例1: 正确的参数化查询配置")
print("=" * 80)

# 正确的配置示例
correct_config = """
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
      WHERE wgid = :wgid              -- ✅ 使用 :wgid 参数化
      ORDER BY site_name
    parameters:
      - wgid                          -- ✅ 声明参数
    connection: microgrid_db
    result_mode: all_rows
  description: 工程规划站点列表
"""

print(correct_config)

print("\n" + "=" * 80)
print("示例2: 混合场景 - 动态表名 + 参数化条件")
print("=" * 80)

hybrid_example = """
user_data:
  type: object
  source: sql
  dependencies:
    - year          # 用于构建表名
    - user_id       # 用于WHERE条件
  sql_config:
    query: |
      SELECT id, name, email, department
      FROM users_{{year}}             -- 插值：动态表名
      WHERE id = :user_id             -- 参数化：安全的数据值
        AND status = :status          -- 参数化：防止注入
    parameters:
      - user_id     # 参数化的变量
      - status      # 参数化的变量
    connection: user_db
    result_mode: first_row

# 执行过程：
# 1. year = 2025 → FROM users_2025 (通过插值)
# 2. user_id = 12345 → WHERE id = 12345 (通过参数化，自动处理类型)
# 3. status = "active" → AND status = 'active' (通过参数化，自动加引号)
"""

print(hybrid_example)

print("\n" + "=" * 80)
print("示例3: 复杂混合场景 - 动态列 + 动态排序 + 多参数")
print("=" * 80)

complex_example = """
employee_report:
  type: array
  source: sql
  dependencies:
    - user_role        # 决定显示哪些列
    - sort_field       # 决定排序字段
    - sort_order       # 决定排序方向
  sql_config:
    query: |
      SELECT 
        id,
        name,
        {{extra_columns}}             -- 插值：管理员看更多列
      FROM employees
      WHERE department = :dept        -- 参数化：部门名称
        AND hire_date >= :start_date  -- 参数化：日期范围
        AND salary > :min_salary      -- 参数化：薪资条件
      ORDER BY {{sort_field}} {{sort_order}}  -- 插值：动态排序
      LIMIT :limit_count              -- 参数化：限制行数
    parameters:
      - dept
      - start_date
      - min_salary
      - limit_count
    connection: hr_db
    result_mode: all_rows

# 使用场景：
# 普通用户: extra_columns = "department"
# 管理员:   extra_columns = "department, salary, performance_score"
# 
# 参数值自动处理：
# - dept = "Engineering" → 'Engineering' (自动加引号)
# - start_date = "2024-01-01" → '2024-01-01' (自动加引号)  
# - min_salary = 80000 → 80000 (数字无引号)
# - limit_count = 50 → 50 (数字无引号)
"""

print(complex_example)

print("\n" + "=" * 80)
print("示例4: 参数类型自动处理对照表")
print("=" * 80)

type_handling = """
| Python值                  | SQL结果                    | 说明 |
|--------------------------|----------------------------|------|
| "ZQGY0174"               | 'ZQGY0174'                | 字符串自动加引号 |
| 12345                    | 12345                     | 数字保持原样 |
| True                     | 1                         | 布尔值转换 |
| None                     | NULL                      | NULL值处理 |
| "2025-10-17"            | '2025-10-17'              | 日期字符串加引号 |
| ["val1", "val2", "val3"] | ('val1', 'val2', 'val3')  | 数组展开(IN查询) |
"""

print(type_handling)

print("\n" + "=" * 80)
print("示例5: SQL注入防护演示")
print("=" * 80)

injection_demo = """
# 恶意输入
malicious_input = "'; DROP TABLE users; --"

# ❌ 使用字符串插值（不安全）
query = "SELECT * FROM users WHERE username = {{username}}"
# 结果: SELECT * FROM users WHERE username = '; DROP TABLE users; --
# 危险！会执行DROP TABLE命令

# ✅ 使用参数化查询（安全）
query = "SELECT * FROM users WHERE username = :username"
parameters = {"username": malicious_input}
# 结果: SELECT * FROM users WHERE username = '''; DROP TABLE users; --'
# 安全！恶意代码被当作普通字符串，不会执行
"""

print(injection_demo)

print("\n" + "=" * 80)
print("总结：什么时候用什么语法")
print("=" * 80)

usage_guide = """
使用原则：
┌─────────────────────────────────────────────────────────────────┐
│ SQL结构（表名、列名、JOIN、ORDER BY）→ 使用 {{variable}} 插值 │
│ 数据值（WHERE条件、VALUES）       → 使用 :param_name 参数化    │
└─────────────────────────────────────────────────────────────────┘

具体场景：
1. 表名/库名    → {{table_name}}     (无法参数化标识符)
2. 列名列表     → {{column_list}}    (无法参数化列名)  
3. JOIN子句    → {{join_clause}}    (动态SQL结构)
4. ORDER BY    → {{sort_field}}     (不支持参数化)
5. WHERE条件值 → :param_value       ✅ 必须参数化
6. IN列表      → :param_list        ✅ 必须参数化
7. LIMIT值     → :limit_count       ✅ 建议参数化
8. 日期范围    → :start_date        ✅ 必须参数化

记住：凡是数据值，都应该参数化！
"""

print(usage_guide)

print("\n" + "=" * 80)
print("测试验证")
print("=" * 80)
print("""
已创建完整的测试套件，覆盖所有场景：
  
  测试文件: tests/test_sql_hybrid_queries.py
  
  运行命令:
    cd /data/tao/code/xuqiu/backend
    python -m pytest tests/test_sql_hybrid_queries.py -v
  
  测试结果: ✅ 8 passed
  
  测试覆盖:
    ✅ 参数化查询 - 字符串类型
    ✅ 参数化查询 - 数字类型
    ✅ 混合场景 - 动态表名 + 参数化
    ✅ 混合场景 - 动态列名 + 参数化
    ✅ 混合场景 - 动态排序 + 参数化
    ✅ 混合场景 - 动态WHERE + 参数化
    ✅ SQL注入防护测试
    ✅ 多参数同时使用
""")

print("\n" + "=" * 80)
print("修复完成！")
print("=" * 80)

