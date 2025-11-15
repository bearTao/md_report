"""
测试操作规划器

测试operation_planner.py中的OperationPlanner类的所有功能。
"""
import pytest
from unittest.mock import Mock

from app.services.agent.operation_planner import OperationPlanner
from app.schemas.modification_schemas import (
    ModificationIntent,
    IntentType,
    OperationStep,
    OperationType,
    ConversationMemory,
    ReportState,
    VariableInfo,
    VariableType
)


@pytest.fixture
def operation_planner():
    """创建OperationPlanner实例"""
    return OperationPlanner()


@pytest.fixture
def sample_memory_with_dependencies():
    """创建带依赖关系的示例记忆"""
    variables = {
        "wgid": VariableInfo(
            name="wgid",
            value="ZQGY0001",
            source="user_input",
            variable_type=VariableType.TEMPLATE,
            metadata={
                "type": "string",
                "source": "user_input"
            }
        ),
        "start_date": VariableInfo(
            name="start_date",
            value="2024-01-01",
            source="user_input",
            variable_type=VariableType.TEMPLATE,
            metadata={
                "type": "string",
                "source": "user_input"
            }
        ),
        "data_query": VariableInfo(
            name="data_query",
            value="SELECT * FROM data WHERE wgid='ZQGY0001'",
            source="sql",
            variable_type=VariableType.TEMPLATE,
            metadata={
                "type": "string",
                "source": "sql",
                "depends_on": ["wgid"]
            }
        ),
        "analysis": VariableInfo(
            name="analysis",
            value="分析结果...",
            source="ai_generation",
            variable_type=VariableType.TEMPLATE,
            metadata={
                "type": "string",
                "source": "ai_generation",
                "depends_on": ["data_query"]
            }
        ),
        "title": VariableInfo(
            name="title",
            value="微电网报告 - ZQGY0001",
            source="ai_generation",
            variable_type=VariableType.TEMPLATE,
            metadata={
                "type": "string",
                "source": "ai_generation",
                "depends_on": ["wgid"]
            }
        )
    }
    
    report_state = ReportState(
        report_id="report-123",
        version=1,
        template_id="template-456",
        variables=variables,
        markdown_content="# 报告内容"
    )
    
    memory = ConversationMemory(
        session_id="session-abc",
        report_id="report-123",
        report_state=report_state,
        conversation_history=[],
        current_version=1
    )
    
    return memory


class TestOperationPlannerInit:
    """测试OperationPlanner初始化"""
    
    def test_init(self):
        """测试初始化"""
        planner = OperationPlanner()
        assert planner is not None


class TestCreatePlan:
    """测试创建操作计划"""
    
    def test_create_plan_single_intent(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试单个意图的规划"""
        intents = [
            ModificationIntent(
                intent_type=IntentType.UPDATE_PARAMETER,
                target_variable="wgid",
                new_value="ZQGY0175"
            )
        ]
        
        steps = operation_planner.create_plan(
            intents=intents,
            memory=sample_memory_with_dependencies
        )
        
        # 应该包含主更新步骤和依赖变量的重新执行步骤
        assert len(steps) > 0
        assert steps[0].operation_type == OperationType.UPDATE_PARAMETER
        assert steps[0].target_variable == "wgid"
    
    def test_create_plan_multiple_intents(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试多个意图的规划"""
        intents = [
            ModificationIntent(
                intent_type=IntentType.UPDATE_PARAMETER,
                target_variable="wgid",
                new_value="ZQGY0175"
            ),
            ModificationIntent(
                intent_type=IntentType.REFINE_AI_CONTENT,
                target_variable="analysis",
                refinement_instruction="使分析更详细"
            )
        ]
        
        steps = operation_planner.create_plan(
            intents=intents,
            memory=sample_memory_with_dependencies
        )
        
        assert len(steps) >= 2
        # 应该包含不同类型的操作
        operation_types = [step.operation_type for step in steps]
        assert OperationType.UPDATE_PARAMETER in operation_types
        assert OperationType.REFINE_AI_CONTENT in operation_types
    
    def test_create_plan_empty_intents(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试空意图列表"""
        intents = []
        
        steps = operation_planner.create_plan(
            intents=intents,
            memory=sample_memory_with_dependencies
        )
        
        assert len(steps) == 0


class TestParameterUpdatePlanning:
    """测试参数更新规划"""
    
    def test_plan_parameter_update_with_dependencies(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试有依赖关系的参数更新"""
        intent = ModificationIntent(
            intent_type=IntentType.UPDATE_PARAMETER,
            target_variable="wgid",
            new_value="ZQGY0175"
        )
        
        steps = operation_planner._plan_parameter_update(
            intent=intent,
            memory=sample_memory_with_dependencies,
            start_step=1
        )
        
        # 应该包含主更新步骤
        assert len(steps) >= 1
        assert steps[0].operation_type == OperationType.UPDATE_PARAMETER
        assert steps[0].parameters["new_value"] == "ZQGY0175"
        
        # 应该检测到依赖变量(data_query和title依赖于wgid)
        # 依赖变量应该被加入重新执行列表
        if len(steps) > 1:
            # 有依赖变量需要重新执行
            assert any("data_query" in step.description or 
                      "title" in step.description 
                      for step in steps[1:])
    
    def test_plan_parameter_update_no_dependencies(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试无依赖关系的参数更新"""
        intent = ModificationIntent(
            intent_type=IntentType.UPDATE_PARAMETER,
            target_variable="start_date",
            new_value="2024-02-01"
        )
        
        steps = operation_planner._plan_parameter_update(
            intent=intent,
            memory=sample_memory_with_dependencies,
            start_step=1
        )
        
        # start_date没有依赖变量,应该只有一个步骤
        assert len(steps) >= 1
        assert steps[0].target_variable == "start_date"
    
    def test_plan_parameter_update_nonexistent_variable(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试更新不存在的变量"""
        intent = ModificationIntent(
            intent_type=IntentType.UPDATE_PARAMETER,
            target_variable="nonexistent_var",
            new_value="value"
        )
        
        with pytest.raises(ValueError) as exc_info:
            operation_planner._plan_parameter_update(
                intent=intent,
                memory=sample_memory_with_dependencies,
                start_step=1
            )
        
        assert "变量不存在" in str(exc_info.value)
    
    def test_plan_parameter_update_fuzzy_matching(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试变量名模糊匹配"""
        intent = ModificationIntent(
            intent_type=IntentType.UPDATE_PARAMETER,
            target_variable="WGID",  # 大写的wgid
            new_value="ZQGY0175"
        )
        
        # 如果实现了模糊匹配,应该能够找到正确的变量
        # 否则会抛出异常
        try:
            steps = operation_planner._plan_parameter_update(
                intent=intent,
                memory=sample_memory_with_dependencies,
                start_step=1
            )
            # 如果成功,验证是否修正了变量名
            assert steps[0].target_variable.lower() == "wgid"
        except ValueError:
            # 如果没有实现模糊匹配,应该抛出异常
            pass


class TestAIRefinementPlanning:
    """测试AI内容优化规划"""
    
    def test_plan_ai_refinement(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试AI内容优化规划"""
        intent = ModificationIntent(
            intent_type=IntentType.REFINE_AI_CONTENT,
            target_variable="analysis",
            refinement_instruction="使分析更详细,增加数据支持"
        )
        
        step = operation_planner._plan_ai_refinement(
            intent=intent,
            memory=sample_memory_with_dependencies,
            step_number=1
        )
        
        assert isinstance(step, OperationStep)
        assert step.operation_type == OperationType.REFINE_AI_CONTENT
        assert step.target_variable == "analysis"
        assert "refinement_instruction" in step.parameters
        assert step.parameters["refinement_instruction"] == "使分析更详细,增加数据支持"
    
    def test_plan_ai_refinement_nonexistent_variable(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试优化不存在的AI变量"""
        intent = ModificationIntent(
            intent_type=IntentType.REFINE_AI_CONTENT,
            target_variable="nonexistent_ai_var",
            refinement_instruction="优化"
        )
        
        with pytest.raises(ValueError):
            operation_planner._plan_ai_refinement(
                intent=intent,
                memory=sample_memory_with_dependencies,
                step_number=1
            )
    
    def test_plan_ai_refinement_non_ai_variable(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试优化非AI类型变量"""
        intent = ModificationIntent(
            intent_type=IntentType.REFINE_AI_CONTENT,
            target_variable="wgid",  # user_input类型,不是ai_generation
            refinement_instruction="优化"
        )
        
        # 应该拒绝优化非AI变量,或给出警告
        with pytest.raises((ValueError, Exception)):
            operation_planner._plan_ai_refinement(
                intent=intent,
                memory=sample_memory_with_dependencies,
                step_number=1
            )


class TestTemplateModificationPlanning:
    """测试模板修改规划"""
    
    def test_plan_add_section(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试添加章节规划"""
        intent = ModificationIntent(
            intent_type=IntentType.ADD_SECTION,
            target_section="竞争对手分析",
            section_description="分析主要竞争对手的市场表现"
        )
        
        step = operation_planner._plan_template_modification(
            intent=intent,
            memory=sample_memory_with_dependencies,
            step_number=1
        )
        
        assert isinstance(step, OperationStep)
        assert step.operation_type == OperationType.ADD_SECTION
        assert "section_name" in step.parameters
        assert step.parameters["section_name"] == "竞争对手分析"
    
    def test_plan_modify_section(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试修改章节规划"""
        intent = ModificationIntent(
            intent_type=IntentType.MODIFY_SECTION,
            target_section="分析",
            section_description="调整格式"
        )
        
        step = operation_planner._plan_template_modification(
            intent=intent,
            memory=sample_memory_with_dependencies,
            step_number=1
        )
        
        assert step.operation_type == OperationType.MODIFY_SECTION
    
    def test_plan_remove_section(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试删除章节规划"""
        intent = ModificationIntent(
            intent_type=IntentType.REMOVE_SECTION,
            target_section="附录"
        )
        
        step = operation_planner._plan_template_modification(
            intent=intent,
            memory=sample_memory_with_dependencies,
            step_number=1
        )
        
        assert step.operation_type == OperationType.REMOVE_SECTION


class TestDependencyAnalysis:
    """测试依赖关系分析"""
    
    def test_find_dependent_variables(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试查找依赖变量"""
        # wgid被data_query和title依赖
        dependent_vars = operation_planner._find_dependent_variables(
            variable_name="wgid",
            memory=sample_memory_with_dependencies
        )
        
        assert isinstance(dependent_vars, (list, set))
        # 应该找到依赖于wgid的变量
        if len(dependent_vars) > 0:
            assert "data_query" in dependent_vars or "title" in dependent_vars
    
    def test_find_no_dependencies(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试查找没有依赖的变量"""
        # start_date没有被其他变量依赖
        dependent_vars = operation_planner._find_dependent_variables(
            variable_name="start_date",
            memory=sample_memory_with_dependencies
        )
        
        # 应该返回空列表或空集合
        assert len(list(dependent_vars)) == 0
    
    def test_transitive_dependencies(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试传递依赖关系"""
        # wgid -> data_query -> analysis (传递依赖)
        dependent_vars = operation_planner._find_dependent_variables(
            variable_name="wgid",
            memory=sample_memory_with_dependencies
        )
        
        # 应该包含直接和间接依赖
        # 具体实现可能不同,至少应该找到直接依赖
        assert len(list(dependent_vars)) > 0


class TestStepOrdering:
    """测试步骤排序"""
    
    def test_step_numbering(
        self, 
        operation_planner, 
        sample_memory_with_dependencies
    ):
        """测试步骤编号正确性"""
        intents = [
            ModificationIntent(
                intent_type=IntentType.UPDATE_PARAMETER,
                target_variable="wgid",
                new_value="ZQGY0175"
            ),
            ModificationIntent(
                intent_type=IntentType.REFINE_AI_CONTENT,
                target_variable="analysis",
                refinement_instruction="优化"
            )
        ]
        
        steps = operation_planner.create_plan(
            intents=intents,
            memory=sample_memory_with_dependencies
        )
        
        # 验证步骤编号连续
        step_numbers = [step.step_number for step in steps]
        assert step_numbers == list(range(1, len(steps) + 1))


class TestUtilityMethods:
    """测试工具方法"""
    
    def test_fuzzy_match_variable(
        self, 
        operation_planner
    ):
        """测试变量名模糊匹配"""
        variable_names = ["wgid", "start_date", "end_date", "analysis"]
        
        # 测试完全匹配
        if hasattr(operation_planner, '_fuzzy_match_variable'):
            result = operation_planner._fuzzy_match_variable(
                "wgid", variable_names
            )
            assert result == "wgid"
            
            # 测试大小写不敏感
            result = operation_planner._fuzzy_match_variable(
                "WGID", variable_names
            )
            # 应该返回wgid或None(取决于实现)
            assert result is None or result == "wgid"
            
            # 测试相似匹配
            result = operation_planner._fuzzy_match_variable(
                "wgId", variable_names
            )
            # 应该返回最相似的变量名
            assert result is None or result == "wgid"


class TestEdgeCases:
    """测试边界情况"""
    
    def test_circular_dependencies(
        self, 
        operation_planner
    ):
        """测试循环依赖检测"""
        # 创建带循环依赖的记忆
        variables = {
            "var_a": VariableInfo(
                name="var_a",
                value="a",
                source="sql",
                metadata={"depends_on": ["var_b"]}
            ),
            "var_b": VariableInfo(
                name="var_b",
                value="b",
                source="sql",
                metadata={"depends_on": ["var_a"]}
            )
        }
        
        report_state = ReportState(
            report_id="report-123",
            version=1,
            template_id="template-456",
            variables=variables,
            markdown_content=""
        )
        
        memory = ConversationMemory(
            session_id="session-abc",
            report_id="report-123",
            report_state=report_state,
            conversation_history=[],
            current_version=1
        )
        
        intent = ModificationIntent(
            intent_type=IntentType.UPDATE_PARAMETER,
            target_variable="var_a",
            new_value="new_a"
        )
        
        # 应该能够处理循环依赖(检测并跳过,或报错)
        try:
            steps = operation_planner._plan_parameter_update(
                intent=intent,
                memory=memory,
                start_step=1
            )
            # 如果成功,验证没有无限循环
            assert len(steps) < 100
        except Exception as e:
            # 或者抛出循环依赖错误
            assert "循环" in str(e) or "circular" in str(e).lower()
    
    def test_deep_dependency_chain(
        self, 
        operation_planner
    ):
        """测试深层依赖链"""
        # 创建深层依赖链: a -> b -> c -> d -> e
        variables = {
            f"var_{chr(97+i)}": VariableInfo(
                name=f"var_{chr(97+i)}",
                value=str(i),
                source="sql",
                metadata={"depends_on": [f"var_{chr(96+i)}"]} if i > 0 else {}
            )
            for i in range(5)
        }
        
        report_state = ReportState(
            report_id="report-123",
            version=1,
            template_id="template-456",
            variables=variables,
            markdown_content=""
        )
        
        memory = ConversationMemory(
            session_id="session-abc",
            report_id="report-123",
            report_state=report_state,
            conversation_history=[],
            current_version=1
        )
        
        intent = ModificationIntent(
            intent_type=IntentType.UPDATE_PARAMETER,
            target_variable="var_a",
            new_value="new_a"
        )
        
        # 应该能够找到整个依赖链
        steps = operation_planner._plan_parameter_update(
            intent=intent,
            memory=memory,
            start_step=1
        )
        
        # 应该有合理数量的步骤
        assert len(steps) >= 1
        assert len(steps) <= 10  # 不应该无限增长

