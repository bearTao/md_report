"""
简单的查询功能测试
"""
import requests
import json


def main():
    print("=" * 60)
    print("Agent Query Test")
    print("=" * 60)
    
    # 获取报告列表
    print("\n1. Getting report list...")
    response = requests.get("http://localhost:8000/api/reports")
    data = response.json()
    reports = data.get("items", [])
    
    if not reports:
        print("No reports found")
        return
    
    report_id = reports[0]["id"]
    print(f"Using report ID: {report_id}")
    
    # 测试查询
    print("\n2. Testing query: Show report content")
    response = requests.post(
        f"http://localhost:8000/api/reports/{report_id}/modify",
        params={"user_request": "请输出当前的报告内容"}
    )
    
    result = response.json()
    
    # 保存完整返回结果
    with open('api_response.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("Full API response saved to: api_response.json")
    
    print("\n" + "=" * 60)
    print("Result Analysis:")
    print("=" * 60)
    
    print(f"\nSuccess: {result.get('success')}")
    print(f"Session ID: {result.get('session_id')}")
    
    operations = result.get('operations', [])
    print(f"Operations count: {len(operations)}")
    
    if operations:
        op = operations[0]
        details = op.get('details', {})
        
        print(f"\nOperation type: {op.get('operation_type')}")
        print(f"Query type: {details.get('query_type')}")
        print(f"Result format: {details.get('result_format')}")
        
        query_result = details.get('query_result', '')
        print(f"\nResult length: {len(query_result)} characters")
        
        # 检查 Markdown 标记
        markdown_marks = {
            'Headers': '#' in query_result,
            'Bold': '**' in query_result,
            'Tables': '|' in query_result,
            'Horizontal Rule': '---' in query_result,
        }
        
        print("\nMarkdown format detection:")
        for mark, found in markdown_marks.items():
            status = "YES" if found else "NO"
            print(f"  {mark}: {status}")
        
        # 保存结果到文件
        with open('query_result.md', 'w', encoding='utf-8') as f:
            f.write(query_result)
        print("\nFull result saved to: query_result.md")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
