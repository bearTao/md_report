"""
测试错误格式化功能
"""
import pytest
from app.core.exceptions import (
    TemplateRenderError, SqlExecutionError, AiGenerationError,
    VariableExecutionError, DependencyError, ValidationError
)
from app.api.reports import _format_error_details


class TestErrorFormatting:
    """测试错误格式化"""
    
    def test_template_render_error_null_value(self):
        """测试模板渲染错误 - 空值"""
        error = TemplateRenderError(
            "Template rendering failed: unsupported operand type(s) for +: 'int' and 'NoneType'"
        )
        result = _format_error_details(error)
        
        assert result['code'] == 'TEMPLATE_RENDER_ERROR'
        assert '模板渲染失败' in result['message']
        assert result['details']['type'] == 'type_error'
        assert result['suggestion'] is not None
        assert 'or 0' in result['suggestion']
    
    def test_template_render_error_dict_access(self):
        """测试模板渲染错误 - 字典访问"""
        error = TemplateRenderError(
            "Template rendering failed: 'dict object' has no attribute 'values'"
        )
        result = _format_error_details(error)
        
        assert result['code'] == 'TEMPLATE_RENDER_ERROR'
        assert result['details']['type'] == 'null_value_error'
        assert result['details']['field'] == 'values'
        assert '.get(' in result['suggestion']
    
    def test_template_render_error_division_by_zero(self):
        """测试模板渲染错误 - 除以零"""
        error = TemplateRenderError("Template rendering failed: division by zero")
        result = _format_error_details(error)
        
        assert result['code'] == 'TEMPLATE_RENDER_ERROR'
        assert result['details']['type'] == 'division_by_zero'
        assert 'if b != 0' in result['suggestion']
    
    def test_template_render_error_subscript(self):
        """测试模板渲染错误 - 索引错误"""
        error = TemplateRenderError(
            "Template rendering failed: 'datetime.datetime' object is not subscriptable"
        )
        result = _format_error_details(error)
        
        assert result['code'] == 'TEMPLATE_RENDER_ERROR'
        assert result['details']['type'] == 'subscript_error'
        assert '[:10]' in result['suggestion']
    
    def test_sql_execution_error_table_not_exists(self):
        """测试SQL执行错误 - 表不存在"""
        error = SqlExecutionError(
            variable_name='overview',
            message="Table 'test.table' doesn't exist"
        )
        result = _format_error_details(error)
        
        assert result['code'] == 'SQL_EXECUTION_ERROR'
        assert result['details']['variable'] == 'overview'
        assert '表名' in result['suggestion'] or '数据库' in result['suggestion']
    
    def test_sql_execution_error_syntax(self):
        """测试SQL执行错误 - 语法错误"""
        error = SqlExecutionError(
            variable_name='query',
            message="You have an error in your SQL syntax"
        )
        result = _format_error_details(error)
        
        assert result['code'] == 'SQL_EXECUTION_ERROR'
        assert 'SQL' in result['suggestion'] or '语法' in result['suggestion']
    
    def test_sql_execution_error_timeout(self):
        """测试SQL执行错误 - 超时"""
        error = SqlExecutionError(
            variable_name='stats',
            message="Query execution timeout"
        )
        result = _format_error_details(error)
        
        assert result['code'] == 'SQL_EXECUTION_ERROR'
        assert '超时' in result['suggestion'] or 'timeout' in result['suggestion'].lower()
    
    def test_ai_generation_error_api_key(self):
        """测试AI生成错误 - API密钥"""
        error = AiGenerationError(
            variable_name='summary',
            message="Invalid API key provided"
        )
        result = _format_error_details(error)
        
        assert result['code'] == 'AI_GENERATION_ERROR'
        assert result['details']['variable'] == 'summary'
        assert 'API' in result['suggestion'] or '密钥' in result['suggestion']
    
    def test_ai_generation_error_rate_limit(self):
        """测试AI生成错误 - 频率限制"""
        error = AiGenerationError(
            variable_name='analysis',
            message="Rate limit exceeded"
        )
        result = _format_error_details(error)
        
        assert result['code'] == 'AI_GENERATION_ERROR'
        assert '频率' in result['suggestion'] or '重试' in result['suggestion']
    
    def test_dependency_error(self):
        """测试依赖错误"""
        error = DependencyError("Variable 'a' depends on missing 'b'")
        result = _format_error_details(error)
        
        assert result['code'] == 'DEPENDENCY_ERROR'
        assert '依赖' in result['message']
        assert result['suggestion'] is not None
    
    def test_validation_error(self):
        """测试验证错误"""
        error = ValidationError("Input validation failed")
        result = _format_error_details(error)
        
        assert result['code'] == 'VALIDATION_ERROR'
        assert '验证' in result['message']
        assert result['suggestion'] is not None
    
    def test_variable_execution_error(self):
        """测试变量执行错误"""
        error = VariableExecutionError(
            variable_name='custom',
            message="Execution failed"
        )
        result = _format_error_details(error)
        
        assert result['code'] == 'VARIABLE_EXECUTION_ERROR'
        assert result['details']['variable'] == 'custom'
        assert result['suggestion'] is not None
    
    def test_generic_error(self):
        """测试通用错误"""
        error = Exception("Generic error message")
        result = _format_error_details(error)
        
        assert result['code'] == 'EXECUTION_ERROR'
        assert result['details']['type'] == 'Exception'
        assert result['details']['error'] == 'Generic error message'
    
    def test_error_includes_traceback(self):
        """测试错误包含堆栈跟踪"""
        error = TemplateRenderError("Test error")
        result = _format_error_details(error)
        
        assert 'traceback' in result['details']
        assert isinstance(result['details']['traceback'], list)
        assert len(result['details']['traceback']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

