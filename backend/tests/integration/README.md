# 集成测试模块

端到端测试和多模块集成测试，验证系统整体功能。

## 📦 测试文件说明

- **test_integration.py** - 基础集成测试
- **test_integration_constant_and_type_preservation.py** - 常量和类型保留集成测试
- **test_image_integration.py** - 图像功能集成测试
- **test_p1_1_e2e.py** - P1 阶段端到端测试
- **test_p1_features.py** - P1 阶段功能测试

## 🎯 测试覆盖范围

### 端到端测试
- 完整的报告生成流程
- 从模板创建到报告输出
- 多变量类型协同工作
- 真实场景模拟

### 模块集成
- 执行器与渲染器集成
- 数据库与 API 集成
- 图像处理集成
- Agent 与报告生成集成

### P1 功能测试
- 核心功能验证
- 关键路径测试
- 性能基准测试
- 边界条件处理

### 常量和类型保留集成
- 常量在完整流程中的行为
- 类型在各模块间的传递
- 数据完整性验证

## 🚀 运行测试

```bash
# 运行所有集成测试
pytest tests/integration/

# 运行端到端测试
pytest tests/integration/test_p1_1_e2e.py

# 运行特定功能测试
pytest tests/integration/test_p1_features.py -v

# 运行测试并生成覆盖率报告
pytest tests/integration/ --cov=app --cov-report=html
```

## 📝 注意事项

### 测试环境
- 集成测试需要完整的测试环境
- 确保数据库、Redis 等服务正常运行
- 可能需要外部 API 密钥（如 OpenAI）

### 测试数据
- 使用 fixture 准备完整的测试数据
- 测试后自动清理
- 注意测试数据的隔离性

### 测试时间
- 集成测试通常比单元测试慢
- 考虑使用 `pytest-xdist` 并行执行
- 可以使用 marker 标记慢速测试：`@pytest.mark.slow`

### 调试建议
- 使用 `pytest -v -s` 查看详细输出
- 使用 `pytest --pdb` 在失败时进入调试器
- 检查日志文件了解测试失败原因

## 🔧 示例：运行特定测试

```bash
# 只运行快速测试
pytest tests/integration/ -m "not slow"

# 运行标记为 smoke 的测试
pytest tests/integration/ -m smoke

# 并行运行测试（需要安装 pytest-xdist）
pytest tests/integration/ -n auto
```
