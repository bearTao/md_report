"""
测试参数显示功能

验证 Agent 查询参数时能正确显示实际值而不是 None
"""
import requests
import json


def test_show_parameters():
    """测试显示参数功能"""
    print("=" * 60)
    print("🧪 测试参数显示功能")
    print("=" * 60)
    
    # 1. 获取报告列表
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
    
    # 选择一个报告
    report = reports[0]
    report_id = report["id"]
    print(f"✅ 使用报告: {report['title']}")
    print(f"   报告ID: {report_id}")
    print(f"   任务ID: {report.get('task_id')}")
    
    # 2. 查看任务的输入参数（用于对比）
    if report.get('task_id'):
        print(f"\n2️⃣ 查询任务输入参数...")
        task_response = requests.get(f"http://localhost:8000/api/tasks/{report['task_id']}")
        if task_response.status_code == 200:
            task_data = task_response.json()
            inputs = task_data.get('inputs_json', {})
            print(f"✅ 任务输入参数:")
            for key, value in inputs.items():
                print(f"   - {key}: {value}")
        else:
            print(f"⚠️  无法获取任务信息")
    
    # 3. 使用 Agent 查询参数
    print(f"\n3️⃣ 使用 Agent 查询参数...")
    query_request = "显示所有参数"
    
    response = requests.post(
        f"http://localhost:8000/api/reports/{report_id}/modify",
        params={"user_request": query_request}
    )
    
    if response.status_code != 200:
        print(f"❌ 请求失败: {response.status_code}")
        print(f"错误信息: {response.text}")
        return
    
    result = response.json()
    
    # 4. 检查返回结果
    print("\n" + "=" * 60)
    print("📊 Agent 返回结果")
    print("=" * 60)
    
    if result.get('operations'):
        operation = result['operations'][0]
        details = operation.get('details', {})
        query_result = details.get('query_result', '')
        
        print(f"\n✅ 查询类型: {details.get('query_type')}")
        print(f"✅ 结果格式: {details.get('result_format')}")
        print(f"\n📄 参数列表:")
        print("-" * 60)
        print(query_result)
        print("-" * 60)
        
        # 检查是否有 None 值
        if 'None' in query_result:
            print("\n⚠️  警告: 检测到参数值为 None")
            print("   这可能表示参数值没有正确加载")
        else:
            print("\n✅ 所有参数都有实际值")
    else:
        print("❌ 没有操作记录")
    
    # 5. 显示完整的说明
    explanation = result.get('explanation', '')
    if explanation:
        print(f"\n💬 Agent 说明:")
        print(f"   {explanation}")
    
    return result


def test_get_statistics():
    """测试获取统计信息（也会显示参数统计）"""
    print("\n\n" + "=" * 60)
    print("🧪 测试统计信息功能")
    print("=" * 60)
    
    # 获取报告列表
    response = requests.get("http://localhost:8000/api/reports")
    data = response.json()
    reports = data.get("items", [])
    if not reports:
        print("❌ 没有可用的报告")
        return
    
    report_id = reports[0]["id"]
    
    # 查询统计信息
    query_request = "获取统计信息"
    
    response = requests.post(
        f"http://localhost:8000/api/reports/{report_id}/modify",
        params={"user_request": query_request}
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('operations'):
            details = result['operations'][0].get('details', {})
            query_result = details.get('query_result', '')
            
            print(f"\n📊 统计信息:")
            print("-" * 60)
            print(query_result)
            print("-" * 60)
    else:
        print(f"❌ 请求失败: {response.status_code}")


def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "参数显示功能测试" + " " * 23 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    try:
        # 测试参数显示
        result = test_show_parameters()
        
        if result:
            # 测试统计信息
            test_get_statistics()
            
            print("\n" + "=" * 60)
            print("✅ 测试完成！")
            print("=" * 60)
            print("\n💡 验证要点:")
            print("   1. 参数值应该显示实际值，而不是 None")
            print("   2. 参数值应该与任务输入参数一致")
            print("   3. 统计信息中应该显示正确的参数数量")
            print()
    
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
