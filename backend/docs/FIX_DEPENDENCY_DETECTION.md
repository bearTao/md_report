# 依赖变量检测和重新执行功能修复报告

## 修复日期
2025-11-17

## 问题描述

### 原始问题
在 Agent 修改报告时，更新参数后无法正确检测和重新执行依赖变量：

1. **依赖检测错误**：字段名不匹配 (`depends_on` vs `dependencies`)
2. **重新执行失败**：ExecutionScheduler 缺少依赖变量的 metadata
3. **用户输入缺失**：重新执行时未传递更新后的参数值

### 错误日志示例
```
[INFO] 参数更新完成: wgid, 耗时: 0ms, 影响 0 个依赖变量  ❌
[ERROR] Variable 'overview' depends on undefined variable 'wgid'  ❌
```

## 修复内容

### 0. 数据库连接注册（关键修复）

**修复文件**：`app/api/reports.py`

**问题**：在 `modify_report` 端点中，未注册数据库连接，导致重新执行 SQL 变量时报错 `Database connection 'xxx' not registered`。

**解决方案**：在调用 Agent 前注册所有活跃的数据库连接（与 `generate_report` 保持一致）。

```python
# 注册数据库连接（修复：重新执行依赖变量时需要访问数据库）
from app.connectors.database import db_connector

db_connections = db.query(DBConnection).all()
# ... 遍历并注册所有活跃连接
```

### 1. 依赖字段名统一 (`dependencies`)

**修复文件**：
- `app/services/agent/strategies/parameter_update.py`
- `app/services/agent/strategies/template_modification.py`
- `app/services/agent/operation_planner.py`

**修改**：将所有 `depends_on` 改为 `dependencies`，与 `VariableMetadata` 模型定义一致。

```python
# 修复前
depends_on = var_info.metadata.get("depends_on", [])

# 修复后
dependencies = var_info.metadata.get("dependencies", [])
```

### 2. 完整 Metadata 构建

**修复文件**：`app/services/agent/strategies/parameter_update.py`

**问题**：`memory.report_state.variables` 中的 `var.metadata` 是原始字典，不包含 `source` 字段（存储在 `var.source` 中），导致无法构建 `VariableMetadata` 对象。

**解决方案**：从 `memory.report_state.variables` 重新构建完整的 `VariableMetadata`：

```python
for var_name, var in memory.report_state.variables.items():
    # 复制 metadata 字典
    meta_dict = dict(var.metadata) if var.metadata else {}
    
    # 合并 source 字段（从 var.source）
    if "source" not in meta_dict:
        meta_dict["source"] = var.source
    
    # 补充必需字段
    if "type" not in meta_dict:
        meta_dict["type"] = "string"
    if "description" not in meta_dict:
        meta_dict["description"] = f"Variable {var_name}"
    
    # 创建完整的 VariableMetadata
    all_metadata[var_name] = VariableMetadata(**meta_dict)
```

### 3. 用户输入参数提取

**功能**：从 `memory.report_state.variables` 中提取所有 `user_input` 类型的变量值（包括已更新的值）。

```python
user_inputs = {}
for var_name, var in memory.report_state.variables.items():
    if var.source == "user_input" and var.value is not None:
        user_inputs[var_name] = var.value  # 包含更新后的新值
```

### 4. 错误处理增强

**改进**：
- 添加 try-except 处理 metadata 解析失败的情况
- 为失败的变量创建最小可用的 metadata
- 改进日志级别（debug → info）和内容

```python
try:
    all_metadata[var_name] = VariableMetadata(**meta_dict)
except Exception as e:
    logger.warning(f"解析变量 {var_name} 的 metadata 失败: {e}，使用默认配置")
    # 创建最小可用的 metadata
    all_metadata[var_name] = VariableMetadata(
        type="string",
        source=VariableSource(var.source),
        description=f"Variable {var_name}",
        required=False
    )
```

## 验证方法

### 测试场景
使用模板 `tpl_e3d21354d503`（微网格报告模板）测试：

1. 创建报告
2. 修改 `wgid` 参数（如：`ZQGY0174` → `JYRC1951`）
3. 观察日志输出

### 预期结果

```
[INFO] 参数 wgid 有 2 个依赖变量: overview, index_scores  ✅
[INFO] 参数更新完成: wgid, 耗时: Xms, 影响 2 个依赖变量  ✅
[INFO] 重新执行变量 overview, user_inputs: ['wgid'], metadata_count: 3  ✅
[INFO] Building DAG for 1 non-constant variables  ✅
[INFO] 变量 overview 重新执行成功，获得新值  ✅
[INFO] 变量 index_scores 重新执行成功，获得新值  ✅
[INFO] 操作执行完成: 3/3 成功, 0 失败  ✅
```

### 关键指标
- ✅ 依赖变量数量正确（2个）
- ✅ user_inputs 包含更新后的值
- ✅ metadata 包含所有需要的变量
- ✅ DAG 构建成功
- ✅ SQL 查询执行成功
- ✅ 所有操作成功完成

## 技术细节

### ExecutionScheduler 的依赖检查
```python
# scheduler.py:96
if dep not in metadata:
    raise DependencyError(
        f"Variable '{var_name}' depends on undefined variable '{dep}'"
    )
```

因此必须传递**所有**变量的 metadata，而不仅仅是要执行的变量。

### VariableInfo 数据结构
```python
VariableInfo(
    name=str,              # 变量名
    value=Any,             # 变量值
    source=str,            # 数据源类型（注意：不在 metadata 里）
    metadata=dict,         # 原始配置字典
    ...
)
```

`source` 字段在外层，需要手动合并到 metadata 中才能构建 `VariableMetadata`。

## 相关文件

### 修改的文件
1. `app/api/reports.py` - 数据库连接注册
2. `app/services/agent/strategies/parameter_update.py` - 核心修复
3. `app/services/agent/strategies/template_modification.py` - 字段名修复
4. `app/services/agent/operation_planner.py` - 字段名修复

### 涉及的模型
- `app/schemas/modification_schemas.py` - `VariableInfo`, `ConversationMemory`
- `app/core/models.py` - `VariableMetadata`
- `app/services/scheduler.py` - `ExecutionScheduler`
- `app/services/context.py` - `ExecutionContext`

## 测试建议

### 单元测试
创建测试用例验证：
1. 依赖检测逻辑
2. metadata 构建逻辑
3. user_inputs 提取逻辑

### 集成测试
1. 使用实际模板测试完整流程
2. 测试多层级依赖（A → B → C）
3. 测试同时更新多个参数

### 回归测试
验证其他功能未受影响：
- AI 内容优化
- 模板修改
- 报告生成

## 总结

此次修复解决了4个核心问题：
0. ✅ 数据库连接未注册（`modify_report` 缺少连接注册）
1. ✅ 字段命名不一致（`depends_on` → `dependencies`）
2. ✅ metadata 结构不完整（缺少 `source` 字段）
3. ✅ 执行上下文不完整（缺少 user_inputs 和依赖变量的 metadata）

修复后，Agent 可以正确：
- 识别依赖变量
- 提取更新后的参数值
- 构建完整的 DAG
- 重新执行 SQL/API/AI 等依赖变量
- 更新报告内容
