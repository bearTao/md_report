#!/usr/bin/env python3
"""
测试错误格式化功能
演示不同类型错误的格式化结果
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.core.exceptions import (
    TemplateRenderError, SqlExecutionError, AiGenerationError,
    VariableExecutionError, DependencyError, ValidationError
)
from app.api.reports import _format_error_details
import json


def print_error_example(title, error):
    """打印错误示例"""
    print(f"\n{'='*60}")
    print(f"📋 {title}")
    print('='*60)
    
    result = _format_error_details(error)
    
    print(f"\n错误代码: {result['code']}")
    print(f"错误消息: {result['message']}")
    
    if result.get('details'):
        print(f"\n详细信息:")
        for key, value in result['details'].items():
            if key != 'traceback':  # 跟踪信息太长，单独显示
                print(f"  - {key}: {value}")
    
    if result.get('suggestion'):
        print(f"\n💡 修复建议:")
        print(f"  {result['suggestion']}")
    
    print(f"\nJSON格式:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    print("🔍 错误处理格式化测试\n")
    print("=" * 60)
    
    # 1. 模板渲染错误 - 空值错误
    print_error_example(
        "场景1: 模板渲染 - 空值参与运算",
        TemplateRenderError("Template rendering failed: unsupported operand type(s) for +: 'int' and 'NoneType'")
    )
    
    # 2. 模板渲染错误 - 字段不存在
    print_error_example(
        "场景2: 模板渲染 - 访问不存在的字段",
        TemplateRenderError("Template rendering failed: 'dict object' has no attribute 'values'")
    )
    
    # 3. 模板渲染错误 - 除以零
    print_error_example(
        "场景3: 模板渲染 - 除以零",
        TemplateRenderError("Template rendering failed: division by zero")
    )
    
    # 4. 模板渲染错误 - 类型不支持索引
    print_error_example(
        "场景4: 模板渲染 - datetime对象不支持切片",
        TemplateRenderError("Template rendering failed: 'datetime.datetime' object is not subscriptable")
    )
    
    # 5. SQL执行错误 - 表不存在
    print_error_example(
        "场景5: SQL执行 - 表不存在",
        SqlExecutionError(
            variable_name='overview',
            message="(pymysql.err.ProgrammingError) (1146, \"Table 'microgrid.micro_grid_overview_w' doesn't exist\")"
        )
    )
    
    # 6. SQL执行错误 - 语法错误
    print_error_example(
        "场景6: SQL执行 - SQL语法错误",
        SqlExecutionError(
            variable_name='problem_buildings',
            message="You have an error in your SQL syntax near 'SELCT' at line 1"
        )
    )
    
    # 7. SQL执行错误 - 超时
    print_error_example(
        "场景7: SQL执行 - 查询超时",
        SqlExecutionError(
            variable_name='statistics',
            message="Query execution timeout after 30 seconds"
        )
    )
    
    # 8. AI生成错误 - API密钥无效
    print_error_example(
        "场景8: AI生成 - API密钥错误",
        AiGenerationError(
            variable_name='analysis_summary',
            message="Invalid API key provided"
        )
    )
    
    # 9. AI生成错误 - 频率限制
    print_error_example(
        "场景9: AI生成 - 频率限制",
        AiGenerationError(
            variable_name='recommendations',
            message="Rate limit exceeded. Please try again later."
        )
    )
    
    # 10. 依赖错误
    print_error_example(
        "场景10: 变量依赖错误",
        DependencyError("Variable 'dependent_var' depends on missing variable 'required_var'")
    )
    
    # 11. 验证错误
    print_error_example(
        "场景11: 输入验证错误",
        ValidationError("wgid must match pattern ^[A-Z0-9]{8,16}$, got 'abc'")
    )
    
    # 12. 通用变量执行错误
    print_error_example(
        "场景12: 变量执行错误",
        VariableExecutionError(
            variable_name='custom_variable',
            message="Failed to execute custom logic: Connection refused"
        )
    )
    
    print("\n" + "="*60)
    print("✅ 测试完成！")
    print("="*60)
    print("\n前端可以根据 'code' 字段进行分类处理：")
    print("  - TEMPLATE_RENDER_ERROR: 模板错误，提供编辑按钮")
    print("  - SQL_EXECUTION_ERROR: SQL错误，提供数据库检查")
    print("  - AI_GENERATION_ERROR: AI错误，提供重试/配置")
    print("  - DEPENDENCY_ERROR: 依赖错误，检查配置")
    print("  - VALIDATION_ERROR: 验证错误，提示用户修正输入")
    print()


if __name__ == '__main__':
    main()

