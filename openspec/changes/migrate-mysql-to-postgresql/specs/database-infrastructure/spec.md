# 数据库基础设施规范变更

## ADDED Requirements

### Requirement: PostgreSQL 数据库支持

系统 SHALL 使用 PostgreSQL 作为生产环境的主数据库管理系统。

#### Scenario: 数据库连接配置

- **WHEN** 应用启动时
- **THEN** 系统 SHALL 使用 PostgreSQL 数据库连接 URL
- **AND** 连接 URL 格式为 `postgresql://用户名:密码@主机:端口/数据库名`
- **AND** 默认连接信息为 `postgresql://microgrid:microgrid123@10.10.20.10:14632/new_md_agent`

#### Scenario: 数据库驱动依赖

- **WHEN** 安装项目依赖时
- **THEN** 系统 SHALL 包含 `psycopg2-binary` 包作为 PostgreSQL 驱动
- **AND** 版本号为 2.9.9 或更高兼容版本

#### Scenario: 连接池配置

- **WHEN** 创建数据库引擎时
- **THEN** 系统 SHALL 配置以下连接池参数:
  - `pool_size`: 5 (默认保持 5 个连接)
  - `max_overflow`: 10 (最大溢出连接数)
  - `pool_pre_ping`: True (连接健康检查)
  - `pool_recycle`: 3600 (连接回收时间 1 小时)
  - `pool_timeout`: 30 (获取连接超时 30 秒)

### Requirement: 布尔类型字段支持

系统 SHALL 使用原生布尔类型存储布尔值，而不是字符串模拟。

#### Scenario: 布尔字段定义

- **WHEN** 定义布尔类型的数据库字段时
- **THEN** 系统 SHALL 使用 SQLAlchemy 的 `Boolean` 类型
- **AND** PostgreSQL 中映射为 `BOOLEAN` 类型
- **AND** 值为 `TRUE` 或 `FALSE`，而不是字符串 `"true"` 或 `"false"`

#### Scenario: 布尔字段查询

- **WHEN** 查询布尔类型字段时
- **THEN** 系统 SHALL 使用布尔值 `True` 或 `False` 进行比较
- **AND** 不使用字符串 `"true"` 或 `"false"`

### Requirement: SQL 查询超时设置

系统 SHALL 支持为 SQL 查询设置超时时间，防止长时间运行的查询阻塞系统。

#### Scenario: PostgreSQL 查询超时

- **WHEN** 执行 SQL 查询时
- **AND** 数据库类型为 PostgreSQL
- **THEN** 系统 SHALL 使用 `SET statement_timeout = N` 设置超时（N 为毫秒）
- **AND** 默认超时时间为 10 秒（10000 毫秒）

#### Scenario: 查询超时可配置

- **WHEN** 执行 SQL 查询时
- **THEN** 系统 SHALL 允许在变量元数据中配置 `timeout` 参数
- **AND** 超时时间以秒为单位
- **AND** 自动转换为数据库特定的超时设置语法

### Requirement: JSON 字段支持

系统 SHALL 支持存储和查询 JSON 格式的数据。

#### Scenario: JSON 字段定义

- **WHEN** 定义 JSON 类型的数据库字段时
- **THEN** 系统 SHALL 使用 SQLAlchemy 的 `JSON` 类型
- **AND** PostgreSQL 中映射为 `JSONB` 类型（支持索引和高效查询）

#### Scenario: JSON 数据存储和查询

- **WHEN** 存储 JSON 数据时
- **THEN** 系统 SHALL 自动序列化 Python 字典或列表为 JSON
- **WHEN** 查询 JSON 数据时
- **THEN** 系统 SHALL 自动反序列化 JSON 为 Python 对象

### Requirement: 数据类型兼容性

系统 SHALL 正确处理所有数据类型的转换和序列化。

#### Scenario: 日期时间类型

- **WHEN** 查询返回日期或时间类型数据时
- **THEN** 系统 SHALL 自动转换为 ISO 8601 格式字符串（如 `2024-01-01T12:00:00`）
- **AND** 支持 `datetime` 和 `date` 类型

#### Scenario: 数值类型

- **WHEN** 查询返回 `NUMERIC` 或 `DECIMAL` 类型数据时
- **THEN** 系统 SHALL 自动转换为 Python `float` 类型
- **AND** 保持数值精度

#### Scenario: 字节类型

- **WHEN** 查询返回 `bytes` 类型数据时
- **THEN** 系统 SHALL 自动解码为 UTF-8 字符串
- **AND** 如果解码失败，使用 `errors='ignore'` 忽略错误字符

### Requirement: 数据库连接管理

系统 SHALL 支持管理多个数据库连接配置，用于 SQL 变量数据源。

#### Scenario: 连接信息存储

- **WHEN** 用户创建数据库连接配置时
- **THEN** 系统 SHALL 存储以下信息:
  - 连接名称（唯一标识）
  - 数据库引擎类型（postgresql, mysql, sqlserver, oracle）
  - 主机地址
  - 端口号
  - 数据库名
  - 用户名
  - 密码（加密存储）
  - 额外选项（JSON 格式）

#### Scenario: 支持的数据库引擎

- **WHEN** 用户配置数据库连接时
- **THEN** 系统 SHALL 支持以下数据库引擎:
  - `postgresql`: PostgreSQL
  - `mysql`: MySQL / MariaDB
  - `sqlserver`: Microsoft SQL Server
  - `oracle`: Oracle Database

## MODIFIED Requirements

### Requirement: 环境变量配置

系统 SHALL 通过环境变量 `DATABASE_URL` 配置主数据库连接，支持灵活的部署环境。

**（此需求已存在，但内容更新以反映 PostgreSQL）**

#### Scenario: 默认数据库连接

- **WHEN** 环境变量 `DATABASE_URL` 未设置时
- **THEN** 系统 SHALL 使用默认的 PostgreSQL 连接字符串
- **AND** 默认值为 `postgresql://microgrid:microgrid123@10.10.20.10:14632/new_md_agent`

#### Scenario: 自定义数据库连接

- **WHEN** 环境变量 `DATABASE_URL` 已设置时
- **THEN** 系统 SHALL 使用该环境变量的值作为数据库连接字符串
- **AND** 支持任何 SQLAlchemy 兼容的连接 URL 格式

#### Scenario: 测试环境数据库

- **WHEN** 运行单元测试时
- **THEN** 系统 MAY 使用 SQLite 内存数据库以提高测试速度
- **WHEN** 运行集成测试时
- **THEN** 系统 SHALL 使用 PostgreSQL 测试数据库以确保兼容性

## REMOVED Requirements

### Requirement: MySQL 数据库支持

**Reason**: 迁移到 PostgreSQL，不再支持 MySQL 作为主数据库

**Migration**: 
- 所有现有 MySQL 数据将迁移到 PostgreSQL
- 如果用户的 SQL 变量数据源使用 MySQL，仍然支持（通过数据库连接器）
- 但系统的主数据库（存储模板、报告、任务等）将使用 PostgreSQL

**历史背景**:
- MySQL 连接 URL 格式: `mysql+pymysql://用户名:密码@主机:端口/数据库名?charset=utf8mb4`
- 使用 `pymysql` 驱动（版本 1.1.0）
- 默认连接: `mysql+pymysql://root:123456@10.10.20.10:24406/md_agent?charset=utf8mb4`

#### 原 Scenario: MySQL 查询超时设置

- **WHEN** 执行 SQL 查询时
- **AND** 数据库类型为 MySQL
- **THEN** 系统使用 `SET SESSION max_execution_time = N` 设置超时（N 为毫秒）

**注**: 此功能不再用于主数据库，但在数据库连接器中仍保留，用于连接外部 MySQL 数据源

### Requirement: 布尔字段的字符串存储

**Reason**: PostgreSQL 支持原生布尔类型，无需使用字符串模拟

**Migration**:
- 数据迁移时，将字符串 `"true"` 转换为布尔值 `TRUE`
- 将字符串 `"false"` 转换为布尔值 `FALSE`
- 更新代码中所有布尔字段的比较逻辑

**历史背景**:
- MySQL 没有真正的布尔类型，使用 `TINYINT(1)` 或 `VARCHAR`
- 项目中 `DBConnection.is_active` 字段使用字符串 `"true"`/`"false"` 存储
- 查询时使用字符串比较: `is_active == "true"`

**新实现**:
- PostgreSQL 使用 `BOOLEAN` 类型
- Python 代码使用布尔值: `is_active = True`
- 查询时使用布尔比较: `is_active == True` 或 `is_active is True`

