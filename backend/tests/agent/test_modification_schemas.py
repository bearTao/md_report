"""
测试报告修改代理的数据结构

测试modification_schemas.py中定义的所有Pydantic模型的验证和序列化功能。
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas.modification_schemas import (
    # 枚举类型
    IntentType,
    OperationType,
    VariableType,
    # 意图解析相关
    ModificationIntent,
    # 操作执行相关
    ParameterUpdateDetails,
    AIRefinementDetails,
    TemplateModificationDetails,
    Operation,
    OperationStep,
    # 报告状态管理
    VariableInfo,
    ReportState,
    # 对话记忆管理
    ConversationTurn,
    ConversationMemory,
    # 修改结果
    ModificationMetadata,
    ModificationResult,
    # API模型
    ReportModificationRequest,
    ReportModificationResponse,
    ConversationHistoryResponse,
    SaveAsTemplateRequest,
    SaveAsTemplateResponse,
)


class TestEnums:
    """测试枚举类型"""
    
    def test_intent_type_values(self):
        """测试IntentType枚举值"""
        assert IntentType.UPDATE_PARAMETER == "update_parameter"
        assert IntentType.REFINE_AI_CONTENT == "refine_ai_content"
        assert IntentType.ADD_SECTION == "add_section"
        assert IntentType.MODIFY_SECTION == "modify_section"
        assert IntentType.REMOVE_SECTION == "remove_section"
    
    def test_operation_type_values(self):
        """测试OperationType枚举值"""
        assert OperationType.UPDATE_PARAMETER == "update_parameter"
        assert OperationType.REFINE_AI_CONTENT == "refine_ai_content"
        assert OperationType.ADD_SECTION == "add_section"
    
    def test_variable_type_values(self):
        """测试VariableType枚举值"""
        assert VariableType.TEMPLATE == "template"
        assert VariableType.RUNTIME == "runtime"


class TestModificationIntent:
    """测试修改意图模型"""
    
    def test_create_parameter_update_intent(self):
        """测试创建参数更新意图"""
        intent = ModificationIntent(
            intent_type=IntentType.UPDATE_PARAMETER,
            target_variable="wgid",
            new_value="ZQGY0175",
            confidence=0.95
        )
        
        assert intent.intent_type == "update_parameter"
        assert intent.target_variable == "wgid"
        assert intent.new_value == "ZQGY0175"
        assert intent.confidence == 0.95
        assert intent.target_section is None
    
    def test_create_ai_refinement_intent(self):
        """测试创建AI内容优化意图"""
        intent = ModificationIntent(
            intent_type=IntentType.REFINE_AI_CONTENT,
            target_variable="analysis",
            refinement_instruction="使分析更详细，增加数据支持"
        )
        
        assert intent.intent_type == "refine_ai_content"
        assert intent.target_variable == "analysis"
        assert intent.refinement_instruction == "使分析更详细，增加数据支持"
    
    def test_create_add_section_intent(self):
        """测试创建添加章节意图"""
        intent = ModificationIntent(
            intent_type=IntentType.ADD_SECTION,
            target_section="竞争对手分析",
            section_description="分析主要竞争对手的市场表现"
        )
        
        assert intent.intent_type == "add_section"
        assert intent.target_section == "竞争对手分析"
        assert intent.section_description == "分析主要竞争对手的市场表现"
    
    def test_confidence_validation(self):
        """测试置信度范围验证"""
        # 有效范围
        ModificationIntent(
            intent_type=IntentType.UPDATE_PARAMETER,
            target_variable="test",
            confidence=0.0
        )
        ModificationIntent(
            intent_type=IntentType.UPDATE_PARAMETER,
            target_variable="test",
            confidence=1.0
        )
        
        # 无效范围 - 小于0
        with pytest.raises(ValidationError):
            ModificationIntent(
                intent_type=IntentType.UPDATE_PARAMETER,
                target_variable="test",
                confidence=-0.1
            )
        
        # 无效范围 - 大于1
        with pytest.raises(ValidationError):
            ModificationIntent(
                intent_type=IntentType.UPDATE_PARAMETER,
                target_variable="test",
                confidence=1.1
            )


class TestOperationDetails:
    """测试操作详情模型"""
    
    def test_parameter_update_details(self):
        """测试参数更新详情"""
        details = ParameterUpdateDetails(
            variable_name="wgid",
            old_value="ZQGY0001",
            new_value="ZQGY0175",
            dependent_variables=["report_title", "data_query"]
        )
        
        assert details.variable_name == "wgid"
        assert details.old_value == "ZQGY0001"
        assert details.new_value == "ZQGY0175"
        assert len(details.dependent_variables) == 2
        assert "report_title" in details.dependent_variables
    
    def test_ai_refinement_details(self):
        """测试AI优化详情"""
        details = AIRefinementDetails(
            variable_name="analysis",
            instruction="使分析更详细",
            old_prompt="分析市场数据",
            new_prompt="详细分析市场数据，包含趋势和预测",
            old_content_length=500,
            new_content_length=1200
        )
        
        assert details.variable_name == "analysis"
        assert details.instruction == "使分析更详细"
        assert details.old_content_length == 500
        assert details.new_content_length == 1200
    
    def test_template_modification_details(self):
        """测试模板修改详情"""
        details = TemplateModificationDetails(
            modification_type="add",
            section_name="竞争对手分析",
            section_content="## 竞争对手分析\n\n{{ competitor_analysis }}",
            insertion_point="市场分析",
            new_variables=["competitor_analysis", "competitor_data"]
        )
        
        assert details.modification_type == "add"
        assert details.section_name == "竞争对手分析"
        assert "竞争对手分析" in details.section_content
        assert details.insertion_point == "市场分析"
        assert len(details.new_variables) == 2


class TestOperation:
    """测试操作模型"""
    
    def test_create_operation_with_parameter_update(self):
        """测试创建参数更新操作"""
        details = ParameterUpdateDetails(
            variable_name="wgid",
            old_value="ZQGY0001",
            new_value="ZQGY0175",
            dependent_variables=[]
        )
        
        operation = Operation(
            operation_type=OperationType.UPDATE_PARAMETER,
            details=details,
            success=True,
            duration_ms=120,
            cost_usd=0.002
        )
        
        assert operation.operation_type == "update_parameter"
        assert operation.success is True
        assert operation.duration_ms == 120
        assert operation.cost_usd == 0.002
        assert operation.error_message is None
    
    def test_create_failed_operation(self):
        """测试创建失败的操作"""
        details = ParameterUpdateDetails(
            variable_name="invalid_var",
            new_value="test"
        )
        
        operation = Operation(
            operation_type=OperationType.UPDATE_PARAMETER,
            details=details,
            success=False,
            error_message="变量不存在"
        )
        
        assert operation.success is False
        assert operation.error_message == "变量不存在"


class TestOperationStep:
    """测试操作步骤模型"""
    
    def test_create_operation_step(self):
        """测试创建操作步骤"""
        step = OperationStep(
            step_number=1,
            operation_type=OperationType.UPDATE_PARAMETER,
            description="更新参数wgid",
            target_variable="wgid",
            parameters={"new_value": "ZQGY0175"}
        )
        
        assert step.step_number == 1
        assert step.operation_type == "update_parameter"
        assert step.target_variable == "wgid"
        assert step.parameters["new_value"] == "ZQGY0175"


class TestVariableInfo:
    """测试变量信息模型"""
    
    def test_create_template_variable(self):
        """测试创建模板变量"""
        var_info = VariableInfo(
            name="wgid",
            value="ZQGY0175",
            source="user_input",
            variable_type=VariableType.TEMPLATE,
            metadata={"type": "string", "required": True}
        )
        
        assert var_info.name == "wgid"
        assert var_info.value == "ZQGY0175"
        assert var_info.source == "user_input"
        assert var_info.variable_type == "template"
        assert var_info.metadata["type"] == "string"
    
    def test_create_runtime_variable(self):
        """测试创建运行时变量"""
        var_info = VariableInfo(
            name="competitor_analysis",
            value="竞争对手分析内容...",
            source="ai_generation",
            variable_type=VariableType.RUNTIME,
            generation_context={"prompt": "分析竞争对手", "model": "gpt-4"}
        )
        
        assert var_info.variable_type == "runtime"
        assert var_info.generation_context["model"] == "gpt-4"


class TestReportState:
    """测试报告状态模型"""
    
    def test_create_report_state(self):
        """测试创建报告状态"""
        variables = {
            "wgid": VariableInfo(
                name="wgid",
                value="ZQGY0175",
                source="user_input",
                variable_type=VariableType.TEMPLATE
            ),
            "title": VariableInfo(
                name="title",
                value="市场分析报告",
                source="user_input",
                variable_type=VariableType.TEMPLATE
            )
        }
        
        state = ReportState(
            report_id="report-123",
            version=1,
            template_id="template-456",
            variables=variables,
            markdown_content="# 市场分析报告\n\nwgid: ZQGY0175"
        )
        
        assert state.report_id == "report-123"
        assert state.version == 1
        assert state.template_id == "template-456"
        assert len(state.variables) == 2
        assert "wgid" in state.variables
        assert state.variables["wgid"].value == "ZQGY0175"


class TestConversationTurn:
    """测试对话轮次模型"""
    
    def test_create_conversation_turn(self):
        """测试创建对话轮次"""
        intents = [
            ModificationIntent(
                intent_type=IntentType.UPDATE_PARAMETER,
                target_variable="wgid",
                new_value="ZQGY0175"
            )
        ]
        
        operations = [
            Operation(
                operation_type=OperationType.UPDATE_PARAMETER,
                details=ParameterUpdateDetails(
                    variable_name="wgid",
                    new_value="ZQGY0175"
                )
            )
        ]
        
        turn = ConversationTurn(
            turn_number=1,
            user_request="把wgid改成ZQGY0175",
            parsed_intents=intents,
            operations=operations,
            system_response="已将wgid更新为ZQGY0175",
            report_version=2
        )
        
        assert turn.turn_number == 1
        assert len(turn.parsed_intents) == 1
        assert len(turn.operations) == 1
        assert turn.report_version == 2


class TestConversationMemory:
    """测试对话记忆模型"""
    
    def test_create_conversation_memory(self):
        """测试创建对话记忆"""
        report_state = ReportState(
            report_id="report-123",
            version=1,
            template_id="template-456",
            variables={},
            markdown_content=""
        )
        
        memory = ConversationMemory(
            session_id="session-abc",
            report_id="report-123",
            report_state=report_state,
            conversation_history=[],
            current_version=1
        )
        
        assert memory.session_id == "session-abc"
        assert memory.report_id == "report-123"
        assert memory.current_version == 1
        assert len(memory.conversation_history) == 0


class TestModificationResult:
    """测试修改结果模型"""
    
    def test_create_successful_result(self):
        """测试创建成功的修改结果"""
        metadata = ModificationMetadata(
            total_duration_ms=1500,
            total_cost_usd=0.05,
            operations_count=3,
            llm_calls_count=2,
            from_version=1,
            to_version=2
        )
        
        result = ModificationResult(
            success=True,
            report_id="report-123",
            session_id="session-abc",
            operations=[],
            explanation="已成功完成3个操作",
            new_markdown_content="# 更新后的报告内容",
            metadata=metadata
        )
        
        assert result.success is True
        assert result.metadata.operations_count == 3
        assert result.metadata.llm_calls_count == 2
        assert result.error_message is None
    
    def test_create_failed_result(self):
        """测试创建失败的修改结果"""
        metadata = ModificationMetadata(
            total_duration_ms=500,
            total_cost_usd=0.01,
            operations_count=1,
            llm_calls_count=1,
            from_version=1,
            to_version=1
        )
        
        result = ModificationResult(
            success=False,
            report_id="report-123",
            session_id="session-abc",
            operations=[],
            explanation="操作失败",
            new_markdown_content="",
            metadata=metadata,
            error_message="变量不存在"
        )
        
        assert result.success is False
        assert result.error_message == "变量不存在"


class TestAPIModels:
    """测试API请求响应模型"""
    
    def test_report_modification_request(self):
        """测试报告修改请求"""
        request = ReportModificationRequest(
            report_id="report-123",
            user_request="把wgid改成ZQGY0175",
            session_id="session-abc"
        )
        
        assert request.report_id == "report-123"
        assert request.user_request == "把wgid改成ZQGY0175"
        assert request.session_id == "session-abc"
    
    def test_report_modification_request_without_session(self):
        """测试无会话ID的修改请求"""
        request = ReportModificationRequest(
            report_id="report-123",
            user_request="把wgid改成ZQGY0175"
        )
        
        assert request.session_id is None
    
    def test_report_modification_response(self):
        """测试报告修改响应"""
        metadata = ModificationMetadata(
            total_duration_ms=1500,
            total_cost_usd=0.05,
            operations_count=3,
            llm_calls_count=2,
            from_version=1,
            to_version=2
        )
        
        response = ReportModificationResponse(
            success=True,
            session_id="session-abc",
            report_id="report-123",
            new_version=2,
            explanation="已成功更新参数",
            operations_summary=["更新wgid", "重新执行依赖变量"],
            markdown_content="# 更新后的内容",
            metadata=metadata
        )
        
        assert response.success is True
        assert response.new_version == 2
        assert len(response.operations_summary) == 2
    
    def test_conversation_history_response(self):
        """测试对话历史响应"""
        response = ConversationHistoryResponse(
            session_id="session-abc",
            report_id="report-123",
            turns=[],
            context_summary="用户进行了3次修改",
            current_version=4
        )
        
        assert response.session_id == "session-abc"
        assert response.current_version == 4
        assert response.context_summary == "用户进行了3次修改"
    
    def test_save_as_template_request(self):
        """测试保存为模板请求"""
        request = SaveAsTemplateRequest(
            report_id="report-123",
            template_name="自定义分析模板",
            template_description="包含竞争对手分析的市场报告模板"
        )
        
        assert request.report_id == "report-123"
        assert request.template_name == "自定义分析模板"
        assert request.template_description is not None
    
    def test_save_as_template_response(self):
        """测试保存为模板响应"""
        response = SaveAsTemplateResponse(
            success=True,
            template_id="template-789",
            message="模板已成功保存"
        )
        
        assert response.success is True
        assert response.template_id == "template-789"


class TestModelSerialization:
    """测试模型序列化和反序列化"""
    
    def test_modification_intent_serialization(self):
        """测试意图模型的JSON序列化"""
        intent = ModificationIntent(
            intent_type=IntentType.UPDATE_PARAMETER,
            target_variable="wgid",
            new_value="ZQGY0175"
        )
        
        # 序列化
        json_data = intent.model_dump()
        assert json_data["intent_type"] == "update_parameter"
        assert json_data["target_variable"] == "wgid"
        
        # 反序列化
        intent2 = ModificationIntent(**json_data)
        assert intent2.intent_type == intent.intent_type
        assert intent2.target_variable == intent.target_variable
    
    def test_operation_serialization(self):
        """测试操作模型的JSON序列化"""
        operation = Operation(
            operation_type=OperationType.UPDATE_PARAMETER,
            details=ParameterUpdateDetails(
                variable_name="wgid",
                new_value="ZQGY0175"
            ),
            success=True
        )
        
        # 序列化
        json_data = operation.model_dump()
        assert json_data["operation_type"] == "update_parameter"
        assert json_data["details"]["variable_name"] == "wgid"
        
        # 反序列化
        operation2 = Operation(**json_data)
        assert operation2.operation_type == operation.operation_type
        assert operation2.details.variable_name == "wgid"
    
    def test_report_state_serialization(self):
        """测试报告状态模型的JSON序列化"""
        state = ReportState(
            report_id="report-123",
            version=1,
            template_id="template-456",
            variables={
                "wgid": VariableInfo(
                    name="wgid",
                    value="ZQGY0175",
                    source="user_input"
                )
            },
            markdown_content="# Test"
        )
        
        # 序列化
        json_data = state.model_dump()
        assert json_data["report_id"] == "report-123"
        assert "wgid" in json_data["variables"]
        
        # 反序列化
        state2 = ReportState(**json_data)
        assert state2.report_id == state.report_id
        assert "wgid" in state2.variables


class TestModelValidation:
    """测试模型验证规则"""
    
    def test_required_fields(self):
        """测试必填字段验证"""
        # ModificationIntent缺少intent_type
        with pytest.raises(ValidationError) as exc_info:
            ModificationIntent()
        
        assert "intent_type" in str(exc_info.value)
    
    def test_field_types(self):
        """测试字段类型验证"""
        # 错误的intent_type类型
        with pytest.raises(ValidationError):
            ModificationIntent(
                intent_type="invalid_type",  # 不是有效的IntentType
                target_variable="test"
            )
    
    def test_nested_model_validation(self):
        """测试嵌套模型验证"""
        # Operation的details必须是有效的详情模型
        with pytest.raises(ValidationError):
            Operation(
                operation_type=OperationType.UPDATE_PARAMETER,
                details={"invalid": "data"}  # 不是有效的详情模型
            )

