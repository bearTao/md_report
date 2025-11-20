"""
测试依赖关系检测功能

验证 ParameterUpdateStrategy 和 OperationPlanner 能够正确识别变量依赖关系
"""
from datetime import datetime
from app.services.agent.strategies.parameter_update import ParameterUpdateStrategy
from app.services.agent.operation_planner import OperationPlanner
from app.schemas.modification_schemas import (
    ConversationMemory,
    ReportState,
    VariableInfo,
    VariableType
)


def test_find_direct_dependents():
    """测试依赖变量查找功能"""
    
    # 创建测试用的内存状态
    memory = ConversationMemory(
        session_id="test_session",
        report_id="test_report",
        report_state=ReportState(
            report_id="test_report",
            version=1,
            template_id="test_template",
            variables={
                "wgid": VariableInfo(
                    name="wgid",
                    value="ZQGY0175",
                    source="user_input",
                    variable_type=VariableType.TEMPLATE,
                    metadata={
                        "type": "string",
                        "source": "user_input",
                        "description": "微网格ID"
                    }
                ),
                "overview": VariableInfo(
                    name="overview",
                    value=None,
                    source="sql",
                    variable_type=VariableType.TEMPLATE,
                    metadata={
                        "type": "object",
                        "source": "sql",
                        "description": "微网格概况",
                        "dependencies": ["wgid"]  # 依赖 wgid
                    }
                ),
                "index_scores": VariableInfo(
                    name="index_scores",
                    value=None,
                    source="sql",
                    variable_type=VariableType.TEMPLATE,
                    metadata={
                        "type": "array",
                        "source": "sql",
                        "description": "指标评分",
                        "dependencies": ["wgid"]  # 依赖 wgid
                    }
                ),
                "summary": VariableInfo(
                    name="summary",
                    value=None,
                    source="ai_generation",
                    variable_type=VariableType.TEMPLATE,
                    metadata={
                        "type": "string",
                        "source": "ai_generation",
                        "description": "总结",
                        "dependencies": ["overview", "index_scores"]  # 依赖其他变量
                    }
                )
            }
        )
    )
    
    # 测试 ParameterUpdateStrategy
    strategy = ParameterUpdateStrategy(db=None)
    dependents = strategy._find_direct_dependents("wgid", memory)
    
    # 应该找到 overview 和 index_scores 两个依赖变量
    assert len(dependents) == 2, f"Expected 2 dependents, got {len(dependents)}: {dependents}"
    assert "overview" in dependents
    assert "index_scores" in dependents
    
    print(f"✓ ParameterUpdateStrategy 正确识别出 {len(dependents)} 个依赖变量: {dependents}")
    
    # 测试 OperationPlanner
    planner = OperationPlanner()
    dependent_vars = planner._find_dependent_variables("wgid", memory)
    
    # 应该找到 overview 和 index_scores 两个依赖变量
    assert len(dependent_vars) == 2, f"Expected 2 dependent vars, got {len(dependent_vars)}: {dependent_vars}"
    assert "overview" in dependent_vars
    assert "index_scores" in dependent_vars
    
    print(f"✓ OperationPlanner 正确识别出 {len(dependent_vars)} 个依赖变量: {dependent_vars}")
    
    # 测试级联依赖
    dependents_overview = strategy._find_direct_dependents("overview", memory)
    assert "summary" in dependents_overview, "summary should depend on overview"
    
    print(f"✓ 级联依赖检测正常: summary 依赖 overview")


if __name__ == "__main__":
    test_find_direct_dependents()
    print("\n✅ 所有依赖检测测试通过!")
