# API 测试模块

API 相关功能的测试，包括 API 连接器、配置管理、增强功能和集成测试。

## 📦 测试文件说明

- **test_api_config.py** - API 配置测试
- **test_api_enhancements.py** - API 增强功能测试（JMESPath、重试逻辑、响应映射）
- **test_api_integration.py** - API 集成测试
- **test_api_reports.py** - API 报告相关测试
- **test_api_templates.py** - API 模板测试
- **test_debug_api.py** - API 调试功能测试

## 🎯 测试覆盖范围

### API 连接器
- HTTP 请求处理
- 响应解析和映射
- JMESPath 路径提取
- 错误处理和重试逻辑

### API 配置
- 配置验证
- 参数管理
- 认证和授权

### API 集成
- 与其他模块的集成
- 端到端测试
- 数据流验证

## 🚀 运行测试

```bash
# 运行所有 API 测试
pytest tests/api/

# 运行特定测试文件
pytest tests/api/test_api_enhancements.py

# 运行特定测试函数
pytest tests/api/test_api_enhancements.py::TestJMESPathExtraction::test_simple_path
```

## 📝 注意事项

- 某些测试可能需要配置 API 密钥或外部服务
- 集成测试可能需要数据库连接
- 建议使用 mock 对象进行单元测试
