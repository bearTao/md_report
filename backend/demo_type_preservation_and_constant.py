"""
演示：智能类型保持 + CONSTANT 变量类型

这个脚本展示了两个新功能的实际效果：
1. 智能类型保持 - 在 API body 中使用变量时自动保持类型
2. CONSTANT 变量类型 - 定义固定常量值
"""
import asyncio
from app.core.models import VariableMetadata, VariableSource
from app.executors.constant import ConstantExecutor
from app.services.context import ExecutionContext
import json


async def demo_type_preservation():
    """演示类型保持功能"""
    print("=" * 70)
    print("演示 1: 智能类型保持")
    print("=" * 70)
    
    # 创建上下文并设置变量值
    context = ExecutionContext("demo_task", "demo_template", {}, {})
    context.variables = {
        'department_name': '技术部',
        'min_salary': 15000,
        'max_salary': 50000,
        'is_active': True,
        'discount_rate': 0.85,
        'items': ['item1', 'item2', 'item3']
    }
    
    # 模拟 API body
    print("\n【原始 API Body 配置】")
    api_body = {
        "department": "{{department_name}}",      # 纯变量引用 - 保持字符串
        "min_salary": "{{min_salary}}",           # 纯变量引用 - 保持数字
        "max_salary": "{{max_salary}}",           # 纯变量引用 - 保持数字
        "active": "{{is_active}}",                # 纯变量引用 - 保持布尔
        "rate": "{{discount_rate}}",              # 纯变量引用 - 保持浮点
        "items": "{{items}}",                     # 纯变量引用 - 保持数组
        "message": "查询{{department_name}}员工",  # 模板字符串 - 返回字符串
        "salary_info": "薪资范围: {{min_salary}}-{{max_salary}}"  # 模板字符串 - 返回字符串
    }
    print(json.dumps(api_body, ensure_ascii=False, indent=2))
    
    # 进行插值处理
    result = context.interpolate_dict(api_body)
    
    print("\n【插值后的结果】")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\n【类型验证】")
    print(f"✅ department: {result['department']!r} (类型: {type(result['department']).__name__})")
    print(f"✅ min_salary: {result['min_salary']!r} (类型: {type(result['min_salary']).__name__}) ← 保持了数字类型！")
    print(f"✅ max_salary: {result['max_salary']!r} (类型: {type(result['max_salary']).__name__}) ← 保持了数字类型！")
    print(f"✅ active: {result['active']!r} (类型: {type(result['active']).__name__}) ← 保持了布尔类型！")
    print(f"✅ rate: {result['rate']!r} (类型: {type(result['rate']).__name__}) ← 保持了浮点类型！")
    print(f"✅ items: {result['items']!r} (类型: {type(result['items']).__name__}) ← 保持了数组类型！")
    print(f"✅ message: {result['message']!r} (类型: {type(result['message']).__name__}) ← 模板字符串返回字符串")
    print(f"✅ salary_info: {result['salary_info']!r} (类型: {type(result['salary_info']).__name__}) ← 模板字符串返回字符串")


async def demo_constant_variables():
    """演示常量变量功能"""
    print("\n\n" + "=" * 70)
    print("演示 2: CONSTANT 变量类型")
    print("=" * 70)
    
    # 定义常量元数据
    constant_metadata = {
        "min_salary_standard": VariableMetadata(
            type="number",
            source=VariableSource.CONSTANT,
            description="公司最低薪资标准",
            value=15000
        ),
        "max_salary_standard": VariableMetadata(
            type="number",
            source=VariableSource.CONSTANT,
            description="公司最高薪资标准",
            value=50000
        ),
        "company_name": VariableMetadata(
            type="string",
            source=VariableSource.CONSTANT,
            description="公司名称",
            value="XX科技有限公司"
        ),
        "vat_rate": VariableMetadata(
            type="number",
            source=VariableSource.CONSTANT,
            description="增值税率",
            value=0.13
        ),
        "enable_cache": VariableMetadata(
            type="boolean",
            source=VariableSource.CONSTANT,
            description="是否启用缓存",
            value=True
        ),
        "major_cities": VariableMetadata(
            type="array",
            source=VariableSource.CONSTANT,
            description="主要城市列表",
            value=["北京", "上海", "深圳", "杭州", "成都"]
        )
    }
    
    print("\n【定义的常量】")
    for var_name, metadata in constant_metadata.items():
        print(f"  {var_name}: {metadata.value} ({metadata.type})")
    
    # 创建上下文并执行常量
    context = ExecutionContext("demo_task", "demo_template", {}, constant_metadata)
    
    print("\n【执行常量变量】")
    for var_name, metadata in constant_metadata.items():
        executor = ConstantExecutor(var_name, metadata, context)
        result = await executor.execute()
        print(f"  ✅ {var_name}: {result.value}")
    
    # 在 API body 中使用常量
    print("\n【在 API Body 中使用常量】")
    api_body = {
        "company": "{{company_name}}",
        "salary_range": {
            "min": "{{min_salary_standard}}",
            "max": "{{max_salary_standard}}"
        },
        "tax": {
            "vat_rate": "{{vat_rate}}"
        },
        "cities": "{{major_cities}}",
        "settings": {
            "cache_enabled": "{{enable_cache}}"
        },
        "description": "{{company_name}}的薪资标准"
    }
    print(json.dumps(api_body, ensure_ascii=False, indent=2))
    
    # 插值处理
    result = context.interpolate_dict(api_body)
    
    print("\n【插值后的结果（类型已保持）】")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\n【类型验证】")
    print(f"✅ company: {result['company']!r} (类型: {type(result['company']).__name__})")
    print(f"✅ min: {result['salary_range']['min']!r} (类型: {type(result['salary_range']['min']).__name__}) ← 数字类型！")
    print(f"✅ max: {result['salary_range']['max']!r} (类型: {type(result['salary_range']['max']).__name__}) ← 数字类型！")
    print(f"✅ vat_rate: {result['tax']['vat_rate']!r} (类型: {type(result['tax']['vat_rate']).__name__}) ← 浮点类型！")
    print(f"✅ cities: {result['cities']} (类型: {type(result['cities']).__name__}) ← 数组类型！")
    print(f"✅ cache_enabled: {result['settings']['cache_enabled']!r} (类型: {type(result['settings']['cache_enabled']).__name__}) ← 布尔类型！")
    print(f"✅ description: {result['description']!r} (类型: {type(result['description']).__name__}) ← 字符串（模板）")


async def demo_problem_solved():
    """演示解决的实际问题"""
    print("\n\n" + "=" * 70)
    print("演示 3: 对比修复前后的效果")
    print("=" * 70)
    
    print("\n【问题场景】后端 API 要求 min_salary 必须是数字类型")
    
    # 设置变量
    context = ExecutionContext("demo_task", "demo_template", {}, {})
    context.variables = {
        'department_name': '技术部',
        'min_salary_value': 15000  # 这是一个数字
    }
    
    # API body 配置
    api_body = {
        "department": "{{department_name}}",
        "min_salary": "{{min_salary_value}}"
    }
    
    # 插值处理
    result = context.interpolate_dict(api_body)
    
    print("\n【修复后】✅ 类型正确保持")
    print(f"  发送到后端的 body: {json.dumps(result, ensure_ascii=False, indent=2)}")
    print(f"  min_salary 的类型: {type(result['min_salary']).__name__}")
    print(f"  min_salary 的值: {result['min_salary']!r}")
    
    if isinstance(result['min_salary'], int):
        print("\n  ✅ 成功！后端可以正确接收数字类型")
        print("  ✅ 不会出现类型错误")
        print("  ✅ 无需在后端进行类型转换")
    
    print("\n【对比】如果没有类型保持功能")
    print("  修复前: min_salary = \"15000\" (字符串) ❌")
    print("  修复后: min_salary = 15000 (数字) ✅")


async def main():
    """主函数"""
    print("\n" + "🎉" * 35)
    print("   智能类型保持 + CONSTANT 变量类型 功能演示")
    print("🎉" * 35)
    
    # 运行各个演示
    await demo_type_preservation()
    await demo_constant_variables()
    await demo_problem_solved()
    
    print("\n\n" + "=" * 70)
    print("演示完成！")
    print("=" * 70)
    print("\n✅ 功能总结：")
    print("  1. 智能类型保持：纯变量引用保持原始类型，模板字符串返回字符串")
    print("  2. CONSTANT 变量：提供清晰的常量定义方式，支持所有数据类型")
    print("  3. 完美配合：常量 + 类型保持 = 强大的配置能力")
    print("  4. 向后兼容：不影响现有功能")
    print("  5. 零性能开销：只增加一次简单的正则匹配")
    print("\n💡 实际应用场景：")
    print("  • API 请求 body 中需要使用数字、布尔等非字符串类型")
    print("  • 定义业务常量（薪资标准、税率等）")
    print("  • 配置参数（API地址、公司信息等）")
    print("  • 在多个变量间共享固定值")


if __name__ == "__main__":
    asyncio.run(main())

