# 测试目录结构说明

本测试目录按功能模块组织，每个模块包含相关的测试文件、文档和测试数据。

## 📁 目录结构

```
tests/
├── agent/              # Agent 模式测试
├── api/                # API 相关测试
├── executors/         # 执行器测试
├── template/          # 模板系统测试
├── sql/               # SQL 和数据库测试
├── integration/       # 集成和端到端测试
├── core/              # 核心功能测试
├── conftest.py        # pytest 配置和共享 fixture
└── __init__.py        # 测试包初始化
```

## 📦 模块说明

### [agent/](./agent/README.md)
Agent 模式相关功能测试，包括：
- 意图解析
- 依赖检测
- 操作规划
- 修改策略
- 对话管理

**文件数**: 7 个测试文件 + README + Postman 集合

### [api/](./api/README.md)
API 相关功能测试，包括：
- API 连接器和配置
- JMESPath 路径提取
- 重试逻辑和错误处理
- API 集成和端到端测试

**文件数**: 6 个测试文件

### [executors/](./executors/README.md)
各类变量执行器测试，包括：
- 用户输入执行器
- 常量执行器
- SQL 执行器
- 图像执行器
- 视觉 AI 执行器

**文件数**: 5 个测试文件

### [template/](./template/README.md)
模板系统测试，包括：
- 模板渲染引擎
- 模板嵌套和继承
- 调试功能

**文件数**: 2 个测试文件

### [sql/](./sql/README.md)
SQL 和数据库功能测试，包括：
- 混合查询（用户输入 + SQL）
- 数据类型保留（Decimal、日期等）
- 参数化查询

**文件数**: 2 个测试文件

### [integration/](./integration/README.md)
集成和端到端测试，包括：
- 完整报告生成流程
- 多模块协同测试
- P1 阶段功能验证
- 图像功能集成

**文件数**: 5 个测试文件

### [core/](./core/README.md)
核心功能测试，包括：
- 执行上下文管理
- 任务调度器
- 错误处理和格式化

**文件数**: 3 个测试文件

## 🚀 快速开始

### 运行所有测试
```bash
# 激活测试环境
conda activate test_md

# 运行所有测试
pytest tests/

# 运行测试并显示覆盖率
pytest tests/ --cov=app --cov-report=html
```

### 运行特定模块测试
```bash
# 运行 API 测试
pytest tests/api/

# 运行执行器测试
pytest tests/executors/

# 运行集成测试
pytest tests/integration/
```

### 运行特定测试文件
```bash
# 运行特定文件
pytest tests/api/test_api_enhancements.py

# 运行特定测试类
pytest tests/executors/test_constant.py::TestConstantExecutor

# 运行特定测试函数
pytest tests/core/test_context.py::test_context_creation
```

## 🔧 测试配置

### pytest.ini
项目根目录的 `pytest.ini` 包含 pytest 配置：
- 测试发现规则
- 标记（markers）定义
- 输出格式设置

### conftest.py
`tests/conftest.py` 包含共享的 fixture：
- 数据库会话
- 测试数据准备
- Mock 对象
- 环境配置

## 📝 测试编写规范

### 命名规范
- 测试文件：`test_*.py`
- 测试类：`Test*`
- 测试函数：`test_*`

### 异步测试
```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### 使用 Fixture
```python
def test_with_fixture(db_session):
    # db_session 来自 conftest.py
    user = db_session.query(User).first()
    assert user is not None
```

### 参数化测试
```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    assert input * 2 == expected
```

## 🎯 测试最佳实践

### 1. 测试隔离
- 每个测试独立运行
- 不依赖其他测试的结果
- 使用 fixture 准备和清理数据

### 2. 明确的断言
```python
# 好的断言
assert user.name == "Alice"
assert len(results) == 3

# 避免模糊的断言
assert user  # 不够明确
```

### 3. 测试边界条件
- 空值、null、空字符串
- 边界值（最大、最小）
- 异常情况

### 4. 使用 Mock
```python
from unittest.mock import Mock, patch

@patch('app.services.external_api.call')
def test_with_mock(mock_call):
    mock_call.return_value = {"status": "ok"}
    result = my_function()
    assert result["status"] == "ok"
```

## 📊 测试覆盖率

### 生成覆盖率报告
```bash
# HTML 报告
pytest tests/ --cov=app --cov-report=html

# 终端报告
pytest tests/ --cov=app --cov-report=term

# XML 报告（用于 CI）
pytest tests/ --cov=app --cov-report=xml
```

### 查看覆盖率
生成的 HTML 报告位于 `htmlcov/index.html`，用浏览器打开查看详细的代码覆盖情况。

## 🐛 调试测试

### 查看详细输出
```bash
# 显示 print 输出
pytest tests/ -s

# 显示详细信息
pytest tests/ -v

# 组合使用
pytest tests/ -v -s
```

### 在失败时进入调试器
```bash
# 使用 pdb
pytest tests/ --pdb

# 使用 ipdb（需要安装）
pytest tests/ --pdb --pdbcls=IPython.terminal.debugger:Pdb
```

### 只运行失败的测试
```bash
# 第一次运行
pytest tests/

# 只重新运行失败的测试
pytest tests/ --lf

# 先运行失败的，再运行其他的
pytest tests/ --ff
```

## 📚 相关文档

- [pytest 官方文档](https://docs.pytest.org/)
- [pytest-asyncio 文档](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py 文档](https://coverage.readthedocs.io/)

## 🤝 贡献指南

添加新测试时：
1. 选择合适的模块目录
2. 遵循命名规范
3. 编写清晰的测试文档字符串
4. 更新对应模块的 README
5. 确保测试可以独立运行
6. 运行 `pytest` 验证所有测试通过

---

**最后更新**: 2025-11-20
