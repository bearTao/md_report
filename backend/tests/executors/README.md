# 执行器测试模块

变量执行器功能的测试，覆盖各种类型的执行器实现。

## 📦 测试文件说明

- **test_executors.py** - 基础执行器测试（用户输入、系统变量、SQL 执行器）
- **test_constant.py** - 常量变量执行器测试
- **test_constant_auto_injection.py** - 常量自动注入功能测试
- **test_image_executor.py** - 图像执行器测试
- **test_vision_ai_executor.py** - 视觉 AI 执行器测试

## 🎯 测试覆盖范围

### 基础执行器
- **UserInputExecutor** - 用户输入变量处理
- **SystemExecutor** - 系统变量处理（时间、日期等）
- **SqlExecutor** - SQL 查询执行和结果处理

### 常量执行器
- 数值常量处理
- 字符串常量处理
- 复杂类型常量（数组、对象）
- 常量自动注入到模板

### 图像执行器
- 图像变量处理
- 图像格式转换
- 图像数据验证

### 视觉 AI 执行器
- 图像分析和识别
- AI 模型集成
- 结果解析和验证

## 🚀 运行测试

```bash
# 运行所有执行器测试
pytest tests/executors/

# 运行特定测试文件
pytest tests/executors/test_constant.py

# 运行特定测试类
pytest tests/executors/test_constant.py::TestConstantExecutor
```

## 📝 注意事项

- SQL 执行器测试需要数据库连接
- 图像执行器测试需要测试图片文件
- 视觉 AI 测试可能需要 API 密钥（如 OpenAI）
- 某些测试使用异步执行，确保使用 `@pytest.mark.asyncio`
