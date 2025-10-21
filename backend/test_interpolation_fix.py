#!/usr/bin/env python3
"""测试字符串插值修复"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.context import ExecutionContext
from app.core.models import VariableMetadata, VariableSource

def test_basic_interpolation():
    """测试基础插值"""
    print("=" * 60)
    print("测试1: 基础变量插值")
    print("=" * 60)
    
    context = ExecutionContext("task1", "tpl1", {}, {})
    context.set_variable('wgid', 'ZQGY0174')
    context.set_variable('score', 85.5)
    
    result = context.interpolate_string('微网格: {{wgid}}, 评分: {{score}}')
    print(f"输入: '微网格: {{{{wgid}}}}, 评分: {{{{score}}}}'")
    print(f"输出: '{result}'")
    assert result == '微网格: ZQGY0174, 评分: 85.5'
    print("✅ 通过\n")


def test_nested_attributes():
    """测试嵌套属性"""
    print("=" * 60)
    print("测试2: 嵌套属性访问")
    print("=" * 60)
    
    context = ExecutionContext("task1", "tpl1", {}, {})
    context.set_variable('overview', {
        'micro_grid_name': '测试微网格',
        'wgid_score': 85.5,
        'problem_count': 10
    })
    
    result = context.interpolate_string('名称: {{overview.micro_grid_name}}, 评分: {{overview.wgid_score}}')
    print(f"输入: '名称: {{{{overview.micro_grid_name}}}}, 评分: {{{{overview.wgid_score}}}}'")
    print(f"输出: '{result}'")
    assert result == '名称: 测试微网格, 评分: 85.5'
    print("✅ 通过\n")


def test_length_filter():
    """测试length过滤器"""
    print("=" * 60)
    print("测试3: length过滤器")
    print("=" * 60)
    
    context = ExecutionContext("task1", "tpl1", {}, {})
    context.set_variable('problem_buildings', [
        {'name': 'A'},
        {'name': 'B'},
        {'name': 'C'}
    ])
    
    result = context.interpolate_string('问题楼宇数: {{problem_buildings | length}}')
    print(f"输入: '问题楼宇数: {{{{problem_buildings | length}}}}'")
    print(f"输出: '{result}'")
    assert result == '问题楼宇数: 3'
    print("✅ 通过\n")


def test_upper_filter():
    """测试upper过滤器"""
    print("=" * 60)
    print("测试4: upper过滤器")
    print("=" * 60)
    
    context = ExecutionContext("task1", "tpl1", {}, {})
    context.set_variable('name', 'John Doe')
    
    result = context.interpolate_string('名称: {{name | upper}}')
    print(f"输入: '名称: {{{{name | upper}}}}'")
    print(f"输出: '{result}'")
    assert result == '名称: JOHN DOE'
    print("✅ 通过\n")


def test_chained_filters():
    """测试链式过滤器"""
    print("=" * 60)
    print("测试5: 链式过滤器")
    print("=" * 60)
    
    context = ExecutionContext("task1", "tpl1", {}, {})
    context.set_variable('text', '  hello world  ')
    
    result = context.interpolate_string('文本: {{text | trim | upper}}')
    print(f"输入: '文本: {{{{text | trim | upper}}}}'")
    print(f"输出: '{result}'")
    assert result == '文本: HELLO WORLD'
    print("✅ 通过\n")


def test_nested_with_filter():
    """测试嵌套属性 + 过滤器"""
    print("=" * 60)
    print("测试6: 嵌套属性 + 过滤器")
    print("=" * 60)
    
    context = ExecutionContext("task1", "tpl1", {}, {})
    context.set_variable('overview', {
        'micro_grid_name': 'test grid',
        'buildings': [1, 2, 3, 4, 5]
    })
    
    result = context.interpolate_string(
        '名称: {{overview.micro_grid_name | upper}}, 楼宇数: {{overview.buildings | length}}'
    )
    print(f"输入: '名称: {{{{overview.micro_grid_name | upper}}}}, 楼宇数: {{{{overview.buildings | length}}}}'")
    print(f"输出: '{result}'")
    assert 'TEST GRID' in result and '5' in result
    print("✅ 通过\n")


def test_none_value():
    """测试None值处理"""
    print("=" * 60)
    print("测试7: None值处理")
    print("=" * 60)
    
    context = ExecutionContext("task1", "tpl1", {}, {})
    context.set_variable('value', None)
    
    result = context.interpolate_string('值: {{value}}')
    print(f"输入: '值: {{{{value}}}}'")
    print(f"输出: '{result}'")
    assert result == '值: '
    print("✅ 通过\n")


def test_list_length_with_none():
    """测试None值的length过滤器"""
    print("=" * 60)
    print("测试8: None值的length过滤器")
    print("=" * 60)
    
    context = ExecutionContext("task1", "tpl1", {}, {})
    context.set_variable('items', None)
    
    result = context.interpolate_string('数量: {{items | length}}')
    print(f"输入: '数量: {{{{items | length}}}}'")
    print(f"输出: '{result}'")
    assert result == '数量: 0'
    print("✅ 通过\n")


def main():
    print("\n" + "=" * 60)
    print("字符串插值功能测试")
    print("=" * 60 + "\n")
    
    try:
        test_basic_interpolation()
        test_nested_attributes()
        test_length_filter()
        test_upper_filter()
        test_chained_filters()
        test_nested_with_filter()
        test_none_value()
        test_list_length_with_none()
        
        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

