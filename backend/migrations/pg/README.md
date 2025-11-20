# 数据库迁移文档

## 迁移文件列表

### 001_add_report_modification_agent_tables.sql
**创建时间**: 2025-11-13  
**描述**: 创建报告修改代理相关表  
**影响**:
- 创建 `conversation_sessions` 表（会话管理）
- 创建 `conversation_turns` 表（对话轮次）
- 创建 `report_states` 表（报告状态）
- 创建 `modification_history` 表（修改历史）

### 002_add_report_lock_fields.sql ✨ NEW
**创建时间**: 2025-11-18  
**描述**: 为 `report_states` 表添加锁定和编辑模式相关字段  
**影响**:
- 添加 `edit_mode` 字段（编辑模式）
- 添加 `variable_snapshot` 字段（变量快照）
- 添加 `generated_at` 字段（生成时间）
- 添加 `locked_at` 字段（锁定时间）
- 添加 `lock_reason` 字段（锁定原因）
- 创建相关索引和约束

---

## 执行迁移

### 方式1：使用 psql 命令行

```bash
# 进入 conda 环境
conda activate test_md

# 连接到数据库并执行迁移
psql -h localhost -U your_username -d your_database -f migrations/pg/002_add_report_lock_fields.sql

# 或者使用环境变量
export PGHOST=localhost
export PGUSER=your_username
export PGDATABASE=your_database
psql -f migrations/pg/002_add_report_lock_fields.sql
```

### 方式2：使用 Python 脚本

```python
import psycopg2
from pathlib import Path

# 读取迁移文件
migration_file = Path(__file__).parent / "migrations/pg/002_add_report_lock_fields.sql"
sql = migration_file.read_text(encoding='utf-8')

# 连接数据库
conn = psycopg2.connect(
    host="localhost",
    database="your_database",
    user="your_username",
    password="your_password"
)

# 执行迁移
with conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        print("迁移执行成功")

conn.close()
```

### 方式3：使用 SQLAlchemy

```python
from sqlalchemy import create_engine, text
from pathlib import Path

# 创建引擎
engine = create_engine("postgresql://user:password@localhost/database")

# 读取并执行迁移
migration_file = Path(__file__).parent / "migrations/pg/002_add_report_lock_fields.sql"
sql = migration_file.read_text(encoding='utf-8')

with engine.begin() as conn:
    # 分割多个语句并执行
    for statement in sql.split(';'):
        if statement.strip():
            conn.execute(text(statement))
    
    print("迁移执行成功")
```

---

## 验证迁移

执行迁移后，运行以下查询验证：

### 1. 检查字段是否存在

```sql
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_name = 'report_states'
AND column_name IN ('edit_mode', 'variable_snapshot', 'generated_at', 'locked_at', 'lock_reason')
ORDER BY ordinal_position;
```

**期望结果**:
```
 column_name       | data_type                   | is_nullable | column_default
-------------------+-----------------------------+-------------+----------------
 edit_mode         | character varying           | NO          | 'template'
 variable_snapshot | json                        | YES         | NULL
 generated_at      | timestamp with time zone    | NO          | CURRENT_TIMESTAMP
 locked_at         | timestamp with time zone    | YES         | NULL
 lock_reason       | text                        | YES         | NULL
```

### 2. 检查索引是否创建

```sql
SELECT 
    indexname, 
    indexdef
FROM pg_indexes
WHERE tablename = 'report_states'
AND indexname LIKE 'idx_report_states_%'
ORDER BY indexname;
```

**期望结果**:
```
 indexname                        | indexdef
----------------------------------+-----------------------------------------------------
 idx_report_states_edit_mode      | CREATE INDEX ... ON report_states USING btree (edit_mode)
 idx_report_states_generated_at   | CREATE INDEX ... ON report_states USING btree (generated_at)
 idx_report_states_locked_at      | CREATE INDEX ... ON report_states USING btree (locked_at)
```

### 3. 检查约束是否创建

```sql
SELECT 
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'report_states'::regclass
AND conname = 'check_edit_mode';
```

**期望结果**:
```
 constraint_name  | constraint_definition
------------------+-------------------------------------------------------
 check_edit_mode  | CHECK ((edit_mode)::text = ANY (ARRAY['template'::character varying, 'locked'::character varying]::text[]))
```

---

## 回滚迁移

如果需要回滚 002 迁移，执行以下 SQL：

```sql
-- ⚠️ 警告：回滚会删除字段，导致数据丢失！

-- 删除字段
ALTER TABLE report_states DROP COLUMN IF EXISTS lock_reason;
ALTER TABLE report_states DROP COLUMN IF EXISTS locked_at;
ALTER TABLE report_states DROP COLUMN IF EXISTS generated_at;
ALTER TABLE report_states DROP COLUMN IF EXISTS variable_snapshot;
ALTER TABLE report_states DROP COLUMN IF EXISTS edit_mode;

-- 删除索引
DROP INDEX IF EXISTS idx_report_states_locked_at;
DROP INDEX IF EXISTS idx_report_states_generated_at;
DROP INDEX IF EXISTS idx_report_states_edit_mode;

-- 删除约束
ALTER TABLE report_states DROP CONSTRAINT IF EXISTS check_edit_mode;
```

---

## 迁移时间估算

| 表大小           | 预计执行时间 |
|-----------------|-------------|
| < 1000 行       | < 1 秒      |
| 1000 - 10000 行 | 1-3 秒      |
| 10000 - 100000 行| 3-10 秒     |
| > 100000 行     | 10-30 秒    |

**注意**：添加字段操作通常很快，主要时间消耗在创建索引上。

---

## 兼容性

- **PostgreSQL 版本**: 10+
- **风险等级**: 低（仅添加字段，不修改现有数据）
- **是否需要停机**: 否（可在线执行）
- **是否可回滚**: 是（但会丢失新增字段的数据）

---

## 常见问题

### Q: 迁移失败怎么办？

A: 检查错误信息：
- 如果提示字段已存在：可能已经执行过迁移，检查字段是否正确
- 如果提示权限不足：确保数据库用户有 ALTER TABLE 权限
- 如果提示表不存在：先执行 001 迁移创建表

### Q: 现有数据的 generated_at 怎么办？

A: 默认值会设为 CURRENT_TIMESTAMP（迁移执行时间）。如果需要使用原始创建时间，执行：

```sql
UPDATE report_states 
SET generated_at = created_at 
WHERE generated_at > created_at;
```

### Q: 如何批量测试迁移？

A: 先在测试环境执行：

```bash
# 1. 备份生产数据库
pg_dump -h localhost -U user -d prod_db > backup.sql

# 2. 还原到测试数据库
psql -h localhost -U user -d test_db < backup.sql

# 3. 在测试数据库执行迁移
psql -h localhost -U user -d test_db -f migrations/pg/002_add_report_lock_fields.sql

# 4. 验证迁移
psql -h localhost -U user -d test_db -c "SELECT * FROM report_states LIMIT 1;"

# 5. 确认无误后，在生产环境执行
```

---

## 迁移日志

记录每次迁移的执行情况：

| 迁移文件 | 执行时间 | 执行人 | 环境 | 结果 | 备注 |
|---------|---------|-------|------|------|------|
| 002     | YYYY-MM-DD HH:mm | 你的名字 | 测试/生产 | 成功/失败 | 备注信息 |

---

## 相关文档

- [删除章节功能设计文档](../../docs/FRONTEND_DELETE_SECTIONS_DESIGN.md)
- [报告修改代理架构文档](../../backend/docs/ARCHITECTURE_REPORT_MODIFICATION.md)
- [数据库设计文档](../../backend/docs/DATABASE_DESIGN.md)
