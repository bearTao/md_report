# PostgreSQL版本微网格预分析 - 快速开始

## 🎯 概述

本文档提供PostgreSQL版本微网格预分析的最简配置流程。

**为什么需要PostgreSQL版本？**
- ✅ 生产环境标准配置
- ✅ 原始数据源（`postgresql://10.10.20.10:14632/microgrid`）
- ✅ 更好的性能和可靠性
- ✅ 支持更多并发连接

## 📋 前置条件

1. PostgreSQL数据库凭证：
   - 主机: `10.10.20.10`
   - 端口: `14632`
   - 数据库: `microgrid`
   - 用户名: `?` （需要获取）
   - 密码: `?` （需要获取）

2. SQL数据文件已就绪：
   - 位置: `/data/tao/code/xuqiu/tmp/预分析报告建表语句及测试数据.sql`
   - 大小: 1.1MB
   - 包含所有表结构和测试数据

## 🚀 快速配置（3步完成）

### 步骤1: 配置PostgreSQL连接

**方法A: 使用配置脚本（推荐）**

```bash
cd /data/tao/code/xuqiu/backend

# 1. 编辑配置脚本，填入正确的凭证
vim setup_postgresql_microgrid.py
# 修改以下行:
#   PG_USERNAME = "your_username"  
#   PG_PASSWORD = "your_password"

# 2. 运行配置脚本
python setup_postgresql_microgrid.py

# 脚本会自动完成:
# - 测试PostgreSQL连接
# - 导入SQL数据（可选）
# - 注册数据库连接配置
# - 验证查询功能
```

**方法B: 手动注册（如果已有数据）**

```python
cd /data/tao/code/xuqiu/backend
python -c "
from app.database import SessionLocal
from app.models.db_models import DBConnection, DBEngineType

db = SessionLocal()

# 创建或更新PostgreSQL连接配置
conn = db.query(DBConnection).filter(DBConnection.name == 'microgrid_db_pg').first()
if conn:
    print('更新现有配置...')
else:
    conn = DBConnection(name='microgrid_db_pg', description='PostgreSQL微网格数据库')
    db.add(conn)

conn.engine = DBEngineType.POSTGRESQL
conn.host = '10.10.20.10'
conn.port = 14632
conn.database = 'microgrid'
conn.username = 'YOUR_USERNAME'      # ⚠️ 修改这里
conn.password_ciphertext = 'YOUR_PASSWORD'  # ⚠️ 修改这里
conn.is_active = 'true'

db.commit()
db.close()
print('✅ PostgreSQL连接已配置')
"
```

### 步骤2: 创建PostgreSQL版本模板

```bash
# 运行模板创建脚本
python create_postgresql_template.py
```

脚本会：
1. ✅ 复制现有MySQL模板
2. ✅ 将所有SQL查询的连接改为 `microgrid_db_pg`
3. ✅ 创建新模板 "微网格预分析-PostgreSQL版"

**输出示例：**
```
✅ PostgreSQL模板创建成功！
   模板ID: tpl_abc123xyz
   模板名称: 微网格预分析-PostgreSQL版
```

### 步骤3: 重启服务并测试

```bash
# 重启API服务
pkill -f "uvicorn main:app"
cd /data/tao/code/xuqiu/backend
nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /dev/null 2>&1 &

# 等待服务启动
sleep 5

# 测试生成报告
curl -X POST "http://localhost:8000/api/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{"template_id": "tpl_abc123xyz", "inputs": {"wgid": "ZQGY0174"}}'

# 查询报告
sleep 10
curl "http://localhost:8000/api/reports/?template_id=tpl_abc123xyz"
```

## ✅ 验证配置

### 检查数据库连接

```python
python -c "
from app.database import SessionLocal
from app.models.db_models import DBConnection

db = SessionLocal()
conn = db.query(DBConnection).filter(DBConnection.name == 'microgrid_db_pg').first()

if conn:
    print('✅ PostgreSQL连接配置存在')
    print(f'   引擎: {conn.engine.value}')
    print(f'   地址: {conn.host}:{conn.port}/{conn.database}')
    print(f'   用户: {conn.username}')
    print(f'   激活: {conn.is_active}')
else:
    print('❌ PostgreSQL连接配置不存在')

db.close()
"
```

### 测试查询

```python
python -c "
from app.connectors.database import db_connector
from app.database import engine as main_engine
from sqlalchemy import create_engine
import asyncio

# 注册连接（需要正确的凭证）
pg_url = 'postgresql://USERNAME:PASSWORD@10.10.20.10:14632/microgrid'
pg_engine = create_engine(pg_url)
db_connector.register_connection('microgrid_db_pg', pg_engine)

async def test():
    result = await db_connector.execute_query(
        connection_name='microgrid_db_pg',
        query='SELECT COUNT(*) as total FROM micro_grid_overview_w',
        timeout=10
    )
    print(f'✅ 查询成功: {result[0][\"total\"]} 条记录')

asyncio.run(test())
"
```

## 📁 相关文件说明

### 配置脚本

1. **`setup_postgresql_microgrid.py`** - PostgreSQL配置向导
   - 自动化配置流程
   - 测试连接和查询
   - 导入数据（可选）

2. **`create_postgresql_template.py`** - 模板创建工具
   - 自动创建PostgreSQL版本模板
   - 修改数据库连接配置

### SQL文件

3. **`/data/tao/code/xuqiu/tmp/预分析报告建表语句及测试数据.sql`**
   - PostgreSQL格式的DDL和数据
   - 包含所有表和测试数据
   - 原始数据源

### 文档

4. **`PostgreSQL版本配置指南.md`** - 详细配置文档
   - 完整的配置步骤
   - 故障排查指南
   - 性能优化建议

5. **`PostgreSQL版本快速开始.md`** (本文档)
   - 快速配置流程
   - 3步完成配置

## 🔧 常见问题

### Q1: 如何获取PostgreSQL凭证？

**A:** 联系数据库管理员或系统管理员，需要：
- 用户名（可能是 `postgres`, `microgrid`, `root` 等）
- 密码
- 确认可以从当前服务器访问 `10.10.20.10:14632`

### Q2: 数据库中没有数据怎么办？

**A:** 使用配置脚本导入数据：

```bash
python setup_postgresql_microgrid.py
# 选择 'y' 导入SQL数据
```

或手动导入：

```bash
psql -h 10.10.20.10 -p 14632 -U username -d microgrid \
  -f /data/tao/code/xuqiu/tmp/预分析报告建表语句及测试数据.sql
```

### Q3: 能否同时使用MySQL和PostgreSQL？

**A:** 可以！系统支持多个数据库连接：
- `microgrid_db` - MySQL版本（已配置）
- `microgrid_db_pg` - PostgreSQL版本（新配置）

两个版本可以并存，根据需要选择使用。

### Q4: 如何切换回MySQL版本？

**A:** 
- 使用原模板 "微网格预分析" （MySQL）
- 或在PostgreSQL模板中改回 `microgrid_db` 连接

### Q5: PostgreSQL连接失败怎么办？

**A:** 检查：
1. 网络连接: `telnet 10.10.20.10 14632`
2. 用户名密码是否正确
3. PostgreSQL是否允许远程连接（`pg_hba.conf`）
4. 防火墙是否开放端口 14632

## 🎯 配置清单

完成配置前，请确认：

- [ ] 已获取PostgreSQL凭证（用户名+密码）
- [ ] 可以访问 `10.10.20.10:14632`
- [ ] SQL数据文件存在
- [ ] API服务正常运行
- [ ] 已修改配置脚本中的凭证
- [ ] 已运行 `setup_postgresql_microgrid.py`
- [ ] 已运行 `create_postgresql_template.py`
- [ ] 已重启API服务
- [ ] 已测试报告生成

## 💡 下一步

配置完成后：

1. **在前端测试**
   - 选择 "微网格预分析-PostgreSQL版" 模板
   - 输入 wgid: `ZQGY0174`
   - 生成报告

2. **性能优化**
   - 创建必要的索引
   - 配置连接池
   - 启用查询缓存

3. **监控和维护**
   - 定期检查数据库连接
   - 监控查询性能
   - 备份数据

## 📞 需要帮助？

如果遇到问题：

1. 查看详细文档: `PostgreSQL版本配置指南.md`
2. 检查日志: `/data/tao/code/xuqiu/backend/logs/app.log`
3. 验证数据库连接配置
4. 测试SQL查询

---

**版本:** 1.0  
**更新:** 2025-10-19  
**状态:** 可用

