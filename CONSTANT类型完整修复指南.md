# CONSTANT 类型完整修复指南

## 问题描述

添加 `source: constant` 类型后，出现两个错误：

### 错误 1：枚举类型不匹配
```
ValueError: 'constant' is not a valid VariableSourceType
```

### 错误 2：数据库 ENUM 不包含新值
```
Data truncated for column 'source' at row 1
[parameters: {'source': 'CONSTANT', ...}]
```

## 根本原因

`CONSTANT` 类型需要在 **3 个地方** 同步定义：

1. ✅ **核心模型** (`app/core/models.py`) - 已完成
2. ✅ **数据库模型** (`app/models/db_models.py`) - 已完成
3. ❌ **数据库 schema** (MySQL ENUM) - **需要迁移**
4. ✅ **前端类型** (`frontend/src/types/index.ts`) - 已完成

## 修复步骤

### 步骤 1：备份数据库（推荐）

```bash
mysqldump -u your_user -p your_database > backup_before_constant.sql
```

### 步骤 2：执行数据库迁移

**方式 A：使用提供的 SQL 脚本**

```bash
cd /data/tao/code/xuqiu/backend
mysql -u your_user -p your_database < add_constant_to_enum.sql
```

**方式 B：手动执行 SQL**

```sql
-- 连接到数据库
mysql -u your_user -p your_database

-- 执行以下 SQL
ALTER TABLE generation_task_variables 
MODIFY COLUMN source ENUM(
    'user_input', 
    'sql', 
    'api', 
    'ai_generation', 
    'system',
    'constant',  -- 新增
    'image',
    'vision_ai'
) NOT NULL;

-- 验证
SELECT COLUMN_TYPE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'generation_task_variables' 
AND COLUMN_NAME = 'source';
```

**方式 C：使用 Python 脚本执行**

```bash
cd /data/tao/code/xuqiu/backend
python migrate_add_constant.py
```

### 步骤 3：验证修复

运行验证脚本：

```bash
cd /data/tao/code/xuqiu/backend
python verify_constant_fix.py
```

### 步骤 4：重启服务

```bash
# 重启后端服务
# 刷新前端页面
```

### 步骤 5：测试

创建包含常量变量的模板并执行，确认：
- ✅ 无 ValueError 错误
- ✅ 无数据库 truncate 错误
- ✅ 前端变量列表正常显示
- ✅ 常量自动注入功能正常工作

## 已修复的代码

### ✅ 1. 后端数据库模型 (db_models.py)

```python
class VariableSourceType(str, enum.Enum):
    """Variable source types"""
    USER_INPUT = "user_input"
    SQL = "sql"
    API = "api"
    AI_GENERATION = "ai_generation"
    SYSTEM = "system"
    CONSTANT = "constant"  # ✅ 已添加
    IMAGE = "image"
    VISION_AI = "vision_ai"
```

### ✅ 2. 前端类型定义 (index.ts)

```typescript
export type VariableSource = 'user_input' | 'sql' | 'api' | 'ai_generation' | 'system' | 'constant' | 'image' | 'vision_ai';
//                                                                                        ^^^^^^^^^^
//                                                                                        已添加
```

## 数据库迁移 SQL

```sql
-- MySQL
ALTER TABLE generation_task_variables 
MODIFY COLUMN source ENUM(
    'user_input', 
    'sql', 
    'api', 
    'ai_generation', 
    'system',
    'constant',  -- 新增
    'image',
    'vision_ai'
) NOT NULL;
```

## 验证清单

- [ ] 数据库已备份
- [ ] SQL 迁移已执行
- [ ] 数据库 ENUM 包含 'constant'
- [ ] 后端服务已重启
- [ ] 前端页面已刷新
- [ ] 创建测试模板成功
- [ ] 常量变量执行成功
- [ ] 前端显示正常
- [ ] 无错误日志

## 故障排查

### 问题：SQL 执行失败

**错误**: `ALTER TABLE failed`

**解决**:
1. 检查数据库权限
2. 确认表名正确
3. 检查是否有现有数据与新 ENUM 冲突

### 问题：迁移后仍报错

**解决**:
1. 确认所有后端进程已重启
2. 清除 SQLAlchemy 缓存
3. 检查连接池是否已刷新

### 问题：数据库连接错误

**解决**:
```bash
# 检查数据库连接
mysql -u your_user -p -h your_host your_database

# 查看当前 ENUM 定义
SHOW COLUMNS FROM generation_task_variables LIKE 'source';
```

## 相关文件

1. `backend/app/core/models.py` - 核心模型定义
2. `backend/app/models/db_models.py` - 数据库模型定义
3. `frontend/src/types/index.ts` - 前端类型定义
4. `backend/add_constant_to_enum.sql` - 数据库迁移脚本
5. `backend/migrate_add_constant.py` - Python 迁移脚本
6. `backend/verify_constant_fix.py` - 验证脚本

## 注意事项

⚠️ **重要**:
1. 在生产环境执行前务必备份数据库
2. 建议在业务低峰期执行迁移
3. 迁移过程中表会被锁定（MySQL）
4. 确保所有应用实例都重启

## 完成确认

修复完成后，你应该能够：

✅ 创建包含 `source: constant` 的变量  
✅ 执行包含常量的模板  
✅ 在前端看到常量变量的执行状态  
✅ 常量自动注入功能正常工作  
✅ 无任何相关错误日志

## 支持

如有问题，请检查：
- `backend/logs/app.log` - 应用日志
- MySQL error log - 数据库日志
- 浏览器 console - 前端错误

---

**更新日期**: 2025-10-29  
**状态**: 待执行数据库迁移

