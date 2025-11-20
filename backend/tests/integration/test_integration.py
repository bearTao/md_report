"""Integration tests for complete workflow"""
import pytest
from app.services.scheduler import ExecutionScheduler
from app.services.context import ExecutionContext
from app.services.renderer import template_renderer
from app.core.models import VariableMetadata, VariableSource, SystemConfig, UiConfig


@pytest.mark.asyncio
async def test_complete_report_generation():
    """Test complete report generation workflow"""
    
    # Define template metadata
    metadata = {
        "report_title": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="报告标题",
            required=True,
            ui_config=UiConfig(input_type="text", placeholder="请输入标题")
        ),
        "project_id": VariableMetadata(
            type="string",
            source=VariableSource.USER_INPUT,
            description="项目ID",
            required=True,
            ui_config=UiConfig(input_type="text")
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
                        "value": "1.0"
                    }
                }
            )
        )
    }
    
    # User inputs
    user_inputs = {
        "report_title": "Q3项目总结报告",
        "project_id": "PRJ-2025-001"
    }
    
    # Create context
    context = ExecutionContext(
        task_id="task_test_123",
        template_id="tpl_test_456",
        user_inputs=user_inputs,
        metadata=metadata
    )
    
    # Execute all variables
    scheduler = ExecutionScheduler()
    results = await scheduler.execute_all(context)
    
    # Verify all variables executed successfully
    assert len(results) == 3
    assert all(r.status.value == "success" for r in results.values())
    
    # Verify variables in context
    assert context.get_variable("report_title") == "Q3项目总结报告"
    assert context.get_variable("project_id") == "PRJ-2025-001"
    
    gen_info = context.get_variable("generation_info")
    assert "timestamp" in gen_info
    assert "report_id" in gen_info
    assert gen_info["version"] == "1.0"
    
    # Define template
    template_content = """# {{report_title}}

**项目ID**: {{project_id}}
**生成时间**: {{generation_info.timestamp}}
**报告ID**: {{generation_info.report_id}}
**版本**: {{generation_info.version}}

## 项目概况

本报告总结了项目 {{project_id}} 在本季度的进展情况。

---
*本报告由系统自动生成*
"""
    
    # Render template
    all_variables = context.get_all_variables()
    markdown = template_renderer.render(template_content, all_variables)
    
    # Verify rendered output
    assert "# Q3项目总结报告" in markdown
    assert "**项目ID**: PRJ-2025-001" in markdown
    assert "**版本**: 1.0" in markdown
    assert "本报告总结了项目 PRJ-2025-001" in markdown
    
    print("\n" + "="*60)
    print("Generated Report:")
    print("="*60)
    print(markdown)
    print("="*60)


@pytest.mark.asyncio
async def test_dependency_resolution():
    """Test variable dependency resolution"""
    
    metadata = {
        "base_value": VariableMetadata(
            type="number",
            source=VariableSource.USER_INPUT,
            description="基础值",
            required=True
        ),
        "multiplier": VariableMetadata(
            type="number",
            source=VariableSource.USER_INPUT,
            description="乘数",
            required=True
        ),
        "result_description": VariableMetadata(
            type="string",
            source=VariableSource.SYSTEM,
            description="结果描述",
            required=True,
            dependencies=["base_value", "multiplier"],
            system_config=SystemConfig(
                fields={
                    "desc": {
                        "value": "Calculation completed"
                    }
                }
            )
        )
    }
    
    user_inputs = {
        "base_value": 10,
        "multiplier": 5
    }
    
    context = ExecutionContext(
        task_id="task_dep_test",
        template_id="tpl_dep_test",
        user_inputs=user_inputs,
        metadata=metadata
    )
    
    scheduler = ExecutionScheduler()
    
    # Build DAG
    dag = scheduler.build_dag(metadata)
    batches = scheduler.get_execution_batches(dag)
    
    # Should have 2 batches
    assert len(batches) == 2
    
    # First batch: base_value and multiplier (no dependencies)
    assert set(batches[0]) == {"base_value", "multiplier"}
    
    # Second batch: result_description (depends on first batch)
    assert batches[1] == ["result_description"]
    
    # Execute all
    results = await scheduler.execute_all(context)
    
    assert len(results) == 3
    assert all(r.status.value == "success" for r in results.values())

