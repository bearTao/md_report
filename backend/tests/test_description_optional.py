"""
测试 description 字段是否为可选

验证修改后 VariableMetadata 可以在不提供 description 的情况下正常创建。
"""
import pytest
from app.core.models import VariableMetadata, VariableSource, SqlConfig


def test_description_is_optional():
    """测试 description 字段是可选的"""
    # 创建没有 description 的变量元数据
    metadata = VariableMetadata(
        type="string",
        source=VariableSource.USER_INPUT
    )
    
    # 验证 description 默认为空字符串
    assert metadata.description == ""
    assert isinstance(metadata.description, str)


def test_description_can_be_provided():
    """测试 description 可以被提供"""
    metadata = VariableMetadata(
        type="string",
        source=VariableSource.USER_INPUT,
        description="用户输入的标题"
    )
    
    assert metadata.description == "用户输入的标题"


def test_sql_variable_without_description():
    """测试 SQL 变量可以不提供 description"""
    metadata = VariableMetadata(
        type="object",
        source=VariableSource.SQL,
        sql_config=SqlConfig(
            connection="test_db",
            query="SELECT * FROM users WHERE id = :user_id",
            parameters=["user_id"]
        )
    )
    
    # 应该成功创建，description 为空
    assert metadata.description == ""
    assert metadata.sql_config is not None
    assert metadata.sql_config.parameters == ["user_id"]


def test_minimal_variable_metadata():
    """测试最小化的变量元数据配置"""
    # 只提供必需字段
    metadata = VariableMetadata(
        type="string",
        source=VariableSource.CONSTANT,
        value="test_value"
    )
    
    # 验证所有可选字段都有默认值
    assert metadata.description == ""
    assert metadata.required is False
    assert metadata.default is None
    assert metadata.dependencies == []
    assert metadata.schema is None


if __name__ == "__main__":
    # 运行测试
    test_description_is_optional()
    test_description_can_be_provided()
    test_sql_variable_without_description()
    test_minimal_variable_metadata()
    print("✅ 所有测试通过！description 字段已成功改为可选。")
