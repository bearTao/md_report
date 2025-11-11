# 技术设计: MySQL 到 PostgreSQL 迁移

## Context

### 当前状态
- 项目使用 MySQL 作为主数据库
- 默认连接: `mysql+pymysql://root:123456@10.10.20.10:24406/md_agent`
- 使用 SQLAlchemy ORM，理论上支持多种数据库
- 开发/测试环境也使用 SQLite

### 迁移目标
- 目标数据库: PostgreSQL
- 连接信息:
  - Host: 10.10.20.10
  - Port: 14632
  - Database: new_md_agent
  - Username: microgrid
  - Password: microgrid123

### 约束条件
1. 不需要支持渐进式迁移（一次性完成）
2. 没有严格的停机时间约束
3. 必须保证数据完整性和一致性
4. 需要避免 SQL 语法差异导致的 bug

## Goals / Non-Goals

### Goals
1. ✅ 将所有数据库连接从 MySQL 迁移到 PostgreSQL
2. ✅ 迁移所有现有数据到新数据库
3. ✅ 修复所有 MySQL 和 PostgreSQL 之间的 SQL 语法差异
4. ✅ 保持代码的数据库抽象层（仍使用 SQLAlchemy）
5. ✅ 确保所有功能测试通过
6. ✅ 更新相关文档

### Non-Goals
1. ❌ 不改变数据模型结构（保持现有表结构）
2. ❌ 不添加新功能或优化性能（除非必要）
3. ❌ 不支持多数据库同时运行（纯粹的替换）
4. ❌ 不支持自动回滚（需要手动操作）

## Decisions

### 决策 1: 数据库驱动选择

**选择**: `psycopg2-binary`

**理由**:
- `psycopg2` 是 PostgreSQL 最成熟和广泛使用的 Python 驱动
- `psycopg2-binary` 包含预编译的二进制文件，安装简单
- SQLAlchemy 官方推荐的 PostgreSQL 驱动
- 性能优秀，稳定可靠

**替代方案**:
- `psycopg3`: 较新，但生态成熟度不如 psycopg2
- `asyncpg`: 异步驱动，性能更好，但需要改动更多代码

### 决策 2: 连接 URL 格式

**格式**: `postgresql://microgrid:microgrid123@10.10.20.10:14632/new_md_agent`

**理由**:
- 标准的 PostgreSQL 连接 URL 格式
- SQLAlchemy 原生支持
- 可通过环境变量 `DATABASE_URL` 配置，灵活性高

**注意事项**:
- 如果密码包含特殊字符，需要进行 URL 编码
- 可以添加连接参数，如 `?sslmode=require`

### 决策 3: 布尔字段处理

**变更**: 将 `DBConnection.is_active` 从字符串 `"true"`/`"false"` 改为真正的布尔类型

**理由**:
- MySQL 没有真正的布尔类型（使用 TINYINT(1)），所以项目中使用字符串模拟
- PostgreSQL 有原生的 `BOOLEAN` 类型，应该使用正确的类型
- 提高类型安全性，避免字符串比较错误

**迁移策略**:
```python
# 数据迁移时转换
is_active = "true"  # MySQL 中
is_active = True     # PostgreSQL 中
```

### 决策 4: 枚举类型处理

**方案**: 继续使用 SQLAlchemy 的 `SQLEnum`，映射到 Python `enum.Enum`

**理由**:
- PostgreSQL 支持原生 ENUM 类型
- SQLAlchemy 的 `SQLEnum` 会根据数据库自动选择实现方式:
  - PostgreSQL: 使用原生 ENUM
  - MySQL: 使用 ENUM 或 VARCHAR + CHECK 约束
- 代码无需修改，ORM 层自动处理

**注意**:
- 迁移时 Alembic 会自动创建 PostgreSQL ENUM 类型
- 如果需要修改枚举值，PostgreSQL 的操作与 MySQL 不同

### 决策 5: JSON 字段处理

**方案**: 使用 SQLAlchemy 的 `JSON` 类型

**理由**:
- PostgreSQL 有两种 JSON 类型: `JSON` 和 `JSONB`
- SQLAlchemy 的 `JSON` 类型会映射到 `JSONB`（性能更好，支持索引）
- 现有代码无需修改

**优势**:
- PostgreSQL 的 JSON 支持更强大（原生操作符、索引、约束）
- 比 MySQL 的 JSON 类型功能更丰富

### 决策 6: 超时设置

**MySQL**:
```sql
SET SESSION max_execution_time = 30000;  -- 毫秒
```

**PostgreSQL**:
```sql
SET statement_timeout = 30000;  -- 毫秒
```

**理由**:
- 两者语法不同，需要根据数据库类型选择
- 项目中 `connectors/database.py` 已经处理了这个差异
- 无需额外修改

### 决策 7: 测试数据库选择

**方案**: 单元测试继续使用 SQLite，集成测试使用 PostgreSQL

**理由**:
- SQLite 轻量、快速，适合快速单元测试
- 集成测试使用真实的 PostgreSQL，确保兼容性
- 平衡测试速度和准确性

**配置**:
```python
# conftest.py
if os.getenv("CI") or os.getenv("INTEGRATION_TEST"):
    # 集成测试: 使用 PostgreSQL
    DATABASE_URL = "postgresql://test_user:test_pass@localhost:5432/test_db"
else:
    # 单元测试: 使用 SQLite
    DATABASE_URL = "sqlite:///./test.db"
```

### 决策 8: 数据迁移策略

**方案**: 使用自定义 Python 脚本进行迁移

**步骤**:
1. 从 MySQL 导出数据（使用 SQLAlchemy 查询）
2. 转换数据格式（处理类型差异）
3. 导入到 PostgreSQL（使用 SQLAlchemy 插入）
4. 验证数据完整性

**理由**:
- 灵活性高，可以处理复杂的数据转换
- 可以使用 SQLAlchemy 的 ORM，代码简洁
- 易于调试和回滚

**替代方案**:
- 使用 `pg_dump` 和 `mysql2pgsql` 工具: 但需要处理 SQL 语法差异
- 使用 ETL 工具（如 Apache Airflow）: 过于复杂，不适合小规模迁移

## Risks / Trade-offs

### 风险 1: SQL 语法差异导致的 Bug

**风险等级**: 高

**描述**: 
- MySQL 和 PostgreSQL 的 SQL 语法有差异
- 如果项目中使用了原生 SQL 字符串，可能存在兼容性问题

**缓解措施**:
1. 全面搜索项目中的 SQL 字符串（使用 `grep`）
2. 重点检查以下差异:
   - 字符串连接: MySQL 的 `CONCAT()` vs PostgreSQL 的 `||`
   - 限制结果: MySQL 的 `LIMIT n OFFSET m` vs PostgreSQL 相同（兼容）
   - 日期函数: MySQL 的 `NOW()` vs PostgreSQL 的 `CURRENT_TIMESTAMP`
   - 自增 ID: MySQL 的 `AUTO_INCREMENT` vs PostgreSQL 的 `SERIAL`
   - 引号: MySQL 的反引号 `` `table` `` vs PostgreSQL 的双引号 `"table"`
3. 编写全面的测试用例
4. 在测试环境充分验证

### 风险 2: 数据迁移不完整或错误

**风险等级**: 高

**描述**:
- 数据迁移过程中可能丢失数据
- 类型转换可能导致数据损坏

**缓解措施**:
1. 在迁移前完整备份 MySQL 数据
2. 编写详细的验证脚本:
   - 验证每个表的行数
   - 验证关键字段的数据完整性
   - 验证外键关系
   - 验证 JSON 字段的有效性
3. 在测试环境先进行迁移演练
4. 迁移后保留 MySQL 备份数据至少 1 周

### 风险 3: 性能下降

**风险等级**: 低

**描述**: 
- 新数据库性能可能不如旧数据库

**缓解措施**:
1. PostgreSQL 的性能通常优于或相当于 MySQL
2. 迁移后进行性能测试
3. 如有问题，优化索引和查询

**权衡**: PostgreSQL 的功能和稳定性值得这个小风险

### 风险 4: 开发环境配置复杂

**风险等级**: 低

**描述**:
- 开发者本地需要安装 PostgreSQL

**缓解措施**:
1. 提供详细的安装和配置文档
2. 提供 Docker Compose 配置，一键启动 PostgreSQL
3. 单元测试可以继续使用 SQLite

### 权衡: 维护多数据库支持 vs 统一到 PostgreSQL

**选择**: 统一到 PostgreSQL

**理由**:
- 简化代码和配置
- 减少测试矩阵（不需要同时测试 MySQL 和 PostgreSQL）
- 降低维护成本

**代价**:
- 失去数据库选择的灵活性
- 如果未来需要支持其他数据库，需要重新适配

**结论**: 在当前项目规模下，统一技术栈的好处大于灵活性的损失

## Migration Plan

### Phase 1: 准备和代码更新（2-3 天）

1. **环境准备**
   - 安装 `psycopg2-binary`
   - 验证 PostgreSQL 连接
   - 备份 MySQL 数据

2. **代码更新**
   - 更新 `requirements.txt`
   - 更新 `database.py` 配置
   - 修复 `db_models.py` 中的类型问题
   - 检查和修复原生 SQL 语句

3. **测试准备**
   - 更新测试配置
   - 编写迁移脚本
   - 编写验证脚本

### Phase 2: 测试环境迁移（1-2 天）

1. **数据库初始化**
   - 在 PostgreSQL 中创建表结构
   - 验证表结构正确性

2. **数据迁移**
   - 运行迁移脚本
   - 验证数据完整性
   - 修复发现的问题

3. **功能测试**
   - 运行所有自动化测试
   - 手动测试关键功能
   - 修复失败的测试用例

### Phase 3: 生产环境迁移（1 天）

1. **迁移执行**
   - 选择低峰时段
   - 停止应用服务（可选）
   - 执行数据迁移
   - 验证数据

2. **部署更新**
   - 更新环境变量
   - 部署新代码
   - 启动服务

3. **监控验证**
   - 验证关键功能
   - 监控性能和错误日志
   - 准备回滚方案

### Phase 4: 稳定和清理（1 周）

1. **持续监控**
   - 监控应用性能
   - 收集用户反馈
   - 修复可能的问题

2. **文档更新**
   - 更新项目文档
   - 记录迁移经验
   - 更新快速开始指南

3. **清理工作**
   - 确认迁移成功后，清理 MySQL 资源
   - 归档迁移脚本

### 回滚方案

如果迁移后发现严重问题:

1. **立即回滚**
   - 恢复旧版本代码
   - 修改环境变量指向 MySQL
   - 重启应用服务

2. **数据恢复**
   - 如果 PostgreSQL 中数据被修改，需要从 MySQL 备份恢复
   - 重新同步数据（如果有新数据产生）

3. **问题分析**
   - 分析失败原因
   - 修复问题
   - 重新规划迁移

## Open Questions

1. **PostgreSQL 版本**: 目标服务器的 PostgreSQL 版本是多少？（影响功能兼容性）
   - 建议: PostgreSQL 12+ （支持生成列、分区表等高级特性）

2. **连接池配置**: 当前 MySQL 的连接池配置是否适用于 PostgreSQL？
   - 当前配置: `pool_size=5, max_overflow=10`
   - 建议: 根据 PostgreSQL 服务器的 `max_connections` 设置调整

3. **字符集**: PostgreSQL 的字符集编码是什么？
   - MySQL 使用 `utf8mb4`
   - PostgreSQL 通常使用 `UTF8`
   - 需要确保字符集兼容

4. **SSL 连接**: 生产环境是否需要 SSL 连接？
   - 如需要，添加连接参数: `?sslmode=require`

5. **备份策略**: PostgreSQL 的备份策略是什么？
   - 建议: 使用 `pg_dump` 或 `pg_basebackup` 定期备份
   - 自动化备份脚本

6. **监控工具**: 是否有 PostgreSQL 监控工具？
   - 建议: pgAdmin, DataGrip, 或 Prometheus + postgres_exporter

7. **性能基准**: 是否需要建立性能基准以便对比？
   - 建议: 在迁移前后对比关键查询的性能

## SQL 语法差异对照表

| 功能 | MySQL | PostgreSQL | 兼容性 |
|------|-------|------------|--------|
| 字符串连接 | `CONCAT('a', 'b')` | `'a' \|\| 'b'` 或 `CONCAT('a', 'b')` | ✅ CONCAT 兼容 |
| 当前时间 | `NOW()` | `NOW()` 或 `CURRENT_TIMESTAMP` | ✅ 兼容 |
| 限制结果 | `LIMIT n OFFSET m` | `LIMIT n OFFSET m` | ✅ 完全兼容 |
| 自增 ID | `AUTO_INCREMENT` | `SERIAL` 或 `IDENTITY` | ⚠️ ORM 自动处理 |
| 布尔类型 | `TINYINT(1)` 或字符串 | `BOOLEAN` | ⚠️ 需要迁移 |
| 引号 | 反引号 `` `table` `` | 双引号 `"table"` | ⚠️ 避免使用 |
| JSON 查询 | `JSON_EXTRACT(col, '$.key')` | `col->>'key'` | ⚠️ 需要修改 |
| 日期格式化 | `DATE_FORMAT(date, '%Y-%m-%d')` | `TO_CHAR(date, 'YYYY-MM-DD')` | ⚠️ 需要修改 |
| 正则匹配 | `REGEXP` | `~` | ⚠️ 需要修改 |
| 大小写不敏感 | 默认不敏感 | 默认敏感 | ⚠️ 使用 `ILIKE` |

**注意**: 由于项目主要使用 SQLAlchemy ORM，大部分 SQL 语法由 ORM 生成，兼容性问题较少。重点检查原生 SQL 字符串。

## 数据类型映射

| SQLAlchemy 类型 | MySQL | PostgreSQL | 注意事项 |
|----------------|-------|------------|---------|
| `String(N)` | `VARCHAR(N)` | `VARCHAR(N)` | ✅ 兼容 |
| `Text` | `TEXT` | `TEXT` | ✅ 兼容 |
| `Integer` | `INT` | `INTEGER` | ✅ 兼容 |
| `Numeric(M, N)` | `DECIMAL(M, N)` | `NUMERIC(M, N)` | ✅ 兼容 |
| `DateTime` | `DATETIME` | `TIMESTAMP` | ✅ 兼容 |
| `JSON` | `JSON` | `JSONB` | ✅ PostgreSQL 更好 |
| `Boolean` | `TINYINT(1)` | `BOOLEAN` | ✅ 兼容 |
| `Enum` | `ENUM` | `ENUM` (自定义类型) | ✅ 兼容 |

**结论**: SQLAlchemy 的类型抽象层处理得很好，迁移风险较低。

