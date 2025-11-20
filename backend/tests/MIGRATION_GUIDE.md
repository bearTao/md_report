# 测试目录重组迁移指南

## 📋 变更概述

测试目录已重新组织为模块化结构，所有测试文件按功能分类到不同的子目录中。

### 之前的结构
```
tests/
├── test_api_config.py
├── test_api_enhancements.py
├── test_executors.py
├── test_constant.py
├── ... (24 个测试文件混在一起)
└── agent/ (已有良好组织)
```

### 现在的结构
```
tests/
├── agent/              # Agent 模式测试
├── api/                # API 相关测试 (6 个文件)
├── executors/         # 执行器测试 (5 个文件)
├── template/          # 模板系统测试 (2 个文件)
├── sql/               # SQL 和数据库测试 (2 个文件)
├── integration/       # 集成测试 (5 个文件)
├── core/              # 核心功能测试 (3 个文件)
├── conftest.py
└── README.md
```

## 📦 文件迁移映射

### API 模块 (`tests/api/`)
- `test_api_config.py` → `tests/api/test_api_config.py`
- `test_api_enhancements.py` → `tests/api/test_api_enhancements.py`
- `test_api_integration.py` → `tests/api/test_api_integration.py`
- `test_api_reports.py` → `tests/api/test_api_reports.py`
- `test_api_templates.py` → `tests/api/test_api_templates.py`
- `test_debug_api.py` → `tests/api/test_debug_api.py`

### 执行器模块 (`tests/executors/`)
- `test_executors.py` → `tests/executors/test_executors.py`
- `test_constant.py` → `tests/executors/test_constant.py`
- `test_constant_auto_injection.py` → `tests/executors/test_constant_auto_injection.py`
- `test_image_executor.py` → `tests/executors/test_image_executor.py`
- `test_vision_ai_executor.py` → `tests/executors/test_vision_ai_executor.py`

### 模板模块 (`tests/template/`)
- `test_renderer.py` → `tests/template/test_renderer.py`
- `test_template_nesting.py` → `tests/template/test_template_nesting.py`

### SQL 模块 (`tests/sql/`)
- `test_sql_hybrid_queries.py` → `tests/sql/test_sql_hybrid_queries.py`
- `test_type_preservation.py` → `tests/sql/test_type_preservation.py`

### 集成测试模块 (`tests/integration/`)
- `test_integration.py` → `tests/integration/test_integration.py`
- `test_integration_constant_and_type_preservation.py` → `tests/integration/test_integration_constant_and_type_preservation.py`
- `test_image_integration.py` → `tests/integration/test_image_integration.py`
- `test_p1_1_e2e.py` → `tests/integration/test_p1_1_e2e.py`
- `test_p1_features.py` → `tests/integration/test_p1_features.py`

### 核心功能模块 (`tests/core/`)
- `test_context.py` → `tests/core/test_context.py`
- `test_scheduler.py` → `tests/core/test_scheduler.py`
- `test_error_formatting.py` → `tests/core/test_error_formatting.py`

## 🚀 运行测试命令变更

### 以前的命令
```bash
# 运行所有测试
pytest tests/

# 运行特定文件
pytest tests/test_api_config.py
```

### 现在的命令
```bash
# 运行所有测试（不变）
pytest tests/

# 运行特定模块的所有测试
pytest tests/api/
pytest tests/executors/
pytest tests/integration/

# 运行特定文件（路径改变）
pytest tests/api/test_api_config.py
pytest tests/executors/test_constant.py
pytest tests/integration/test_p1_features.py

# 运行特定测试函数（路径改变）
pytest tests/api/test_api_enhancements.py::TestJMESPathExtraction::test_simple_path
```

## 📝 代码中的导入路径

### 测试文件内部导入
测试文件内部导入应用代码的方式**不需要改变**：

```python
# 这些导入仍然有效
from app.services.renderer import template_renderer
from app.executors.sql import SqlExecutor
from app.core.models import VariableMetadata
```

### conftest.py
`conftest.py` 保持在 `tests/` 根目录，所有子模块的测试都能自动使用其中定义的 fixture。

## ✅ 验证迁移

运行以下命令验证所有测试都能正常发现和运行：

```bash
# 激活测试环境
conda activate test_md

# 收集所有测试（不运行）
pytest tests/ --collect-only

# 应该显示: 290 tests collected

# 运行所有测试
pytest tests/ -v

# 运行特定模块
pytest tests/api/ -v
pytest tests/executors/ -v
```

## 📖 新增文档

每个模块目录都包含：

1. **README.md** - 模块说明文档
   - 测试文件说明
   - 测试覆盖范围
   - 运行示例
   - 注意事项

2. **__init__.py** - 模块初始化文件
   - 模块说明

3. 主 `tests/README.md` - 总体结构说明

## 🎯 优势

### 更清晰的结构
- 按功能模块组织，易于查找相关测试
- 每个模块有独立的文档说明
- 新增测试时容易确定放置位置

### 更好的可维护性
- 模块化测试，降低耦合
- 可以针对特定模块运行测试
- 便于 CI/CD 中的测试分组

### 更快的测试执行
- 可以只运行相关模块的测试
- 支持并行测试执行
- 便于测试优先级管理

## 📊 统计信息

- **总测试数**: 290 个
- **模块数**: 7 个 (agent, api, executors, template, sql, integration, core)
- **每个模块的 README**: 7 个
- **共享 fixture**: conftest.py (保持不变)

## 🤝 后续操作

1. **熟悉新结构**: 查看各模块的 README 了解测试范围
2. **更新 CI/CD**: 如果有 CI 配置，可以考虑按模块分组运行测试
3. **添加新测试**: 根据功能选择合适的模块目录

## ❓ 常见问题

### Q: 旧的测试路径还能用吗？
A: 不能，文件已经移动。需要使用新的路径。

### Q: conftest.py 的 fixture 还能用吗？
A: 可以，所有子模块都能使用根目录的 conftest.py 中的 fixture。

### Q: 如何添加新测试？
A: 根据测试功能选择合适的模块目录，参考该模块的 README。

### Q: 可以在子模块添加自己的 conftest.py 吗？
A: 可以，子模块可以有自己的 conftest.py 来定义模块特定的 fixture。

---

**迁移日期**: 2025-11-20  
**影响范围**: 测试目录结构  
**破坏性变更**: 测试文件路径改变
