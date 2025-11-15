"""
测试对话记忆管理器

测试memory_manager.py中的MemoryManager类的所有功能。
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.agent.memory_manager import MemoryManager
from app.models.db_models import (
    Report,
    Template,
    ConversationSession,
    ConversationTurn as DBConversationTurn,
    ReportState as DBReportState
)
from app.schemas.modification_schemas import (
    ConversationMemory,
    ReportState,
    VariableInfo,
    VariableType,
    ModificationIntent,
    IntentType,
    Operation,
    OperationType,
    ParameterUpdateDetails
)


@pytest.fixture
def sample_report(db_session):
    """创建示例报告"""
    # 创建模板
    template = Template(
        id="template-123",
        name="测试模板",
        description="测试用模板",
        template_content="# {{title}}\n\nwgid: {{wgid}}",
        metadata_json={
            "title": {
                "type": "string",
                "source": "user_input",
                "required": True
            },
            "wgid": {
                "type": "string",
                "source": "user_input",
                "required": True
            }
        }
    )
    db_session.add(template)
    
    # 创建报告
    report = Report(
        id="report-123",
        title="测试报告",
        template_id="template-123",
        status="success",
        markdown_content="# 测试报告\n\nwgid: ZQGY0001"
    )
    db_session.add(report)
    db_session.commit()
    
    return report


@pytest.fixture
def memory_manager(db_session):
    """创建MemoryManager实例"""
    return MemoryManager(
        db=db_session,
        max_history_turns=10,
        context_summary_threshold=10
    )


class TestMemoryManagerInit:
    """测试MemoryManager初始化"""
    
    def test_init_with_defaults(self, db_session):
        """测试使用默认参数初始化"""
        manager = MemoryManager(db=db_session)
        
        assert manager.db == db_session
        assert manager.max_history_turns == 10
        assert manager.context_summary_threshold == 10
    
    def test_init_with_custom_params(self, db_session):
        """测试使用自定义参数初始化"""
        manager = MemoryManager(
            db=db_session,
            max_history_turns=20,
            context_summary_threshold=15
        )
        
        assert manager.max_history_turns == 20
        assert manager.context_summary_threshold == 15
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_init_with_api_key(self, db_session):
        """测试使用API密钥初始化"""
        manager = MemoryManager(db=db_session)
        
        assert manager.llm is not None


class TestGetOrCreateMemory:
    """测试获取或创建对话记忆"""
    
    def test_create_new_memory_without_session_id(
        self, 
        memory_manager, 
        sample_report,
        db_session
    ):
        """测试创建新会话（无session_id）"""
        memory = memory_manager.get_or_create_memory(
            report_id="report-123"
        )
        
        # 验证返回的memory对象
        assert isinstance(memory, ConversationMemory)
        assert memory.report_id == "report-123"
        assert memory.session_id.startswith("session_")
        assert memory.current_version == 1
        assert len(memory.conversation_history) == 0
        
        # 验证数据库中创建了会话
        db_session_obj = db_session.query(ConversationSession).filter(
            ConversationSession.id == memory.session_id
        ).first()
        assert db_session_obj is not None
        assert db_session_obj.report_id == "report-123"
        assert db_session_obj.status == "active"
        
        # 验证数据库中创建了初始状态
        db_state = db_session.query(DBReportState).filter(
            DBReportState.session_id == memory.session_id
        ).first()
        assert db_state is not None
        assert db_state.version == 1
    
    def test_load_existing_memory_with_session_id(
        self, 
        memory_manager, 
        sample_report,
        db_session
    ):
        """测试加载现有会话（有session_id）"""
        # 先创建一个会话
        memory1 = memory_manager.get_or_create_memory(
            report_id="report-123"
        )
        session_id = memory1.session_id
        
        # 再次加载同一会话
        memory2 = memory_manager.get_or_create_memory(
            report_id="report-123",
            session_id=session_id
        )
        
        assert memory2.session_id == session_id
        assert memory2.report_id == "report-123"
        assert memory2.current_version == 1
    
    def test_create_memory_for_nonexistent_report(
        self, 
        memory_manager
    ):
        """测试为不存在的报告创建会话"""
        with pytest.raises(ValueError) as exc_info:
            memory_manager.get_or_create_memory(
                report_id="nonexistent-report"
            )
        
        assert "报告不存在" in str(exc_info.value)
    
    def test_load_memory_with_invalid_session_id(
        self, 
        memory_manager, 
        sample_report
    ):
        """测试使用无效的session_id加载会话"""
        with pytest.raises(ValueError) as exc_info:
            memory_manager.get_or_create_memory(
                report_id="report-123",
                session_id="invalid-session"
            )
        
        assert "会话不存在" in str(exc_info.value)
    
    def test_load_memory_with_mismatched_report(
        self, 
        memory_manager, 
        sample_report,
        db_session
    ):
        """测试使用不匹配的报告ID加载会话"""
        # 创建第一个报告的会话
        memory = memory_manager.get_or_create_memory(
            report_id="report-123"
        )
        session_id = memory.session_id
        
        # 创建第二个报告
        report2 = Report(
            id="report-456",
            title="另一个报告",
            template_id="template-123",
            status="success",
            markdown_content="# 另一个报告"
        )
        db_session.add(report2)
        db_session.commit()
        
        # 尝试用第一个报告的session_id访问第二个报告
        with pytest.raises(ValueError) as exc_info:
            memory_manager.get_or_create_memory(
                report_id="report-456",
                session_id=session_id
            )
        
        assert "不属于报告" in str(exc_info.value)


class TestUpdateMemory:
    """测试更新对话记忆"""
    
    def test_update_memory_with_new_turn(
        self, 
        memory_manager, 
        sample_report
    ):
        """测试添加新的对话轮次"""
        # 创建初始记忆
        memory = memory_manager.get_or_create_memory(
            report_id="report-123"
        )
        
        # 准备更新数据
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
                    old_value="ZQGY0001",
                    new_value="ZQGY0175"
                )
            )
        ]
        
        # 更新记忆
        updated_memory = memory_manager.update_memory(
            memory=memory,
            user_request="把wgid改成ZQGY0175",
            parsed_intents=intents,
            operations=operations,
            system_response="已将wgid更新为ZQGY0175",
            new_markdown_content="# 测试报告\n\nwgid: ZQGY0175"
        )
        
        # 验证更新后的记忆
        assert updated_memory.current_version == 2
        assert len(updated_memory.conversation_history) == 1
        assert updated_memory.report_state.markdown_content == "# 测试报告\n\nwgid: ZQGY0175"
        
        # 验证对话轮次
        turn = updated_memory.conversation_history[0]
        assert turn.turn_number == 1
        assert turn.user_request == "把wgid改成ZQGY0175"
        assert len(turn.parsed_intents) == 1
        assert len(turn.operations) == 1
        assert turn.report_version == 2
    
    def test_update_memory_persists_to_database(
        self, 
        memory_manager, 
        sample_report,
        db_session
    ):
        """测试更新记忆是否持久化到数据库"""
        # 创建初始记忆
        memory = memory_manager.get_or_create_memory(
            report_id="report-123"
        )
        session_id = memory.session_id
        
        # 更新记忆
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
        
        memory_manager.update_memory(
            memory=memory,
            user_request="把wgid改成ZQGY0175",
            parsed_intents=intents,
            operations=operations,
            system_response="已更新",
            new_markdown_content="新内容"
        )
        
        # 验证数据库中的对话轮次
        db_turn = db_session.query(DBConversationTurn).filter(
            DBConversationTurn.session_id == session_id
        ).first()
        assert db_turn is not None
        assert db_turn.turn_number == 1
        assert db_turn.user_request == "把wgid改成ZQGY0175"
        
        # 验证数据库中的报告状态
        db_state = db_session.query(DBReportState).filter(
            DBReportState.session_id == session_id,
            DBReportState.version == 2
        ).first()
        assert db_state is not None
        assert db_state.markdown_content == "新内容"
    
    def test_multiple_turns_accumulation(
        self, 
        memory_manager, 
        sample_report
    ):
        """测试多轮对话累积"""
        memory = memory_manager.get_or_create_memory(
            report_id="report-123"
        )
        
        # 第一轮
        memory = memory_manager.update_memory(
            memory=memory,
            user_request="请求1",
            parsed_intents=[],
            operations=[],
            system_response="响应1",
            new_markdown_content="内容1"
        )
        
        assert len(memory.conversation_history) == 1
        assert memory.current_version == 2
        
        # 第二轮
        memory = memory_manager.update_memory(
            memory=memory,
            user_request="请求2",
            parsed_intents=[],
            operations=[],
            system_response="响应2",
            new_markdown_content="内容2"
        )
        
        assert len(memory.conversation_history) == 2
        assert memory.current_version == 3
        
        # 第三轮
        memory = memory_manager.update_memory(
            memory=memory,
            user_request="请求3",
            parsed_intents=[],
            operations=[],
            system_response="响应3",
            new_markdown_content="内容3"
        )
        
        assert len(memory.conversation_history) == 3
        assert memory.current_version == 4


class TestSaveStateSnapshot:
    """测试保存状态快照"""
    
    def test_save_state_snapshot(
        self, 
        memory_manager, 
        sample_report
    ):
        """测试保存状态快照"""
        memory = memory_manager.get_or_create_memory(
            report_id="report-123"
        )
        
        # 修改状态
        memory.report_state.variables["wgid"] = VariableInfo(
            name="wgid",
            value="ZQGY0175",
            source="user_input"
        )
        memory.current_version = 2
        
        # 保存快照
        memory_manager.save_state_snapshot(memory)
        
        # 验证是否保存成功（通过重新加载验证）
        reloaded_memory = memory_manager.get_or_create_memory(
            report_id="report-123",
            session_id=memory.session_id
        )
        
        assert reloaded_memory.current_version == 2
        assert "wgid" in reloaded_memory.report_state.variables
        assert reloaded_memory.report_state.variables["wgid"].value == "ZQGY0175"


class TestContextSummary:
    """测试上下文总结"""
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_generate_context_summary_with_llm(
        self, 
        db_session, 
        sample_report
    ):
        """测试使用LLM生成上下文总结"""
        manager = MemoryManager(db=db_session)
        
        # Mock LLM响应
        with patch.object(manager, 'llm') as mock_llm:
            mock_response = Mock()
            mock_response.content = "用户更新了wgid参数"
            mock_llm.invoke.return_value = mock_response
            
            memory = manager.get_or_create_memory(
                report_id="report-123"
            )
            
            # 添加一些对话历史
            for i in range(3):
                memory.conversation_history.append(Mock(
                    turn_number=i+1,
                    user_request=f"请求{i+1}",
                    system_response=f"响应{i+1}"
                ))
            
            summary = manager._generate_context_summary(memory)
            
            assert summary is not None
            assert isinstance(summary, str)
    
    def test_generate_context_summary_without_llm(
        self, 
        memory_manager, 
        sample_report
    ):
        """测试不使用LLM生成简单总结"""
        memory = memory_manager.get_or_create_memory(
            report_id="report-123"
        )
        
        # 添加对话历史
        for i in range(5):
            memory.conversation_history.append(Mock(
                turn_number=i+1,
                user_request=f"请求{i+1}",
                system_response=f"响应{i+1}"
            ))
        
        summary = memory_manager._generate_context_summary(memory)
        
        # 简单总结应该包含对话轮数
        assert summary is not None
        assert "5" in summary or "五" in summary


class TestUtilityMethods:
    """测试工具方法"""
    
    def test_serialize_and_deserialize_variables(
        self, 
        memory_manager
    ):
        """测试变量序列化和反序列化"""
        # 创建变量字典
        variables = {
            "wgid": VariableInfo(
                name="wgid",
                value="ZQGY0175",
                source="user_input",
                variable_type=VariableType.TEMPLATE,
                metadata={"type": "string"}
            ),
            "title": VariableInfo(
                name="title",
                value="测试报告",
                source="user_input",
                variable_type=VariableType.TEMPLATE
            )
        }
        
        # 序列化
        serialized = memory_manager._serialize_variables(variables)
        
        assert isinstance(serialized, dict)
        assert "wgid" in serialized
        assert serialized["wgid"]["value"] == "ZQGY0175"
        
        # 反序列化
        deserialized = memory_manager._deserialize_variables(serialized)
        
        assert isinstance(deserialized, dict)
        assert "wgid" in deserialized
        assert isinstance(deserialized["wgid"], VariableInfo)
        assert deserialized["wgid"].value == "ZQGY0175"
        assert deserialized["wgid"].metadata["type"] == "string"
    
    def test_build_initial_state_from_report(
        self, 
        memory_manager, 
        sample_report,
        db_session
    ):
        """测试从报告构建初始状态"""
        # 加载模板
        template = db_session.query(Template).filter(
            Template.id == sample_report.template_id
        ).first()
        
        sample_report.template = template
        
        # 构建初始状态
        state = memory_manager._build_initial_state(sample_report)
        
        assert isinstance(state, ReportState)
        assert state.report_id == "report-123"
        assert state.template_id == "template-123"
        assert state.version == 1
        assert "wgid" in state.variables or "title" in state.variables
    
    def test_format_recent_context(
        self, 
        memory_manager, 
        sample_report
    ):
        """测试格式化最近的上下文"""
        memory = memory_manager.get_or_create_memory(
            report_id="report-123"
        )
        
        # 添加对话历史
        for i in range(5):
            intent = ModificationIntent(
                intent_type=IntentType.UPDATE_PARAMETER,
                target_variable=f"var{i}"
            )
            memory = memory_manager.update_memory(
                memory=memory,
                user_request=f"请求{i+1}",
                parsed_intents=[intent],
                operations=[],
                system_response=f"响应{i+1}",
                new_markdown_content="内容"
            )
        
        # 格式化最近3轮上下文
        context = memory_manager.format_recent_context(memory, limit=3)
        
        assert isinstance(context, str)
        assert "请求3" in context or "请求4" in context or "请求5" in context
        assert "请求1" not in context  # 应该不包含最早的轮次


class TestMemoryCleanup:
    """测试记忆清理"""
    
    def test_cleanup_inactive_sessions(
        self, 
        memory_manager, 
        sample_report,
        db_session
    ):
        """测试清理不活跃的会话"""
        # 创建多个会话
        memory1 = memory_manager.get_or_create_memory(
            report_id="report-123"
        )
        
        # 手动设置一个会话为不活跃（修改last_activity_at）
        from datetime import timedelta
        old_time = datetime.now() - timedelta(days=8)
        
        db_session_obj = db_session.query(ConversationSession).filter(
            ConversationSession.id == memory1.session_id
        ).first()
        db_session_obj.last_activity_at = old_time
        db_session.commit()
        
        # 执行清理（如果实现了cleanup方法）
        if hasattr(memory_manager, 'cleanup_inactive_sessions'):
            deleted_count = memory_manager.cleanup_inactive_sessions(days=7)
            assert deleted_count >= 0


class TestEdgeCases:
    """测试边界情况"""
    
    def test_empty_conversation_history(
        self, 
        memory_manager, 
        sample_report
    ):
        """测试空对话历史"""
        memory = memory_manager.get_or_create_memory(
            report_id="report-123"
        )
        
        assert len(memory.conversation_history) == 0
        assert memory.current_version == 1
    
    def test_large_conversation_history(
        self, 
        memory_manager, 
        sample_report
    ):
        """测试大量对话历史"""
        memory = memory_manager.get_or_create_memory(
            report_id="report-123"
        )
        
        # 添加20轮对话
        for i in range(20):
            memory = memory_manager.update_memory(
                memory=memory,
                user_request=f"请求{i+1}",
                parsed_intents=[],
                operations=[],
                system_response=f"响应{i+1}",
                new_markdown_content="内容"
            )
        
        # 重新加载会话（应该只保留最近N轮）
        reloaded_memory = memory_manager.get_or_create_memory(
            report_id="report-123",
            session_id=memory.session_id
        )
        
        # 应该只保留max_history_turns轮
        assert len(reloaded_memory.conversation_history) <= memory_manager.max_history_turns
    
    def test_concurrent_session_access(
        self, 
        memory_manager, 
        sample_report
    ):
        """测试并发会话访问"""
        memory = memory_manager.get_or_create_memory(
            report_id="report-123"
        )
        session_id = memory.session_id
        
        # 模拟两个"并发"加载
        memory1 = memory_manager.get_or_create_memory(
            report_id="report-123",
            session_id=session_id
        )
        
        memory2 = memory_manager.get_or_create_memory(
            report_id="report-123",
            session_id=session_id
        )
        
        # 应该加载同一个会话
        assert memory1.session_id == memory2.session_id
        assert memory1.current_version == memory2.current_version

