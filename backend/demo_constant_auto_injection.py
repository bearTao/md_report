"""
演示：常量自动注入功能

展示 CONSTANT 变量如何自动预先执行，无需显式声明依赖
"""
import asyncio
from app.core.models import VariableMetadata, VariableSource, VariableStatus, ApiConfig
from app.services.scheduler import ExecutionScheduler
from app.services.context import ExecutionContext
import json


async def demo_auto_injection():
    """演示常量自动注入 - 无需声明依赖"""
    print("=" * 70)
    print("演示：常量自动注入功能")
    print("=" * 70)
    
    # 定义变量元数据
    metadata = {
        # 常量 1：API基础地址
        "api_base_url": VariableMetadata(
            type="string",
            source=VariableSource.CONSTANT,
            description="API基础地址",
            value="http://10.10.20.10:5000"
        ),
        
        # 常量 2：最低薪资标准
        "min_salary_standard": VariableMetadata(
            type="number",
            source=VariableSource.CONSTANT,
            description="公司最低薪资标准",
            value=15000
        ),
        
        # 常量 3：最高薪资标准
        "max_salary_standard": VariableMetadata(
            type="number",
            source=VariableSource.CONSTANT,
            description="公司最高薪资标准",
            value=50000
        ),
        
        # 常量 4：增值税率
        "vat_rate": VariableMetadata(
            type="number",
            source=VariableSource.CONSTANT,
            description="增值税率",
            value=0.13
        ),
        
        # 用户输入：部门名称
        "department_name": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="部门名称",
            required=True
        ),
        
        # API 调用 - 使用多个常量，但不需要声明依赖！
        "salary_query": VariableMetadata(
            type="object",
            source=VariableSource.API,
            description="薪资查询（使用多个常量）",
            required=False,
            dependencies=["department_name"],  # 只需声明非常量依赖
            api_config=ApiConfig(
                endpoint="{{api_base_url}}/api/salary/query",  # 常量自动可用
                method="POST",
                body={
                    "department": "{{department_name}}",
                    "min_salary": "{{min_salary_standard}}",  # 常量自动可用
                    "max_salary": "{{max_salary_standard}}",  # 常量自动可用
                    "vat_rate": "{{vat_rate}}"                # 常量自动可用
                }
            )
        )
    }
    
    print("\n【变量配置】")
    print("\n1. 常量变量（自动预执行）：")
    for var_name, meta in metadata.items():
        if meta.source == VariableSource.CONSTANT:
            print(f"   - {var_name}: {meta.value} ({meta.type})")
    
    print("\n2. 其他变量：")
    for var_name, meta in metadata.items():
        if meta.source != VariableSource.CONSTANT:
            deps = meta.dependencies or []
            print(f"   - {var_name} ({meta.source.value})")
            if deps:
                print(f"     依赖: {deps}")
            else:
                print(f"     依赖: [] (无需声明常量依赖)")
    
    # 创建执行上下文
    user_inputs = {"department_name": "技术部"}
    context = ExecutionContext("demo_task", "demo_template", user_inputs, metadata)
    
    # 创建调度器
    scheduler = ExecutionScheduler()
    
    # 跟踪执行顺序
    execution_order = []
    execution_status = {}
    
    async def progress_callback(var_name, status, result):
        if status == VariableStatus.RUNNING:
            execution_order.append(var_name)
            print(f"\n   执行: {var_name}")
        elif status == VariableStatus.SUCCESS:
            execution_status[var_name] = "✅ 成功"
            if result:
                # Some results may not have execution_time_ms
                exec_time = getattr(result, 'execution_time_ms', 0)
                print(f"   完成: {var_name} (耗时: {exec_time}ms)")
        elif status == VariableStatus.FAILED:
            execution_status[var_name] = "❌ 失败"
            print(f"   失败: {var_name} - {result.error if result else 'Unknown error'}")
    
    print("\n【执行过程】")
    
    # 执行所有变量
    try:
        results = await scheduler.execute_all(context, progress_callback=progress_callback)
    except Exception as e:
        print(f"\n执行异常: {e}")
        # 这是预期的，因为实际 API 服务器可能不可用
    
    print("\n【执行顺序分析】")
    print(f"执行顺序: {' → '.join(execution_order)}")
    
    # 验证常量在前
    constant_vars = [name for name, meta in metadata.items() if meta.source == VariableSource.CONSTANT]
    constant_positions = [execution_order.index(name) for name in constant_vars if name in execution_order]
    
    if constant_positions:
        print(f"\n常量执行位置: {constant_positions}")
        print(f"常量最晚位置: {max(constant_positions)}")
        non_constant_first = len(constant_vars)
        print(f"非常量开始位置: {non_constant_first}")
        print(f"✅ 验证：所有常量在非常量之前执行: {max(constant_positions) < non_constant_first}")
    
    print("\n【常量值验证】")
    print("常量已自动注入到 context，可直接使用：")
    for var_name, meta in metadata.items():
        if meta.source == VariableSource.CONSTANT:
            if context.has_variable(var_name):
                value = context.get_variable(var_name)
                print(f"   ✅ {var_name} = {value!r} (类型: {type(value).__name__})")
            else:
                print(f"   ❌ {var_name} = 未找到")
    
    print("\n【插值演示】")
    print("在其他变量中使用常量（自动类型保持）：")
    
    # 模拟 API body
    api_body = {
        "endpoint": "{{api_base_url}}/api/test",
        "min_salary": "{{min_salary_standard}}",
        "max_salary": "{{max_salary_standard}}",
        "vat_rate": "{{vat_rate}}",
        "message": "查询{{department_name}}的薪资（范围：{{min_salary_standard}}-{{max_salary_standard}}）"
    }
    
    print("\n原始 body:")
    print(json.dumps(api_body, ensure_ascii=False, indent=2))
    
    # 插值处理
    interpolated = context.interpolate_dict(api_body)
    
    print("\n插值后 body:")
    print(json.dumps(interpolated, ensure_ascii=False, indent=2))
    
    print("\n类型验证:")
    print(f"   endpoint: {interpolated['endpoint']!r} ({type(interpolated['endpoint']).__name__})")
    print(f"   min_salary: {interpolated['min_salary']!r} ({type(interpolated['min_salary']).__name__}) ← 数字类型保持！")
    print(f"   max_salary: {interpolated['max_salary']!r} ({type(interpolated['max_salary']).__name__}) ← 数字类型保持！")
    print(f"   vat_rate: {interpolated['vat_rate']!r} ({type(interpolated['vat_rate']).__name__}) ← 浮点类型保持！")
    print(f"   message: {interpolated['message']!r} ({type(interpolated['message']).__name__}) ← 模板字符串")


async def demo_backward_compatibility():
    """演示向后兼容性 - 显式声明依赖仍然有效"""
    print("\n\n" + "=" * 70)
    print("演示：向后兼容性")
    print("=" * 70)
    
    metadata = {
        "api_base_url": VariableMetadata(
            type="string",
            source=VariableSource.CONSTANT,
            description="API基础地址",
            value="http://localhost:5000"
        ),
        
        # 方式 1：不声明常量依赖（新方式）
        "api_call_1": VariableMetadata(
            type="object",
            source=VariableSource.API,
            description="API调用1（新方式：不声明常量依赖）",
            required=False,
            # dependencies 为空或不包含常量
            api_config=ApiConfig(
                endpoint="{{api_base_url}}/api/test1",
                method="GET"
            )
        ),
        
        # 方式 2：显式声明常量依赖（旧方式）
        "api_call_2": VariableMetadata(
            type="object",
            source=VariableSource.API,
            description="API调用2（旧方式：显式声明常量依赖）",
            required=False,
            dependencies=["api_base_url"],  # 显式声明
            api_config=ApiConfig(
                endpoint="{{api_base_url}}/api/test2",
                method="GET"
            )
        )
    }
    
    print("\n【配置对比】")
    print("\n1. api_call_1（新方式）:")
    print(f"   dependencies: {metadata['api_call_1'].dependencies or []}")
    print("   ✅ 无需声明常量依赖")
    
    print("\n2. api_call_2（旧方式）:")
    print(f"   dependencies: {metadata['api_call_2'].dependencies}")
    print("   ✅ 显式声明常量依赖也可以")
    
    context = ExecutionContext("demo_task", "demo_template", {}, metadata)
    scheduler = ExecutionScheduler()
    
    print("\n【执行结果】")
    try:
        await scheduler.execute_all(context)
    except Exception:
        pass  # API 调用会失败，但这不影响演示
    
    # 验证常量在两种方式中都可用
    print("\n常量在两个 API 调用中都可用：")
    print(f"   api_base_url 在 context 中: {context.has_variable('api_base_url')}")
    print(f"   api_base_url 值: {context.get_variable('api_base_url')}")
    print("\n✅ 两种方式都能正常工作，选择你喜欢的即可！")


async def demo_error_handling():
    """演示常量失败的错误处理"""
    print("\n\n" + "=" * 70)
    print("演示：常量失败的错误处理")
    print("=" * 70)
    
    metadata = {
        # 正常的常量
        "good_constant": VariableMetadata(
            type="number",
            source=VariableSource.CONSTANT,
            description="正常的常量",
            value=100
        ),
        
        # 缺少 value 字段的常量（会失败）
        "bad_constant": VariableMetadata(
            type="number",
            source=VariableSource.CONSTANT,
            description="缺少value的常量（会失败）",
            # value=None  # 缺少 value
        ),
        
        # 用户输入（不依赖常量）
        "user_var": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="用户输入",
            required=True
        )
    }
    
    user_inputs = {"user_var": "test_value"}
    context = ExecutionContext("demo_task", "demo_template", user_inputs, metadata)
    scheduler = ExecutionScheduler()
    
    print("\n【执行过程】")
    results = await scheduler.execute_all(context)
    
    print("\n【执行结果】")
    for var_name, result in results.items():
        status_icon = "✅" if result.status == VariableStatus.SUCCESS else "❌"
        print(f"{status_icon} {var_name}: {result.status.value}")
        if result.status == VariableStatus.FAILED:
            print(f"   错误: {result.error}")
    
    print("\n【结论】")
    print("✅ 常量失败不会中断整体执行")
    print("✅ 其他变量继续正常执行")
    print("✅ 失败信息被记录，便于排查")


async def main():
    """主函数"""
    print("\n" + "🚀" * 35)
    print("   常量自动注入功能演示")
    print("🚀" * 35)
    
    # 运行各个演示
    await demo_auto_injection()
    await demo_backward_compatibility()
    await demo_error_handling()
    
    print("\n\n" + "=" * 70)
    print("演示完成！")
    print("=" * 70)
    
    print("\n✅ 功能总结：")
    print("  1. 常量自动预执行：无需手动管理执行顺序")
    print("  2. 无需声明依赖：配置更简洁，减少错误")
    print("  3. 类型自动保持：数字、布尔等类型正确传递")
    print("  4. 向后兼容：现有配置无需修改")
    print("  5. 容错处理：常量失败不影响其他变量")
    
    print("\n💡 使用建议：")
    print("  • 将固定配置值定义为常量")
    print("  • 在其他变量中直接使用，无需声明依赖")
    print("  • 只需声明非常量的依赖关系")
    print("  • 享受更简洁、更直观的配置体验！")


if __name__ == "__main__":
    asyncio.run(main())

