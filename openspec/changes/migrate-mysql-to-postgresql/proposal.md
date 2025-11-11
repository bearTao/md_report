# 数据库迁移提案: MySQL → PostgreSQL

## Why

当前项目使用 MySQL 作为主数据库，但在 AI 化过程中发现存在以下问题：

1. **运维成本问题**: 生产环境的主数据库是 PostgreSQL，如果继续使用 MySQL 会增加运维人力成本（需要维护两套数据库）
2. **适配性问题**: 生产环境统一使用 PostgreSQL，保持技术栈一致性可以减少维护复杂度
3. **功能完善性**: PostgreSQL 提供更强大的 JSON 支持、更完善的事务处理和更丰富的数据类型

因此，建议将所有模块的数据库从 MySQL 迁移到 PostgreSQL，统一使用生产环境的数据库技术栈。

## What Changes

### **BREAKING** 数据库引擎变更

- 将默认数据库从 MySQL 更改为 PostgreSQL
- 更新所有数据库连接配置
- 修改数据库驱动依赖（pymysql → psycopg2）
- 迁移现有 MySQL 数据到 PostgreSQL
- 修复 MySQL 和 PostgreSQL 之间的 SQL 语法差异

### 具体变更内容

1. **依赖包更新** (`requirements.txt`):
   - 移除: `pymysql==1.1.0`
   - 添加: `psycopg2-binary==2.9.9`（取消注释）

2. **数据库配置更新** (`app/database.py`):
   - 更新默认 `DATABASE_URL` 为 PostgreSQL 连接串
   - 移除 SQLite 特殊配置（仅用于开发测试）

3. **SQL 语法修复**:
   - 修复时间戳函数: `NOW()` → `CURRENT_TIMESTAMP`
   - 修复布尔类型: MySQL 的 `"true"`/`"false"` 字符串 → PostgreSQL 的 `TRUE`/`FALSE` 布尔值
   - 修复字符串连接: MySQL 的 `CONCAT()` → PostgreSQL 的 `||` 或 `CONCAT()`
   - 修复 LIMIT 语法差异
   - 修复自增 ID 处理差异

4. **ORM 模型调整** (`app/models/db_models.py`):
   - 验证所有字段类型与 PostgreSQL 兼容
   - 修复布尔字段类型（`is_active` 从字符串改为布尔）
   - 确保 JSON 字段兼容性
   - 调整枚举类型定义

5. **数据库连接器更新** (`app/connectors/database.py`):
   - 更新超时设置语法（MySQL 的 `max_execution_time` → PostgreSQL 的 `statement_timeout`）
   - 更新连接 URL 格式示例

6. **测试配置更新** (`tests/conftest.py`):
   - 更新测试数据库为 PostgreSQL
   - 或保留 SQLite 用于单元测试（性能考虑）

7. **数据迁移脚本**:
   - 创建数据导出脚本（从 MySQL 导出）
   - 创建数据导入脚本（导入到 PostgreSQL）
   - 创建数据验证脚本（确保迁移完整性）

8. **文档更新**:
   - 更新 `openspec/project.md` 中的技术栈说明
   - 更新快速开始指南中的数据库配置说明
   - 添加迁移操作指南

## Impact

### 影响的规范
- 暂无正式规范（`openspec/specs/` 为空）
- 但影响整个项目的数据库基础设施

### 影响的代码模块

#### 核心模块
- `backend/app/database.py` - 数据库连接配置
- `backend/app/models/db_models.py` - ORM 模型定义
- `backend/app/connectors/database.py` - 数据库连接器

#### API 模块
- `backend/app/api/config.py` - 配置 API
- `backend/app/api/reports.py` - 报告生成 API
- `backend/app/api/db_connections.py` - 数据库连接管理 API

#### 测试模块
- `backend/tests/conftest.py` - 测试配置
- `backend/tests/test_p1_features.py` - P1 功能测试

#### 迁移脚本
- `backend/migrate_template_fields.py`
- `backend/run_migration.py`
- `backend/check_enum.py`
- `backend/direct_alter.py`
- `backend/import_microgrid_data.py`
- `backend/import_microgrid_data_v2.py`
- `backend/generate_microgrid_report_direct.py`

#### 依赖配置
- `backend/requirements.txt` - Python 依赖包

### 停机时间
- 不需要渐进式迁移
- 可以计划维护窗口进行一次性迁移
- 建议在低峰时段执行

### 数据完整性
- 必须验证所有数据成功迁移
- 必须保持数据一致性（外键、约束等）
- 建议先在测试环境验证迁移流程

### 回滚策略
- 保留 MySQL 数据备份，直到确认迁移成功
- 可以快速切换回 MySQL（通过环境变量）
- 建议保留 MySQL 数据至少 1 周作为备份

### 风险评估
- **高风险**: 数据丢失或损坏 → 通过多轮验证降低风险
- **中风险**: SQL 语法兼容性问题 → 通过全面测试发现和修复
- **低风险**: 性能下降 → PostgreSQL 通常性能更好

