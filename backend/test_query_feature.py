"""
测试 Agent 查询功能

测试查询报告内容并验证 Markdown 格式返回
"""
import asyncio
import requests
import json
from datetime import datetime


def test_query_report_content():
    """测试查询报告内容"""
    print("=" * 60)
    print("🧪 测试查询报告内容功能")
    print("=" * 60)
    
    # 首先获取一个报告ID
    print("\n1️⃣ 获取报告列表...")
    response = requests.get("http://localhost:8000/api/reports")
    
    if response.status_code != 200:
        print(f"❌ 获取报告列表失败: {response.status_code}")
        return
    
    data = response.json()
    reports = data.get("items", [])
    if not reports:
        print("❌ 没有可用的报告")
        return
    
    report_id = reports[0]["id"]
    print(f"✅ 使用报告 ID: {report_id}")
    
    # 测试查询报告内容
    print("\n2️⃣ 测试查询: 显示当前报告内容")
    query_request = "请输出当前的报告内容"
    
    response = requests.post(
        f"http://localhost:8000/api/reports/{report_id}/modify",
        params={"user_request": query_request}
    )
    
    if response.status_code != 200:
        print(f"❌ 请求失败: {response.status_code}")
        print(f"错误信息: {response.text}")
        return
    
    result = response.json()
    
    print("\n" + "=" * 60)
    print("📊 返回结果分析")
    print("=" * 60)
    
    print(f"\n✅ Session ID: {result.get('session_id')}")
    print(f"✅ Report Version: {result.get('report_version')}")
    print(f"✅ Success: {result.get('success')}")
    
    # 检查操作详情
    operations = result.get('operations', [])
    print(f"\n✅ 执行操作数: {len(operations)}")
    
    if operations:
        operation = operations[0]
        print(f"\n📋 操作详情:")
        print(f"   - 类型: {operation.get('operation_type')}")
        print(f"   - 成功: {operation.get('success')}")
        print(f"   - 耗时: {operation.get('duration_ms')}ms")
        
        # 检查查询详情
        details = operation.get('details', {})
        print(f"\n📝 查询详情:")
        print(f"   - 查询类型: {details.get('query_type')}")
        print(f"   - 结果格式: {details.get('result_format')}")
        
        # 显示查询结果（前500字符）
        query_result = details.get('query_result', '')
        print(f"\n📄 查询结果预览 (格式: {details.get('result_format')}):")
        print("-" * 60)
        preview = query_result[:500] if len(query_result) > 500 else query_result
        print(preview)
        if len(query_result) > 500:
            print(f"\n... (还有 {len(query_result) - 500} 个字符)")
        print("-" * 60)
        
        # 检查是否包含 Markdown 格式标记
        markdown_indicators = ['#', '**', '|', '-', '```']
        found_indicators = [ind for ind in markdown_indicators if ind in query_result]
        
        if found_indicators:
            print(f"\n✅ 检测到 Markdown 格式标记: {', '.join(found_indicators)}")
        else:
            print("\n⚠️  未检测到明显的 Markdown 格式标记")
    
    # 显示完整的返回说明
    explanation = result.get('explanation', '')
    print(f"\n💬 Agent 说明:")
    print(f"   {explanation}")
    
    return result


def test_other_queries():
    """测试其他查询类型"""
    print("\n" + "=" * 60)
    print("🧪 测试其他查询功能")
    print("=" * 60)
    
    # 获取报告ID
    response = requests.get("http://localhost:8000/api/reports")
    data = response.json()
    reports = data.get("items", [])
    if not reports:
        print("❌ 没有可用的报告")
        return
    report_id = reports[0]["id"]
    
    test_queries = [
        "显示所有参数",
        "获取统计信息",
        "显示章节结构",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}️⃣ 测试查询: {query}")
        
        response = requests.post(
            f"http://localhost:8000/api/reports/{report_id}/modify",
            params={"user_request": query}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('operations'):
                details = result['operations'][0].get('details', {})
                result_format = details.get('result_format')
                print(f"   ✅ 成功 - 格式: {result_format}")
            else:
                print(f"   ⚠️  成功但无操作记录")
        else:
            print(f"   ❌ 失败: {response.status_code}")


def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "Agent 查询功能测试" + " " * 23 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    try:
        # 测试主要查询功能
        result = test_query_report_content()
        
        if result:
            # 测试其他查询
            test_other_queries()
            
            print("\n" + "=" * 60)
            print("✅ 测试完成！")
            print("=" * 60)
            print("\n💡 提示:")
            print("   1. 检查返回的 result_format 是否为 'markdown'")
            print("   2. 查询结果应包含 Markdown 格式标记（#, **, | 等）")
            print("   3. 前端应使用 ReactMarkdown 组件渲染这些内容")
            print()
    
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
