# 数据库迁移提案: MySQL → PostgreSQL

## 快速概览

本提案将项目的主数据库从 MySQL 迁移到 PostgreSQL，以统一生产环境的技术栈，降低运维成本。

## 提案文件

- **proposal.md** - 迁移提案（为什么迁移、影响范围）
- **design.md** - 技术设计（决策、风险、迁移计划）
- **tasks.md** - 实施任务清单（共 8 个阶段，31 个子任务）
- **specs/database-infrastructure/spec.md** - 数据库基础设施规范变更

## 关键信息

### 目标数据库
- **主机**: 10.10.20.10
- **端口**: 14632
- **数据库**: new_md_agent
- **用户**: microgrid
- **密码**: microgrid123

### 主要变更
1. ✅ 更新数据库驱动: `pymysql` → `psycopg2-binary`
2. ✅ 更新数据库配置: MySQL URL → PostgreSQL URL
3. ✅ 修复布尔字段类型: 字符串 → 真正的布尔值
4. ✅ 迁移所有现有数据
5. ✅ 修复 SQL 语法兼容性问题

## 快速开始

### 1. 查看详细迁移指南

```bash
cat 数据库迁移指南_MySQL到PostgreSQL.md
```

### 2. 备份 MySQL 数据

```bash
cd backend
python export_mysql_data.py
```

### 3. 更新依赖

```bash
# 编辑 requirements.txt
# 取消注释: psycopg2-binary==2.9.9
# 注释: pymysql==1.1.0

pip install -r requirements.txt
```

### 4. 更新代码

编辑 `backend/app/database.py`:

```python
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://microgrid:microgrid123@10.10.20.10:14632/new_md_agent"
)
```

编辑 `backend/app/models/db_models.py`:

```python
# DBConnection 模型
is_active = Column(Boolean, default=True)  # 从 String 改为 Boolean
```

### 5. 创建表结构

```bash
cd backend
python -c "from app.database import init_db; init_db()"
```

### 6. 导入数据

```bash
cd backend
python import_to_postgresql.py
```

### 7. 验证数据

```bash
cd backend
python verify_migration.py
```

### 8. 测试

```bash
cd backend
pytest tests/ -v
```

## 验证提案

```bash
# 验证提案格式
openspec validate migrate-mysql-to-postgresql --strict

# 查看提案详情
openspec show migrate-mysql-to-postgresql

# 查看任务列表
openspec list
```

## 迁移脚本

项目包含以下迁移辅助脚本:

1. **export_mysql_data.py** - 从 MySQL 导出数据为 JSON
   - 自动导出所有表
   - 记录导出统计信息
   - 保存到 `mysql_export/` 目录

2. **import_to_postgresql.py** - 导入数据到 PostgreSQL
   - 读取导出的 JSON 文件
   - 自动转换布尔字段
   - 重置序列（自增 ID）
   - 验证导入行数

3. **verify_migration.py** - 验证数据完整性
   - 对比 MySQL 和 PostgreSQL 的表结构
   - 对比每个表的行数
   - 生成验证报告

## 影响范围

### 核心文件
- `backend/requirements.txt` - 依赖包
- `backend/app/database.py` - 数据库配置
- `backend/app/models/db_models.py` - ORM 模型
- `backend/app/connectors/database.py` - 连接器（已兼容）
- `backend/tests/conftest.py` - 测试配置
- `openspec/project.md` - 项目文档

### API 模块（无需修改）
- `backend/app/api/config.py`
- `backend/app/api/reports.py`
- `backend/app/api/db_connections.py`

由于使用 SQLAlchemy ORM，大部分代码无需修改。

## 时间估算

- **准备和代码更新**: 2-3 天
- **测试环境迁移**: 1-2 天
- **生产环境迁移**: 1 天
- **稳定和清理**: 1 周

**总计**: 约 1-2 周

## 风险控制

### 高风险
- ❌ 数据丢失或损坏
- ✅ 缓解: 完整备份 + 多轮验证

### 中风险
- ⚠️ SQL 语法兼容性问题
- ✅ 缓解: 全面测试 + 使用 ORM

### 低风险
- ✅ 性能下降
- ✅ 缓解: PostgreSQL 性能通常更好

## 回滚方案

如果迁移失败，可以快速回滚:

1. 恢复代码到迁移前版本
2. 修改环境变量指向 MySQL
3. 重启服务

MySQL 数据保留至少 1 周作为备份。

## 下一步

1. ✅ 提案已创建并验证通过
2. ⏳ **等待审批** - 请团队 review 提案
3. ⏳ 审批通过后，开始实施 `tasks.md` 中的任务
4. ⏳ 完成后归档提案: `openspec archive migrate-mysql-to-postgresql`

## 文档

- **详细迁移指南**: `数据库迁移指南_MySQL到PostgreSQL.md`（项目根目录）
- **OpenSpec 工作流**: `openspec/AGENTS.md`
- **项目规范**: `openspec/project.md`

## 联系

如有问题，请查看:
1. 提案中的 `design.md` - 技术决策和风险分析
2. 迁移指南中的"常见问题"部分
3. 提案中的 `proposal.md` - 影响范围和变更说明

---

**状态**: ✅ 提案已创建，等待审批

**创建日期**: 2025-11-10

**验证**: `openspec validate migrate-mysql-to-postgresql --strict` ✅ 通过

