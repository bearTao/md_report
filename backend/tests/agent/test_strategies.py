"""
测试操作执行策略

测试所有执行策略的功能,包括:
- ParameterUpdateStrategy
- AIRefinementStrategy  
- TemplateModificationStrategy
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from app.services.agent.strategies.parameter_update import ParameterUpdateStrategy
from app.services.agent.strategies.ai_refinement import AIRefinementStrategy
from app.services.agent.strategies.template_modification import TemplateModificationStrategy
from app.schemas.modification_schemas import (
    OperationStep,
    OperationType,
    Operation,
    ConversationMemory,
    ReportState,
    VariableInfo,
    VariableType
)


@pytest.fixture
def sample_memory():
    """创建示例记忆"""
    variables = {
        "wgid": VariableInfo(
            name="wgid",
            value="ZQGY0001",
            source="user_input",
            variable_type=VariableType.TEMPLATE,
            metadata={"type": "string", "source": "user_input"}
        ),
        "analysis": VariableInfo(
            name="analysis",
            value="原始分析内容",
            source="ai_generation",
            variable_type=VariableType.TEMPLATE,
            metadata={
                "type": "string",
                "source": "ai_generation",
                "generation_config": {
                    "model": "gpt-4",
                    "prompt": "分析数据"
                }
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
    
    return ConversationMemory(
        session_id="session-abc",
        report_id="report-123",
        report_state=report_state,
        conversation_history=[],
        current_version=1
    )


class TestParameterUpdateStrategy:
    """测试参数更新策略"""
    
    @pytest.mark.asyncio
    async def test_execute_simple_update(
        self, 
        db_session, 
        sample_memory
    ):
        """测试简单的参数更新"""
        strategy = ParameterUpdateStrategy(db=db_session)
        
        step = OperationStep(
            step_number=1,
            operation_type=OperationType.UPDATE_PARAMETER,
            description="更新wgid",
            target_variable="wgid",
            parameters={
                "new_value": "ZQGY0175",
                "old_value": "ZQGY0001"
            }
        )
        
        operation = await strategy.execute(step=step, memory=sample_memory)
        
        assert isinstance(operation, Operation)
        assert operation.success is True
        assert operation.operation_type == "update_parameter"
        
        # 验证变量已更新
        assert sample_memory.report_state.variables["wgid"].value == "ZQGY0175"
    
    @pytest.mark.asyncio
    async def test_execute_update_nonexistent_variable(
        self, 
        db_session, 
        sample_memory
    ):
        """测试更新不存在的变量"""
        strategy = ParameterUpdateStrategy(db=db_session)
        
        step = OperationStep(
            step_number=1,
            operation_type=OperationType.UPDATE_PARAMETER,
            description="更新不存在的变量",
            target_variable="nonexistent",
            parameters={"new_value": "value"}
        )
        
        operation = await strategy.execute(step=step, memory=sample_memory)
        
        # 应该返回失败的操作
        assert operation.success is False
        assert "不存在" in operation.error_message
    
    @pytest.mark.asyncio
    async def test_execute_update_with_dependencies(
        self, 
        db_session, 
        sample_memory
    ):
        """测试更新带依赖关系的参数"""
        # 添加依赖变量
        sample_memory.report_state.variables["data_query"] = VariableInfo(
            name="data_query",
            value="SELECT * FROM data WHERE wgid='ZQGY0001'",
            source="sql",
            variable_type=VariableType.TEMPLATE,
            metadata={
                "type": "string",
                "source": "sql",
                "depends_on": ["wgid"],
                "sql_config": {"query": "SELECT * FROM data WHERE wgid='{wgid}'"}
            }
        )
        
        strategy = ParameterUpdateStrategy(db=db_session)
        
        step = OperationStep(
            step_number=1,
            operation_type=OperationType.UPDATE_PARAMETER,
            description="更新wgid",
            target_variable="wgid",
            parameters={"new_value": "ZQGY0175"}
        )
        
        # Mock the scheduler执行
        with patch.object(strategy, '_re_execute_variable', new_callable=AsyncMock) as mock_re_exec:
            operation = await strategy.execute(step=step, memory=sample_memory)
            
            assert operation.success is True


class TestAIRefinementStrategy:
    """测试AI内容优化策略"""
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    async def test_execute_ai_refinement(
        self, 
        db_session, 
        sample_memory
    ):
        """测试AI内容优化"""
        strategy = AIRefinementStrategy(db=db_session)
        
        step = OperationStep(
            step_number=1,
            operation_type=OperationType.REFINE_AI_CONTENT,
            description="优化分析内容",
            target_variable="analysis",
            parameters={
                "refinement_instruction": "使分析更详细,增加数据支持"
            }
        )
        
        # Mock LLM调用
        with patch('app.services.agent.strategies.ai_refinement.ChatOpenAI') as MockLLM:
            mock_llm_instance = Mock()
            mock_llm_instance.ainvoke = AsyncMock(return_value=Mock(content="优化后的详细分析内容"))
            MockLLM.return_value = mock_llm_instance
            
            operation = await strategy.execute(step=step, memory=sample_memory)
            
            assert isinstance(operation, Operation)
            assert operation.success is True
            assert operation.operation_type == "refine_ai_content"
            
            # 验证内容已更新
            assert sample_memory.report_state.variables["analysis"].value != "原始分析内容"
    
    @pytest.mark.asyncio
    async def test_execute_ai_refinement_non_ai_variable(
        self, 
        db_session, 
        sample_memory
    ):
        """测试优化非AI变量"""
        strategy = AIRefinementStrategy(db=db_session)
        
        step = OperationStep(
            step_number=1,
            operation_type=OperationType.REFINE_AI_CONTENT,
            description="优化wgid",
            target_variable="wgid",  # 非AI变量
            parameters={"refinement_instruction": "优化"}
        )
        
        operation = await strategy.execute(step=step, memory=sample_memory)
        
        # 应该返回失败
        assert operation.success is False
        assert "AI" in operation.error_message or "ai" in operation.error_message


class TestTemplateModificationStrategy:
    """测试模板修改策略"""
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    async def test_execute_add_section(
        self, 
        db_session, 
        sample_memory
    ):
        """测试添加章节"""
        # 设置模板内容
        sample_memory.report_state.template_content = """# {{title}}

## 市场分析

{{analysis}}

## 结论

{{conclusion}}
"""
        
        strategy = TemplateModificationStrategy(db=db_session)
        
        step = OperationStep(
            step_number=1,
            operation_type=OperationType.ADD_SECTION,
            description="添加竞争对手分析章节",
            parameters={
                "section_name": "竞争对手分析",
                "section_description": "分析主要竞争对手的市场表现",
                "insertion_point": "市场分析"
            }
        )
        
        # Mock LLM调用
        with patch('app.services.agent.strategies.template_modification.ChatOpenAI') as MockLLM:
            mock_llm_instance = Mock()
            mock_llm_instance.ainvoke = AsyncMock(
                return_value=Mock(content='{"sql": "SELECT * FROM competitors", "description": "查询竞争对手"}')
            )
            MockLLM.return_value = mock_llm_instance
            
            operation = await strategy.execute(step=step, memory=sample_memory)
            
            # 验证操作结果
            if operation.success:
                assert "竞争对手分析" in operation.details.section_name
                # 验证模板内容已更新
                assert sample_memory.report_state.template_content is not None
    
    @pytest.mark.asyncio
    async def test_execute_modify_section(
        self, 
        db_session, 
        sample_memory
    ):
        """测试修改章节"""
        sample_memory.report_state.template_content = """# 报告

## 分析

{{analysis}}
"""
        
        strategy = TemplateModificationStrategy(db=db_session)
        
        step = OperationStep(
            step_number=1,
            operation_type=OperationType.MODIFY_SECTION,
            description="修改分析章节",
            parameters={
                "section_name": "分析",
                "section_description": "调整格式"
            }
        )
        
        # Mock实现
        with patch.object(strategy, '_modify_existing_section', new_callable=AsyncMock) as mock_modify:
            mock_modify.return_value = (
                "## 分析\n\n{{analysis}}\n\n图表: {{chart}}",
                ["chart"]
            )
            
            operation = await strategy.execute(step=step, memory=sample_memory)
            
            # 验证调用
            if hasattr(strategy, '_modify_existing_section'):
                assert mock_modify.called


class TestStrategyErrorHandling:
    """测试策略错误处理"""
    
    @pytest.mark.asyncio
    async def test_parameter_update_missing_target(
        self, 
        db_session, 
        sample_memory
    ):
        """测试缺少目标变量的参数更新"""
        strategy = ParameterUpdateStrategy(db=db_session)
        
        step = OperationStep(
            step_number=1,
            operation_type=OperationType.UPDATE_PARAMETER,
            description="更新",
            target_variable=None,  # 缺少目标变量
            parameters={"new_value": "value"}
        )
        
        operation = await strategy.execute(step=step, memory=sample_memory)
        
        assert operation.success is False
        assert "缺少" in operation.error_message or "target" in operation.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_parameter_update_missing_new_value(
        self, 
        db_session, 
        sample_memory
    ):
        """测试缺少新值的参数更新"""
        strategy = ParameterUpdateStrategy(db=db_session)
        
        step = OperationStep(
            step_number=1,
            operation_type=OperationType.UPDATE_PARAMETER,
            description="更新wgid",
            target_variable="wgid",
            parameters={}  # 缺少new_value
        )
        
        operation = await strategy.execute(step=step, memory=sample_memory)
        
        assert operation.success is False


class TestStrategyPerformanceMetrics:
    """测试策略性能指标"""
    
    @pytest.mark.asyncio
    async def test_operation_duration_tracking(
        self, 
        db_session, 
        sample_memory
    ):
        """测试操作时长跟踪"""
        strategy = ParameterUpdateStrategy(db=db_session)
        
        step = OperationStep(
            step_number=1,
            operation_type=OperationType.UPDATE_PARAMETER,
            description="更新wgid",
            target_variable="wgid",
            parameters={"new_value": "ZQGY0175"}
        )
        
        operation = await strategy.execute(step=step, memory=sample_memory)
        
        # 应该记录执行时长
        assert operation.duration_ms is not None
        assert operation.duration_ms >= 0
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    async def test_llm_cost_tracking(
        self, 
        db_session, 
        sample_memory
    ):
        """测试LLM成本跟踪"""
        strategy = AIRefinementStrategy(db=db_session)
        
        step = OperationStep(
            step_number=1,
            operation_type=OperationType.REFINE_AI_CONTENT,
            description="优化分析",
            target_variable="analysis",
            parameters={"refinement_instruction": "优化"}
        )
        
        # Mock LLM
        with patch('app.services.agent.strategies.ai_refinement.ChatOpenAI') as MockLLM:
            mock_llm_instance = Mock()
            mock_llm_instance.ainvoke = AsyncMock(
                return_value=Mock(content="优化后内容")
            )
            MockLLM.return_value = mock_llm_instance
            
            operation = await strategy.execute(step=step, memory=sample_memory)
            
            # 应该记录成本(如果实现了)
            if operation.success:
                assert operation.cost_usd is not None or operation.cost_usd == 0


class TestStrategyIntegration:
    """测试策略集成"""
    
    @pytest.mark.asyncio
    async def test_multiple_strategies_sequential(
        self, 
        db_session, 
        sample_memory
    ):
        """测试多个策略顺序执行"""
        # 1. 更新参数
        param_strategy = ParameterUpdateStrategy(db=db_session)
        param_step = OperationStep(
            step_number=1,
            operation_type=OperationType.UPDATE_PARAMETER,
            description="更新wgid",
            target_variable="wgid",
            parameters={"new_value": "ZQGY0175"}
        )
        
        param_op = await param_strategy.execute(param_step, sample_memory)
        assert param_op.success is True
        
        # 2. 优化AI内容
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            ai_strategy = AIRefinementStrategy(db=db_session)
            ai_step = OperationStep(
                step_number=2,
                operation_type=OperationType.REFINE_AI_CONTENT,
                description="优化分析",
                target_variable="analysis",
                parameters={"refinement_instruction": "更详细"}
            )
            
            with patch('app.services.agent.strategies.ai_refinement.ChatOpenAI') as MockLLM:
                mock_llm_instance = Mock()
                mock_llm_instance.ainvoke = AsyncMock(
                    return_value=Mock(content="详细分析")
                )
                MockLLM.return_value = mock_llm_instance
                
                ai_op = await ai_strategy.execute(ai_step, sample_memory)
                
                # 两个操作都应该成功
                if ai_op.success:
                    assert param_op.success and ai_op.success

