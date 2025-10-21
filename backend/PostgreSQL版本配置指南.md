# PostgreSQL版本微网格预分析配置指南

## 概述

本指南帮助您将微网格预分析系统配置为使用PostgreSQL数据库（生产环境推荐）。

## 前置条件

- PostgreSQL数据库服务器（版本 12+）
- 数据库连接信息：
  - 主机: `10.10.20.10`
  - 端口: `14632`
  - 数据库: `microgrid`
  - 用户名和密码

## 配置步骤

### 方案1: 使用配置脚本（推荐）

#### 1.1 修改配置参数

编辑 `setup_postgresql_microgrid.py` 文件的配置区：

```python
PG_HOST = "10.10.20.10"
PG_PORT = 14632
PG_DATABASE = "microgrid"
PG_USERNAME = "postgres"        # ⚠️ 修改为实际用户名
PG_PASSWORD = "your_password"   # ⚠️ 修改为实际密码
```

#### 1.2 运行配置脚本

```bash
cd /data/tao/code/xuqiu/backend
python setup_postgresql_microgrid.py
```

脚本会自动：
1. ✅ 测试PostgreSQL连接
2. ✅ 导入SQL数据（可选）
3. ✅ 注册数据库连接配置
4. ✅ 测试查询功能

---

### 方案2: 手动配置

#### 2.1 导入数据到PostgreSQL

```bash
# 使用psql命令行工具
psql -h 10.10.20.10 -p 14632 -U postgres -d microgrid -f /data/tao/code/xuqiu/tmp/预分析报告建表语句及测试数据.sql

# 或使用Python脚本
python -c "
from sqlalchemy import create_engine, text

pg_url = 'postgresql://USERNAME:PASSWORD@10.10.20.10:14632/microgrid'
engine = create_engine(pg_url)

with open('/data/tao/code/xuqiu/tmp/预分析报告建表语句及测试数据.sql', 'r') as f:
    sql = f.read()

with engine.connect() as conn:
    conn.execute(text(sql))
    conn.commit()
    print('数据导入完成')
"
```

#### 2.2 注册数据库连接

```python
from app.database import SessionLocal
from app.models.db_models import DBConnection, DBEngineType

db = SessionLocal()

# 创建PostgreSQL连接配置
pg_conn = DBConnection(
    name="microgrid_db_pg",
    engine=DBEngineType.POSTGRESQL,
    host="10.10.20.10",
    port=14632,
    database="microgrid",
    username="your_username",          # ⚠️ 修改
    password_ciphertext="your_password", # ⚠️ 修改
    is_active="true",
    description="PostgreSQL版本微网格预分析数据库"
)

db.add(pg_conn)
db.commit()
db.close()

print("✅ PostgreSQL连接已注册")
```

#### 2.3 验证连接

```python
from app.connectors.database import db_connector
from sqlalchemy import create_engine
import asyncio

pg_url = "postgresql://USERNAME:PASSWORD@10.10.20.10:14632/microgrid"
engine = create_engine(pg_url)
db_connector.register_connection("microgrid_db_pg", engine)

async def test():
    result = await db_connector.execute_query(
        connection_name="microgrid_db_pg",
        query="SELECT COUNT(*) as total FROM micro_grid_overview_w",
        timeout=10
    )
    print(f"总记录数: {result[0]['total']}")

asyncio.run(test())
```

---

## 创建PostgreSQL版本模板

### 方法1: 通过API复制并修改模板

```python
import requests
import json

# 1. 获取现有MySQL模板
response = requests.get("http://localhost:8000/api/templates/tpl_21c2afbe565c")
mysql_template = response.json()

# 2. 修改连接配置
metadata = mysql_template['metadata_json']

for var_name, var_config in metadata.items():
    if var_config.get('source') == 'sql':
        sql_config = var_config.get('sql_config', {})
        if sql_config.get('connection') == 'microgrid_db':
            sql_config['connection'] = 'microgrid_db_pg'  # 改为PostgreSQL连接

# 3. 创建新模板
new_template = {
    'name': '微网格预分析-PostgreSQL版',
    'description': 'PostgreSQL版本的微网格预分析报告（生产环境）',
    'template_content': mysql_template['template_content'],
    'metadata_json': metadata
}

response = requests.post(
    "http://localhost:8000/api/templates",
    headers={'Content-Type': 'application/json'},
    json=new_template
)

if response.status_code == 200:
    new_template_data = response.json()
    print(f"✅ PostgreSQL模板创建成功！")
    print(f"   模板ID: {new_template_data['id']}")
    print(f"   模板名称: {new_template_data['name']}")
else:
    print(f"❌ 创建失败: {response.text}")
```

### 方法2: 手动在管理界面创建

1. 登录管理界面
2. 复制"微网格预分析"模板
3. 修改名称为"微网格预分析-PostgreSQL版"
4. 在变量元数据JSON中，查找所有 `"connection": "microgrid_db"`
5. 替换为 `"connection": "microgrid_db_pg"`
6. 保存模板

---

## 使用PostgreSQL模板生成报告

### 通过API

```bash
curl -X POST "http://localhost:8000/api/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "tpl_xxx_postgresql",
    "inputs": {"wgid": "ZQGY0174"}
  }'
```

### 通过前端

1. 选择"微网格预分析-PostgreSQL版"模板
2. 输入微网格ID: `ZQGY0174`
3. 点击"生成报告"

---

## MySQL vs PostgreSQL 对比

| 特性 | MySQL | PostgreSQL |
|-----|-------|------------|
| **当前状态** | ✅ 已配置 | ⚠️ 需配置 |
| **连接名** | `microgrid_db` | `microgrid_db_pg` |
| **数据库地址** | 10.10.20.10:24406 | 10.10.20.10:14632 |
| **数据格式** | MySQL | PostgreSQL |
| **使用场景** | 开发/测试 | 生产环境 |
| **优势** | 已有数据 | 原始数据源 |

---

## 数据库差异处理

### 字段类型映射

PostgreSQL → MySQL 的主要差异已在代码中处理：

| PostgreSQL | MySQL | 处理方式 |
|-----------|-------|---------|
| `int8` | `BIGINT` | 自动映射 |
| `numeric(28,6)` | `DECIMAL(28,6)` | 自动映射 |
| `timestamp` | `DATETIME` | 转换为ISO字符串 |
| `varchar` | `VARCHAR` | 无需转换 |

### JSON序列化

所有datetime和Decimal类型都会自动转换为JSON兼容格式：
- `datetime` → ISO 8601字符串
- `Decimal` → float

---

## 故障排查

### 问题1: 无法连接PostgreSQL

**症状:**
```
connection to server at "10.10.20.10", port 14632 failed: FATAL: password authentication failed
```

**解决方案:**
1. 检查用户名和密码是否正确
2. 检查PostgreSQL的 `pg_hba.conf` 配置
3. 确认防火墙规则允许连接
4. 验证数据库和用户是否存在

```sql
-- 在PostgreSQL中检查
SELECT usename FROM pg_user;  -- 查看用户
\l                             -- 查看数据库列表
```

### 问题2: 表不存在

**症状:**
```
relation "micro_grid_overview_w" does not exist
```

**解决方案:**
1. 检查是否已导入SQL文件
2. 确认表是在正确的schema中（默认是public）

```sql
-- 检查表是否存在
SELECT tablename FROM pg_tables WHERE schemaname = 'public';

-- 查看特定表
\d micro_grid_overview_w
```

### 问题3: 数据为空

**症状:**
模板渲染失败，变量为None

**解决方案:**
1. 检查wgid是否存在于数据库中
2. 验证SQL查询是否正确

```sql
-- 检查数据
SELECT COUNT(*) FROM micro_grid_overview_w;
SELECT wgid FROM micro_grid_overview_w LIMIT 10;
```

---

## 性能优化建议

### 1. 创建索引

```sql
-- 为常用查询字段创建索引
CREATE INDEX idx_overview_wgid ON micro_grid_overview_w(wgid);
CREATE INDEX idx_overview_endtime ON micro_grid_overview_w(endtime);

CREATE INDEX idx_problem_build_wgid ON micro_grid_problem_build_m(wgid);
CREATE INDEX idx_problem_grid_mdt_wgid ON micro_grid_problem_grid_mdt_m(wgid);
CREATE INDEX idx_problem_grid_cloud_wgid ON micro_grid_problem_grid_cloud_m(wgid);
```

### 2. 连接池配置

```python
# 在注册连接时配置连接池
db_connector.register_connection(
    name="microgrid_db_pg",
    connection_url_or_engine=pg_url,
    pool_size=10,        # 连接池大小
    max_overflow=20      # 最大溢出连接数
)
```

### 3. 查询优化

```sql
-- 使用EXPLAIN分析查询性能
EXPLAIN ANALYZE 
SELECT * FROM micro_grid_overview_w 
WHERE wgid = 'ZQGY0174' 
ORDER BY endtime DESC 
LIMIT 1;
```

---

## 安全建议

### 1. 密码加密

生产环境中应加密存储数据库密码：

```python
from cryptography.fernet import Fernet

# 生成密钥（仅一次）
key = Fernet.generate_key()

# 加密密码
cipher = Fernet(key)
encrypted_password = cipher.encrypt(b"your_password")

# 存储encrypted_password到数据库
# 使用时解密
decrypted_password = cipher.decrypt(encrypted_password)
```

### 2. 最小权限原则

为应用创建专用数据库用户：

```sql
-- 创建专用用户
CREATE USER microgrid_app WITH PASSWORD 'secure_password';

-- 只授予必要权限（只读）
GRANT SELECT ON ALL TABLES IN SCHEMA public TO microgrid_app;

-- 如果需要写入权限
GRANT INSERT, UPDATE ON specific_tables TO microgrid_app;
```

### 3. SSL连接

使用SSL加密数据库连接：

```python
pg_url = "postgresql://user:pass@host:port/db?sslmode=require"
```

---

## 快速配置命令

```bash
# 1. 测试连接（修改用户名和密码）
python -c "
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://USERNAME:PASSWORD@10.10.20.10:14632/microgrid')
with engine.connect() as conn:
    result = conn.execute(text('SELECT version()'))
    print('✅ 连接成功:', result.scalar()[:50])
"

# 2. 检查数据
python -c "
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://USERNAME:PASSWORD@10.10.20.10:14632/microgrid')
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM micro_grid_overview_w'))
    print('✅ 数据行数:', result.scalar())
"

# 3. 注册连接（使用配置脚本）
python setup_postgresql_microgrid.py

# 4. 重启API服务
pkill -f 'uvicorn main:app'
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 总结

### 配置清单

- [ ] PostgreSQL数据库可访问
- [ ] 获取正确的用户名和密码
- [ ] 导入SQL数据文件
- [ ] 注册 `microgrid_db_pg` 连接
- [ ] 测试连接和查询
- [ ] 创建PostgreSQL版本模板
- [ ] 重启API服务
- [ ] 测试报告生成

### 下一步

1. **获取PostgreSQL凭证** - 联系数据库管理员
2. **运行配置脚本** - `python setup_postgresql_microgrid.py`
3. **创建PG模板** - 复制并修改连接配置
4. **测试生成报告** - 使用PostgreSQL模板

---

**文档版本:** 1.0  
**更新日期:** 2025-10-19  
**适用环境:** PostgreSQL 12+ / Python 3.8+

