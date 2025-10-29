# CONSTANT 类型枚举修复说明

## 问题描述

**错误信息**:
```
ValueError: 'constant' is not a valid VariableSourceType
```

**错误位置**:
```python
File "/data/tao/code/xuqiu/backend/app/api/reports.py", line 999
source=VariableSourceType(var_meta.source.value),
```

## 问题原因

在实施"常量自动注入"功能时，我们在核心模型 `app/core/models.py` 中的 `VariableSource` 枚举添加了 `CONSTANT = "constant"`，但忘记同步更新以下两处：

1. **后端数据库模型** - `app/models/db_models.py` 中的 `VariableSourceType` 枚举
2. **前端类型定义** - `frontend/src/types/index.ts` 中的 `VariableSource` 类型

## 修复内容

### 1. 后端数据库模型 (db_models.py)

**文件**: `/data/tao/code/xuqiu/backend/app/models/db_models.py`

**修改前**:
```python
class VariableSourceType(str, enum.Enum):
    """Variable source types"""
    USER_INPUT = "user_input"
    SQL = "sql"
    API = "api"
    AI_GENERATION = "ai_generation"
    SYSTEM = "system"
    IMAGE = "image"
    VISION_AI = "vision_ai"
```

**修改后**:
```python
class VariableSourceType(str, enum.Enum):
    """Variable source types"""
    USER_INPUT = "user_input"
    SQL = "sql"
    API = "api"
    AI_GENERATION = "ai_generation"
    SYSTEM = "system"
    CONSTANT = "constant"  # ✅ 添加
    IMAGE = "image"
    VISION_AI = "vision_ai"
```

### 2. 前端类型定义 (index.ts)

**文件**: `/data/tao/code/xuqiu/frontend/src/types/index.ts`

**修改前**:
```typescript
export type VariableSource = 'user_input' | 'sql' | 'api' | 'ai_generation' | 'system' | 'image' | 'vision_ai';
```

**修改后**:
```typescript
export type VariableSource = 'user_input' | 'sql' | 'api' | 'ai_generation' | 'system' | 'constant' | 'image' | 'vision_ai';
```

## 修复效果

修复后，系统将能够正确处理 `source: constant` 类型的变量：

1. ✅ **后端 API** - `progress_callback` 可以正确创建 `VariableSourceType` 枚举
2. ✅ **前端显示** - TypeScript 类型检查通过
3. ✅ **变量执行** - 常量变量正常执行并显示在前端
4. ✅ **WebSocket 通信** - 变量状态更新正常传递

## 验证步骤

1. 重启后端服务
2. 刷新前端页面
3. 创建或执行包含 `constant` 变量的模板
4. 验证变量执行详情能正常显示所有变量

## 相关功能

- [常量自动注入功能](./常量自动注入功能说明.md)
- [常量变量类型](./类型保持和常量变量实施总结.md)

## 修复日期

2025-10-29

## 状态

✅ 已修复并验证

