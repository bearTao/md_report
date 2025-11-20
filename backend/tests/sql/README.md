# SQL 和数据库测试模块

SQL 查询功能和数据库集成的测试，包括混合查询和类型保留。

## 📦 测试文件说明

- **test_sql_hybrid_queries.py** - SQL 混合查询测试（用户输入 + SQL 变量）
- **test_type_preservation.py** - 数据类型保留测试（Decimal、日期等）

## 🎯 测试覆盖范围

### SQL 混合查询
- 用户输入参数与 SQL 变量结合
- 参数化查询
- 查询结果映射
- 多数据源集成
- 依赖关系处理

### 类型保留
- **Decimal 类型** - 精确数值保留（避免浮点误差）
- **日期时间类型** - datetime、date、time 处理
- **JSON 类型** - 复杂对象序列化和反序列化
- **枚举类型** - 枚举值验证
- **自定义类型** - 扩展类型支持

### 数据库连接
- 连接池管理
- 多数据库支持（PostgreSQL、MySQL 等）
- 事务处理
- 错误恢复

## 🚀 运行测试

```bash
# 运行所有 SQL 测试
pytest tests/sql/

# 运行特定测试文件
pytest tests/sql/test_sql_hybrid_queries.py

# 运行特定测试类
pytest tests/sql/test_type_preservation.py::TestTypePreservation
```

## 📝 注意事项

### 数据库配置
- 测试需要数据库连接（通常使用 PostgreSQL）
- 配置数据库连接信息在 `.env` 或 `conftest.py`
- 建议使用独立的测试数据库

### 测试数据
- 测试会创建临时表和数据
- 使用 fixture 自动清理测试数据
- 注意数据库事务的隔离级别

### 类型精度
- Decimal 类型测试涉及精确计算，避免使用 float
- 日期时间测试注意时区设置
- JSON 数据注意编码格式

## 🔧 数据库连接示例

```python
# 在 conftest.py 中配置
@pytest.fixture
def test_db_connection():
    connection = DatabaseConnection(
        engine="postgresql",
        host="localhost",
        port=5432,
        database="test_db",
        username="test_user",
        password="test_password"
    )
    yield connection
    connection.close()
```
