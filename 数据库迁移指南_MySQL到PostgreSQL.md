# 数据库迁移指南: MySQL → PostgreSQL

## 概述

本指南帮助你将项目数据库从 MySQL 迁移到 PostgreSQL。

### 迁移原因

1. **降低运维成本**: 生产环境主数据库是 PostgreSQL，统一技术栈可减少维护负担
2. **技术栈一致性**: 避免维护多套数据库系统
3. **功能优势**: PostgreSQL 提供更强大的 JSON 支持、更完善的事务处理

### 目标环境

- **数据库**: PostgreSQL
- **主机**: 10.10.20.10
- **端口**: 14632
- **数据库名**: new_md_agent
- **用户名**: microgrid
- **密码**: microgrid123

## 前置条件

### 1. 安装 PostgreSQL 客户端（可选，用于手动操作）

```bash
# Ubuntu/Debian
sudo apt-get install postgresql-client

# macOS
brew install postgresql
```

### 2. 验证 PostgreSQL 连接

```bash
psql -h 10.10.20.10 -p 14632 -U microgrid -d new_md_agent
# 输入密码: microgrid123
```

如果连接成功，输入 `\q` 退出。

## 迁移步骤

### 阶段 1: 准备工作

#### 1.1 备份当前 MySQL 数据（重要！）

```bash
cd backend

# 使用脚本导出数据
python export_mysql_data.py

# 导出结果保存在 mysql_export/ 目录
# 包含所有表的 JSON 文件和统计信息
```

或使用 mysqldump 备份:

```bash
mysqldump -h 10.10.20.10 -P 24406 -u root -p123456 md_agent > md_agent_backup_$(date +%Y%m%d).sql
```

#### 1.2 更新 Python 依赖

编辑 `backend/requirements.txt`:

```diff
# Database
sqlalchemy==2.0.44
-# psycopg2-binary==2.9.9
-pymysql==1.1.0
+psycopg2-binary==2.9.9
+# pymysql==1.1.0  # 不再作为主数据库，但保留用于连接外部 MySQL
alembic==1.13.1
```

安装新依赖:

```bash
cd backend
pip install -r requirements.txt
```

验证安装:

```bash
python -c "import psycopg2; print('psycopg2 version:', psycopg2.__version__)"
```

### 阶段 2: 代码更新

#### 2.1 更新数据库配置

编辑 `backend/app/database.py`:

```python
# 从环境变量获取数据库URL，如果未设置则使用默认的PostgreSQL连接
# PostgreSQL连接格式: postgresql://用户名:密码@主机:端口/数据库名
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://microgrid:microgrid123@10.10.20.10:14632/new_md_agent"
)
```

**注意**: 移除原来的 MySQL 默认连接。

#### 2.2 修复布尔字段类型

编辑 `backend/app/models/db_models.py`:

找到 `DBConnection` 模型，修改 `is_active` 字段:

```python
class DBConnection(Base):
    """Database connection configurations"""
    __tablename__ = "db_connections"
    
    # ... 其他字段 ...
    
    # 修改前:
    # is_active = Column(String(10), default="true")
    
    # 修改后:
    is_active = Column(Boolean, default=True)  # 使用真正的布尔类型
```

#### 2.3 更新项目文档

编辑 `openspec/project.md`:

```diff
### 后端
- **Python 3.11+** - 编程语言
- **FastAPI 0.109** - Web框架
- **Uvicorn** - ASGI服务器
- **SQLAlchemy 2.0** - ORM
-- **MySQL** - 生产数据库,需要迁移至pgsql（开发环境使用SQLite）
-- **PyMySQL** - MySQL驱动
+- **PostgreSQL** - 生产数据库
+- **psycopg2** - PostgreSQL驱动
- **Jinja2 3.1** - 模板引擎
```

### 阶段 3: 数据迁移

#### 3.1 在 PostgreSQL 中创建表结构

```bash
cd backend

# 方法 1: 使用 SQLAlchemy 自动创建（推荐）
python -c "from app.database import init_db; init_db(); print('Tables created successfully')"

# 方法 2: 使用 Alembic 迁移（如果配置了）
# alembic upgrade head
```

验证表结构:

```bash
psql -h 10.10.20.10 -p 14632 -U microgrid -d new_md_agent -c "\dt"
```

#### 3.2 导入数据

```bash
cd backend

# 运行导入脚本
python import_to_postgresql.py

# 查看导入统计: mysql_export/_import_stats.json
```

#### 3.3 验证数据完整性

```bash
cd backend

# 运行验证脚本（对比 MySQL 和 PostgreSQL 的数据）
python verify_migration.py

# 如果所有表都显示 ✅，说明迁移成功
```

### 阶段 4: 测试验证

#### 4.1 运行自动化测试

```bash
cd backend

# 更新测试环境变量（可选，或在 tests/conftest.py 中修改）
export DATABASE_URL="postgresql://microgrid:microgrid123@10.10.20.10:14632/new_md_agent"

# 运行所有测试
pytest tests/ -v

# 如果有失败的测试，检查并修复
```

#### 4.2 启动应用进行手动测试

```bash
cd backend

# 设置环境变量（或在 .env 文件中配置）
export DATABASE_URL="postgresql://microgrid:microgrid123@10.10.20.10:14632/new_md_agent"

# 启动后端
uvicorn app.main:app --reload
```

测试以下关键功能:

- [ ] 创建和查询模板
- [ ] 生成报告
- [ ] 查询报告历史
- [ ] 管理数据库连接配置
- [ ] 测试 SQL 变量（重点测试）
- [ ] 测试 AI 配置保存

#### 4.3 测试 SQL 变量功能

由于 SQL 变量会直接查询数据库，需要重点测试:

1. 创建一个包含 SQL 变量的模板
2. 配置不同类型的数据库连接（PostgreSQL, MySQL）
3. 测试查询结果的正确性
4. 测试超时设置

### 阶段 5: 生产部署

#### 5.1 设置环境变量

在生产服务器上设置环境变量（根据部署方式选择）:

**方法 1: .env 文件**

```bash
# backend/.env
DATABASE_URL=postgresql://microgrid:microgrid123@10.10.20.10:14632/new_md_agent
```

**方法 2: 系统环境变量**

```bash
# 添加到 ~/.bashrc 或 systemd 配置
export DATABASE_URL="postgresql://microgrid:microgrid123@10.10.20.10:14632/new_md_agent"
```

**方法 3: Docker 环境变量**

```yaml
# docker-compose.yml
environment:
  - DATABASE_URL=postgresql://microgrid:microgrid123@10.10.20.10:14632/new_md_agent
```

#### 5.2 部署更新的代码

```bash
# 拉取最新代码
git pull

# 安装依赖
cd backend
pip install -r requirements.txt

# 重启服务（根据部署方式）
# systemd:
sudo systemctl restart xuqiu-backend

# supervisor:
supervisorctl restart xuqiu-backend

# docker:
docker-compose restart backend
```

#### 5.3 监控和验证

1. **检查应用日志**:
   ```bash
   # 查看最近的日志
   tail -f logs/app.log
   
   # 或使用 journalctl（systemd）
   sudo journalctl -u xuqiu-backend -f
   ```

2. **验证数据库连接**:
   ```bash
   # 检查数据库连接数
   psql -h 10.10.20.10 -p 14632 -U microgrid -d new_md_agent \
        -c "SELECT count(*) FROM pg_stat_activity WHERE datname='new_md_agent';"
   ```

3. **测试关键功能**: 通过前端界面或 API 测试所有关键功能

### 阶段 6: 清理和归档

#### 6.1 保留 MySQL 备份（1 周）

在确认迁移成功后，保留 MySQL 数据至少 1 周作为备份:

```bash
# 保持 MySQL 数据库运行，但不再主动使用
# mysql_export/ 目录保留作为备份
```

#### 6.2 更新文档

- [x] `openspec/project.md` - 技术栈说明
- [x] `快速开始.md` - 数据库配置说明
- [x] 添加本迁移指南

#### 6.3 归档迁移脚本

迁移脚本保留在代码库中，供参考:

- `backend/export_mysql_data.py` - MySQL 导出脚本
- `backend/import_to_postgresql.py` - PostgreSQL 导入脚本
- `backend/verify_migration.py` - 数据验证脚本

## 回滚方案

如果迁移后发现严重问题，可以快速回滚:

### 1. 恢复代码

```bash
git checkout <之前的commit>
```

### 2. 恢复数据库配置

```bash
# 修改环境变量指向 MySQL
export DATABASE_URL="mysql+pymysql://root:123456@10.10.20.10:24406/md_agent?charset=utf8mb4"
```

### 3. 重启服务

```bash
sudo systemctl restart xuqiu-backend
```

### 4. 验证服务正常

检查日志和测试关键功能。

## 常见问题

### Q1: psycopg2 安装失败

**问题**: `pip install psycopg2-binary` 失败

**解决**:
```bash
# 安装依赖
sudo apt-get install libpq-dev python3-dev

# 或使用预编译版本
pip install psycopg2-binary --only-binary :all:
```

### Q2: 数据库连接失败

**问题**: `psycopg2.OperationalError: could not connect to server`

**检查**:
1. PostgreSQL 服务是否运行
2. 防火墙是否允许连接
3. 连接信息是否正确
4. 用户权限是否足够

```bash
# 测试连接
psql -h 10.10.20.10 -p 14632 -U microgrid -d new_md_agent
```

### Q3: 导入数据后行数不匹配

**问题**: `verify_migration.py` 显示行数不匹配

**排查**:
1. 检查导入日志 `mysql_export/_import_stats.json`
2. 查看是否有错误信息
3. 手动对比具体表的数据

```sql
-- MySQL
SELECT COUNT(*) FROM table_name;

-- PostgreSQL
SELECT COUNT(*) FROM table_name;
```

### Q4: 布尔字段查询错误

**问题**: 查询 `is_active` 字段报错或返回错误结果

**原因**: 代码中还在使用字符串比较

**修复**:
```python
# 错误
db.query(DBConnection).filter(DBConnection.is_active == "true")

# 正确
db.query(DBConnection).filter(DBConnection.is_active == True)
# 或
db.query(DBConnection).filter(DBConnection.is_active.is_(True))
```

### Q5: SQL 语法错误

**问题**: 原生 SQL 查询失败，提示语法错误

**常见差异**:

| 功能 | MySQL | PostgreSQL |
|------|-------|------------|
| 限制结果 | `LIMIT n` | `LIMIT n` ✅ 兼容 |
| 当前时间 | `NOW()` | `NOW()` ✅ 兼容 |
| 字符串连接 | `CONCAT('a', 'b')` | `CONCAT('a', 'b')` 或 `'a' \|\| 'b'` ✅ 兼容 |
| JSON 提取 | `JSON_EXTRACT(col, '$.key')` | `col->>'key'` ⚠️ 不同 |
| 正则匹配 | `REGEXP 'pattern'` | `~ 'pattern'` ⚠️ 不同 |
| 大小写不敏感 | `LIKE '%value%'` | `ILIKE '%value%'` ⚠️ 不同 |

### Q6: 枚举类型错误

**问题**: 插入数据时提示枚举值无效

**原因**: PostgreSQL 的枚举类型更严格

**解决**: 确保插入的值在枚举定义中

```python
# 检查枚举定义
class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

# 确保插入的值是枚举成员
task.status = ReportStatus.PENDING.value  # "pending"
```

## MySQL 和 PostgreSQL 差异对照

### 数据类型映射

| SQLAlchemy | MySQL | PostgreSQL | 兼容性 |
|-----------|-------|------------|--------|
| `String(N)` | `VARCHAR(N)` | `VARCHAR(N)` | ✅ |
| `Text` | `TEXT` | `TEXT` | ✅ |
| `Integer` | `INT` | `INTEGER` | ✅ |
| `Numeric(M,N)` | `DECIMAL(M,N)` | `NUMERIC(M,N)` | ✅ |
| `DateTime` | `DATETIME` | `TIMESTAMP` | ✅ |
| `JSON` | `JSON` | `JSONB` | ✅ |
| `Boolean` | `TINYINT(1)` | `BOOLEAN` | ⚠️ |
| `Enum` | `ENUM` | `ENUM(自定义类型)` | ✅ |

### 连接 URL 格式

```python
# MySQL
"mysql+pymysql://用户名:密码@主机:端口/数据库名?charset=utf8mb4"

# PostgreSQL
"postgresql://用户名:密码@主机:端口/数据库名"

# PostgreSQL with SSL
"postgresql://用户名:密码@主机:端口/数据库名?sslmode=require"
```

### 超时设置

```python
# MySQL
conn.execute(text("SET SESSION max_execution_time = 30000"))  # 毫秒

# PostgreSQL
conn.execute(text("SET statement_timeout = 30000"))  # 毫秒
```

## 性能优化建议

迁移到 PostgreSQL 后，可以考虑以下优化:

### 1. 添加索引

```sql
-- 为常用查询字段添加索引
CREATE INDEX idx_task_status ON generation_tasks(status);
CREATE INDEX idx_task_created ON generation_tasks(created_at);
CREATE INDEX idx_report_template ON reports(template_id);
```

### 2. 启用查询分析

```sql
-- 分析查询性能
EXPLAIN ANALYZE SELECT * FROM generation_tasks WHERE status = 'running';
```

### 3. 定期维护

```sql
-- 更新统计信息
ANALYZE;

-- 清理死元组
VACUUM;

-- 或自动维护
VACUUM ANALYZE;
```

### 4. 配置连接池

根据实际负载调整连接池参数:

```python
# backend/app/database.py
engine_kwargs = {
    "pool_size": 10,        # 增加连接池大小（如果负载高）
    "max_overflow": 20,     # 增加最大溢出
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}
```

## 监控和告警

### 1. 数据库连接监控

```sql
-- 查看当前活跃连接
SELECT * FROM pg_stat_activity WHERE datname = 'new_md_agent';

-- 查看连接数
SELECT count(*) FROM pg_stat_activity WHERE datname = 'new_md_agent';
```

### 2. 慢查询监控

```sql
-- 启用慢查询日志（postgresql.conf）
log_min_duration_statement = 1000  # 记录超过1秒的查询

-- 查看慢查询
SELECT * FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
```

### 3. 应用监控

在应用日志中记录数据库操作:

```python
# 启用 SQLAlchemy 日志
engine = create_engine(DATABASE_URL, echo=True)  # 开发环境
```

## 参考资源

- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [psycopg2 文档](https://www.psycopg.org/docs/)
- [MySQL to PostgreSQL 迁移指南](https://wiki.postgresql.org/wiki/Converting_from_other_Databases_to_PostgreSQL)

## 联系支持

如果在迁移过程中遇到问题:

1. 查看本指南的"常见问题"部分
2. 检查应用日志 `backend/logs/app.log`
3. 查看 OpenSpec 提案 `openspec/changes/migrate-mysql-to-postgresql/`

## 版本历史

- **2025-11-10**: 初始版本，完成迁移提案和脚本

