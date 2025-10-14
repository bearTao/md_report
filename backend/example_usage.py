"""
示例：完整的报告生成流程演示
运行: python example_usage.py
"""
import asyncio
from app.services.scheduler import ExecutionScheduler
from app.services.context import ExecutionContext
from app.services.renderer import template_renderer
from app.core.models import (
    VariableMetadata, VariableSource, SystemConfig, UiConfig, VariableStatus
)


async def example_simple_report():
    """示例1: 简单的项目报告生成"""
    print("=" * 60)
    print("示例1: 简单项目报告生成")
    print("=" * 60)
    
    # 定义变量元数据
    metadata = {
        "report_title": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="报告标题",
            required=True,
            ui_config=UiConfig(
                input_type="text",
                placeholder="请输入报告标题"
            )
        ),
        "project_name": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="项目名称",
            required=True,
            ui_config=UiConfig(input_type="text")
        ),
        "report_date": VariableMetadata(
            type="string",
            source=VariableSource.SYSTEM,
            description="报告日期",
            required=True,
            system_config=SystemConfig(
                fields={
                    "date": {
                        "generator": "datetime",
                        "format": "%Y年%m月%d日"
                    }
                }
            )
        ),
        "generation_info": VariableMetadata(
            type="object",
            source=VariableSource.SYSTEM,
            description="生成信息",
            required=True,
            system_config=SystemConfig(
                fields={
                    "timestamp": {
                        "generator": "datetime",
                        "format": "%Y-%m-%d %H:%M:%S"
                    },
                    "report_id": {
                        "generator": "uuid"
                    },
                    "version": {
                        "value": "1.0.0"
                    }
                }
            )
        )
    }
    
    # 用户输入
    user_inputs = {
        "report_title": "2025年Q3季度总结报告",
        "project_name": "智能报告生成系统"
    }
    
    # 创建执行上下文
    context = ExecutionContext(
        task_id="demo_task_001",
        template_id="demo_template_001",
        user_inputs=user_inputs,
        metadata=metadata
    )
    
    # 执行所有变量
    scheduler = ExecutionScheduler()
    
    print("\n执行变量...")
    results = await scheduler.execute_all(context)
    
    # 打印执行结果
    print("\n变量执行结果:")
    for var_name, result in results.items():
        status_icon = "✅" if result.status == VariableStatus.SUCCESS else "❌"
        print(f"{status_icon} {var_name}: {result.status.value} ({result.duration_ms}ms)")
    
    # 定义模板
    template_content = """# {{report_title}}

## 项目信息

- **项目名称**: {{project_name}}
- **报告日期**: {{report_date}}
- **报告版本**: {{generation_info.version}}

## 生成信息

- **生成时间**: {{generation_info.timestamp}}
- **报告ID**: {{generation_info.report_id}}

## 项目概况

本报告总结了「{{project_name}}」项目在本季度的主要工作进展、取得的成果以及下一步的工作计划。

## 工作亮点

1. 完成核心功能开发
2. 通过系统测试
3. 优化用户体验

---
*本报告由系统自动生成于 {{generation_info.timestamp}}*
"""
    
    # 渲染模板
    print("\n渲染报告...")
    markdown = template_renderer.render(template_content, context.get_all_variables())
    
    # 输出结果
    print("\n" + "=" * 60)
    print("生成的Markdown报告:")
    print("=" * 60)
    print(markdown)
    print("=" * 60)


async def example_with_dependencies():
    """示例2: 带依赖关系的变量执行"""
    print("\n\n" + "=" * 60)
    print("示例2: 带依赖关系的变量执行")
    print("=" * 60)
    
    metadata = {
        "user_name": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="用户名",
            required=True
        ),
        "department": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="部门",
            required=True
        ),
        "greeting_message": VariableMetadata(
            type="string",
            source=VariableSource.SYSTEM,
            description="问候语",
            required=True,
            dependencies=["user_name", "department"],  # 依赖前两个变量
            system_config=SystemConfig(
                fields={
                    "message": {
                        "value": "已生成 {{user_name}} 的问候语，部门为 {{department}}"
                    }
                }
            )
        )
    }
    
    user_inputs = {
        "user_name": "张三",
        "department": "技术部"
    }
    
    context = ExecutionContext(
        task_id="demo_task_002",
        template_id="demo_template_002",
        user_inputs=user_inputs,
        metadata=metadata
    )
    
    scheduler = ExecutionScheduler()
    
    # 构建DAG并显示执行计划
    dag = scheduler.build_dag(metadata)
    batches = scheduler.get_execution_batches(dag)
    
    print("\n执行计划（按批次）:")
    for i, batch in enumerate(batches, 1):
        print(f"批次 {i}: {', '.join(batch)}")
    
    print("\n开始执行...")
    results = await scheduler.execute_all(context)
    
    print("\n执行结果:")
    for var_name, result in results.items():
        status_icon = "✅" if result.status == VariableStatus.SUCCESS else "❌"
        value_preview = str(result.value)[:50]
        print(f"{status_icon} {var_name}: {value_preview}")
    
    # 使用变量插值功能
    template = """
员工信息卡片
============

姓名: {{user_name}}
部门: {{department}}
状态: {{greeting_message}}

欢迎 {{user_name}} 加入 {{department}}！
"""
    
    markdown = template_renderer.render(template, context.get_all_variables())
    print("\n生成的内容:")
    print(markdown)


async def main():
    """主函数"""
    # 运行示例1
    await example_simple_report()
    
    # 运行示例2
    await example_with_dependencies()
    
    print("\n" + "=" * 60)
    print("所有示例执行完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

