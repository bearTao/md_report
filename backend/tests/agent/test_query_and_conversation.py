"""
测试查询和通用对话功能

测试新添加的 QUERY 和 GENERAL_CONVERSATION 意图类型。
"""
import pytest
from datetime import datetime
from app.schemas.modification_schemas import (
    ModificationIntent,
    IntentType,
    OperationStep,
    OperationType,
    ConversationMemory,
    ReportState,
    VariableInfo,
    VariableType,
    QueryDetails,
    GeneralConversationDetails
)
from app.services.agent.operation_planner import OperationPlanner


class TestQueryIntent:
    """测试查询意图"""
    
    def test_query_intent_creation(self):
        """测试查询意图的创建"""
        intent = ModificationIntent(
            intent_type=IntentType.QUERY,
            query_type="show_content",
            query_details={"format": "markdown"},
            confidence=0.95
        )
        
        assert intent.intent_type == IntentType.QUERY
        assert intent.query_type == "show_content"
        assert intent.query_details["format"] == "markdown"
        assert intent.confidence == 0.95
    
    def test_query_intent_types(self):
        """测试不同的查询类型"""
        query_types = [
            "show_content",
            "list_variables",
            "show_parameters",
            "show_sections",
            "get_statistics",
            "show_history"
        ]
        
        for query_type in query_types:
            intent = ModificationIntent(
                intent_type=IntentType.QUERY,
                query_type=query_type,
                confidence=1.0
            )
            assert intent.query_type == query_type


class TestGeneralConversationIntent:
    """测试通用对话意图"""
    
    def test_conversation_intent_creation(self):
        """测试对话意图的创建"""
        intent = ModificationIntent(
            intent_type=IntentType.GENERAL_CONVERSATION,
            conversation_context="问候",
            query_details={"type": "greeting"},
            confidence=1.0
        )
        
        assert intent.intent_type == IntentType.GENERAL_CONVERSATION
        assert intent.conversation_context == "问候"
        assert intent.query_details["type"] == "greeting"
    
    def test_conversation_types(self):
        """测试不同的对话类型"""
        conversation_contexts = [
            "你好",
            "谢谢",
            "这个报告怎么样",
            "有什么建议吗"
        ]
        
        for context in conversation_contexts:
            intent = ModificationIntent(
                intent_type=IntentType.GENERAL_CONVERSATION,
                conversation_context=context,
                confidence=1.0
            )
            assert intent.conversation_context == context


class TestOperationPlanner:
    """测试操作规划器对新意图的支持"""
    
    def setup_method(self):
        """设置测试环境"""
        self.planner = OperationPlanner()
        
        # 创建模拟的对话记忆
        self.memory = ConversationMemory(
            session_id="test_session",
            report_id="test_report",
            report_state=ReportState(
                report_id="test_report",
                template_id="test_template",
                variables={
                    "param1": VariableInfo(
                        name="param1",
                        value="value1",
                        source="user_input",
                        variable_type=VariableType.TEMPLATE
                    )
                },
                markdown_content="# Test Report\n\nContent here."
            )
        )
    
    def test_plan_query_operation(self):
        """测试查询操作规划"""
        intents = [
            ModificationIntent(
                intent_type=IntentType.QUERY,
                query_type="show_content",
                confidence=1.0
            )
        ]
        
        steps = self.planner.create_plan(intents, self.memory)
        
        assert len(steps) == 1
        assert steps[0].operation_type == OperationType.QUERY
        assert steps[0].parameters["query_type"] == "show_content"
    
    def test_plan_conversation_operation(self):
        """测试对话操作规划"""
        intents = [
            ModificationIntent(
                intent_type=IntentType.GENERAL_CONVERSATION,
                conversation_context="你好",
                confidence=1.0
            )
        ]
        
        steps = self.planner.create_plan(intents, self.memory)
        
        assert len(steps) == 1
        assert steps[0].operation_type == OperationType.GENERAL_CONVERSATION
        assert steps[0].parameters["conversation_context"] == "你好"
    
    def test_plan_mixed_operations(self):
        """测试混合操作规划（修改 + 查询）"""
        intents = [
            ModificationIntent(
                intent_type=IntentType.UPDATE_PARAMETER,
                target_variable="param1",
                new_value="new_value",
                confidence=1.0
            ),
            ModificationIntent(
                intent_type=IntentType.QUERY,
                query_type="show_parameters",
                confidence=1.0
            )
        ]
        
        steps = self.planner.create_plan(intents, self.memory)
        
        assert len(steps) == 2
        assert steps[0].operation_type == OperationType.UPDATE_PARAMETER
        assert steps[1].operation_type == OperationType.QUERY


class TestQueryDetails:
    """测试查询详情模型"""
    
    def test_query_details_creation(self):
        """测试查询详情的创建"""
        details = QueryDetails(
            query_type="show_content",
            query_result="# Report Content",
            result_format="markdown"
        )
        
        assert details.query_type == "show_content"
        assert details.query_result == "# Report Content"
        assert details.result_format == "markdown"


class TestGeneralConversationDetails:
    """测试通用对话详情模型"""
    
    def test_conversation_details_creation(self):
        """测试对话详情的创建"""
        details = GeneralConversationDetails(
            user_message="你好",
            system_response="您好！我是报告修改助手。",
            conversation_type="greeting"
        )
        
        assert details.user_message == "你好"
        assert details.system_response == "您好！我是报告修改助手。"
        assert details.conversation_type == "greeting"


class TestIntentTypeEnum:
    """测试意图类型枚举"""
    
    def test_all_intent_types_exist(self):
        """测试所有意图类型都存在"""
        expected_types = [
            "update_parameter",
            "refine_ai_content",
            "add_section",
            "modify_section",
            "remove_section",
            "query",
            "general_conversation"
        ]
        
        for intent_type in expected_types:
            assert hasattr(IntentType, intent_type.upper())
    
    def test_query_and_conversation_types(self):
        """测试新添加的查询和对话类型"""
        assert IntentType.QUERY.value == "query"
        assert IntentType.GENERAL_CONVERSATION.value == "general_conversation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
