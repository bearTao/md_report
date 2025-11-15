"""
测试意图解析器

测试intent_parser.py中的IntentParser类的所有功能,包括LLM集成和意图识别。
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from langchain_core.messages import AIMessage
from datetime import datetime
from app.services.agent.intent_parser import IntentParser, IntentParserOutput
from app.schemas.modification_schemas import (
    ModificationIntent,
    IntentType,
    ConversationMemory,
    ReportState,
    VariableInfo,
    VariableType
)


@pytest.fixture
def mock_llm():
    """创建模拟的LLM对象"""
    llm = Mock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def sample_memory():
    """创建示例对话记忆"""
    variables = {
        "wgid": VariableInfo(
            name="wgid",
            value="ZQGY0001",
            source="user_input",
            variable_type=VariableType.TEMPLATE
        ),
        "title": VariableInfo(
            name="title",
            value="市场分析报告",
            source="user_input",
            variable_type=VariableType.TEMPLATE
        ),
        "analysis": VariableInfo(
            name="analysis",
            value="分析内容...",
            source="ai_generation",
            variable_type=VariableType.TEMPLATE
        )
    }
    
    report_state = ReportState(
        report_id="report-123",
        version=1,
        template_id="template-456",
        variables=variables,
        markdown_content="# 市场分析报告"
    )
    
    memory = ConversationMemory(
        session_id="session-abc",
        report_id="report-123",
        report_state=report_state,
        conversation_history=[],
        current_version=1
    )
    
    return memory


@pytest.fixture
@patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
def intent_parser():
    """创建IntentParser实例"""
    return IntentParser(api_key="test-key")


class TestIntentParserInit:
    """测试IntentParser初始化"""
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_init_with_env_var(self):
        """测试使用环境变量初始化"""
        parser = IntentParser()
        
        assert parser.llm is not None
        assert parser.output_parser is not None
        assert parser.prompt_template is not None
    
    def test_init_with_api_key(self):
        """测试使用API密钥初始化"""
        parser = IntentParser(api_key="test-key")
        
        assert parser.api_key == "test-key"
        assert parser.llm is not None
    
    def test_init_without_api_key(self):
        """测试无API密钥初始化应该失败"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                IntentParser()
            
            assert "API密钥未配置" in str(exc_info.value)
    
    def test_init_with_custom_model(self):
        """测试使用自定义模型"""
        parser = IntentParser(
            api_key="test-key",
            model="gpt-3.5-turbo",
            temperature=0.5
        )
        
        assert parser.llm.model_name == "gpt-3.5-turbo"
        assert parser.llm.temperature == 0.5


class TestParseParameterUpdate:
    """测试参数更新意图解析"""
    
    @pytest.mark.asyncio
    async def test_parse_simple_parameter_update(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试解析简单的参数更新请求"""
        # Mock LLM响应
        mock_response = AIMessage(content="""{
            "intents": [
                {
                    "intent_type": "update_parameter",
                    "target_variable": "wgid",
                    "new_value": "ZQGY0175",
                    "confidence": 0.95
                }
            ],
            "confidence": 0.95,
            "clarification_needed": false
        }""")
        
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.return_value = mock_response
            
            intents = await intent_parser.parse(
                user_request="把wgid改成ZQGY0175",
                memory=sample_memory
            )
            
            assert len(intents) == 1
            assert intents[0].intent_type == IntentType.UPDATE_PARAMETER
            assert intents[0].target_variable == "wgid"
            assert intents[0].new_value == "ZQGY0175"
            assert intents[0].confidence == 0.95
    
    @pytest.mark.asyncio
    async def test_parse_multiple_parameter_updates(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试解析多个参数更新"""
        mock_response = AIMessage(content="""{
            "intents": [
                {
                    "intent_type": "update_parameter",
                    "target_variable": "wgid",
                    "new_value": "ZQGY0175",
                    "confidence": 0.9
                },
                {
                    "intent_type": "update_parameter",
                    "target_variable": "title",
                    "new_value": "新标题",
                    "confidence": 0.9
                }
            ],
            "confidence": 0.9,
            "clarification_needed": false
        }""")
        
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.return_value = mock_response
            
            intents = await intent_parser.parse(
                user_request="把wgid改成ZQGY0175,同时将标题改为'新标题'",
                memory=sample_memory
            )
            
            assert len(intents) == 2
            assert intents[0].intent_type == IntentType.UPDATE_PARAMETER
            assert intents[1].intent_type == IntentType.UPDATE_PARAMETER


class TestParseAIRefinement:
    """测试AI内容优化意图解析"""
    
    @pytest.mark.asyncio
    async def test_parse_ai_refinement(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试解析AI内容优化请求"""
        mock_response = AIMessage(content="""{
            "intents": [
                {
                    "intent_type": "refine_ai_content",
                    "target_variable": "analysis",
                    "refinement_instruction": "使分析更详细,增加数据支持",
                    "confidence": 0.88
                }
            ],
            "confidence": 0.88,
            "clarification_needed": false
        }""")
        
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.return_value = mock_response
            
            intents = await intent_parser.parse(
                user_request="让分析更详细一些",
                memory=sample_memory
            )
            
            assert len(intents) == 1
            assert intents[0].intent_type == IntentType.REFINE_AI_CONTENT
            assert intents[0].target_variable == "analysis"
            assert intents[0].refinement_instruction is not None
    
    @pytest.mark.asyncio
    async def test_parse_implicit_ai_refinement(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试解析隐式的AI优化请求"""
        mock_response = AIMessage(content="""{
            "intents": [
                {
                    "intent_type": "refine_ai_content",
                    "target_variable": "analysis",
                    "refinement_instruction": "增加长度",
                    "confidence": 0.75
                }
            ],
            "confidence": 0.75,
            "clarification_needed": false
        }""")
        
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.return_value = mock_response
            
            intents = await intent_parser.parse(
                user_request="写长一点",
                memory=sample_memory
            )
            
            assert len(intents) == 1
            assert intents[0].intent_type == IntentType.REFINE_AI_CONTENT


class TestParseTemplateModification:
    """测试模板修改意图解析"""
    
    @pytest.mark.asyncio
    async def test_parse_add_section(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试解析添加章节请求"""
        mock_response = AIMessage(content="""{
            "intents": [
                {
                    "intent_type": "add_section",
                    "target_section": "竞争对手分析",
                    "section_description": "分析主要竞争对手的市场表现",
                    "confidence": 0.92
                }
            ],
            "confidence": 0.92,
            "clarification_needed": false
        }""")
        
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.return_value = mock_response
            
            intents = await intent_parser.parse(
                user_request="添加竞争对手分析章节",
                memory=sample_memory
            )
            
            assert len(intents) == 1
            assert intents[0].intent_type == IntentType.ADD_SECTION
            assert intents[0].target_section == "竞争对手分析"
            assert intents[0].section_description is not None
    
    @pytest.mark.asyncio
    async def test_parse_modify_section(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试解析修改章节请求"""
        mock_response = AIMessage(content="""{
            "intents": [
                {
                    "intent_type": "modify_section",
                    "target_section": "市场分析",
                    "section_description": "调整格式,增加图表",
                    "confidence": 0.85
                }
            ],
            "confidence": 0.85,
            "clarification_needed": false
        }""")
        
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.return_value = mock_response
            
            intents = await intent_parser.parse(
                user_request="修改市场分析部分,增加一些图表",
                memory=sample_memory
            )
            
            assert len(intents) == 1
            assert intents[0].intent_type == IntentType.MODIFY_SECTION
    
    @pytest.mark.asyncio
    async def test_parse_remove_section(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试解析删除章节请求"""
        mock_response = AIMessage(content="""{
            "intents": [
                {
                    "intent_type": "remove_section",
                    "target_section": "附录",
                    "confidence": 0.95
                }
            ],
            "confidence": 0.95,
            "clarification_needed": false
        }""")
        
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.return_value = mock_response
            
            intents = await intent_parser.parse(
                user_request="删除附录部分",
                memory=sample_memory
            )
            
            assert len(intents) == 1
            assert intents[0].intent_type == IntentType.REMOVE_SECTION


class TestReferenceResolution:
    """测试引用解析"""
    
    @pytest.mark.asyncio
    async def test_parse_pronoun_reference(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试代词引用解析"""
        mock_response = AIMessage(content="""{
            "intents": [
                {
                    "intent_type": "refine_ai_content",
                    "target_variable": "analysis",
                    "refinement_instruction": "使其更详细",
                    "confidence": 0.8
                }
            ],
            "confidence": 0.8,
            "clarification_needed": false
        }""")
        
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.return_value = mock_response
            
            intents = await intent_parser.parse(
                user_request="把它改详细一点",
                memory=sample_memory
            )
            
            assert len(intents) == 1
            # LLM应该从上下文推断"它"指的是什么


class TestClarificationHandling:
    """测试澄清请求处理"""
    
    @pytest.mark.asyncio
    async def test_parse_ambiguous_request_needs_clarification(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试模糊请求需要澄清"""
        mock_response = AIMessage(content="""{
            "intents": [],
            "confidence": 0.3,
            "clarification_needed": true,
            "clarification_question": "请问您想要修改哪个变量的值?"
        }""")
        
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.return_value = mock_response
            
            with pytest.raises(ValueError) as exc_info:
                await intent_parser.parse(
                    user_request="改一下",
                    memory=sample_memory
                )
            
            assert "不够明确" in str(exc_info.value)
            assert "需要更多信息" in str(exc_info.value)


class TestConfidenceFiltering:
    """测试置信度过滤"""
    
    @pytest.mark.asyncio
    async def test_filter_low_confidence_intents(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试过滤低置信度意图"""
        mock_response = AIMessage(content="""{
            "intents": [
                {
                    "intent_type": "update_parameter",
                    "target_variable": "wgid",
                    "new_value": "ZQGY0175",
                    "confidence": 0.9
                },
                {
                    "intent_type": "add_section",
                    "target_section": "未知",
                    "confidence": 0.3
                }
            ],
            "confidence": 0.6,
            "clarification_needed": false
        }""")
        
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.return_value = mock_response
            
            intents = await intent_parser.parse(
                user_request="把wgid改成ZQGY0175,可能还要添加点什么",
                memory=sample_memory
            )
            
            # 应该只返回高置信度的意图
            assert len(intents) == 1
            assert intents[0].confidence >= 0.5


class TestContextBuilding:
    """测试上下文构建"""
    
    def test_build_context_with_empty_history(
        self, 
        intent_parser, 
        sample_memory
    ):
        """测试构建空历史的上下文"""
        context = intent_parser._build_context(sample_memory)
        
        assert isinstance(context, str)
        # 空历史应该返回默认消息
        assert len(context) > 0
    
    def test_build_context_with_history(
        self, 
        intent_parser, 
        sample_memory
    ):
        """测试构建有历史的上下文"""
        # 添加对话历史
        from app.schemas.modification_schemas import ConversationTurn
        
        sample_memory.conversation_history.append(
            ConversationTurn(
                turn_number=1,
                user_request="把wgid改成ZQGY0175",
                parsed_intents=[],
                operations=[],
                system_response="已更新",
                report_version=2,
                timestamp=datetime.now() 
            )
        )
        
        context = intent_parser._build_context(sample_memory)
        print(context)
        assert isinstance(context, str)
        assert "wgid" in context or "ZQGY0175" in context


class TestErrorHandling:
    """测试错误处理"""
    
    @pytest.mark.asyncio
    async def test_parse_with_llm_error(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试LLM调用失败"""
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.side_effect = Exception("LLM调用失败")
            
            with pytest.raises(Exception):
                await intent_parser.parse(
                    user_request="测试请求",
                    memory=sample_memory
                )
    
    @pytest.mark.asyncio
    async def test_parse_with_invalid_json_response(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试LLM返回无效JSON"""
        mock_response = AIMessage(content="这不是JSON格式")
        
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.return_value = mock_response
            
            with pytest.raises(Exception):
                await intent_parser.parse(
                    user_request="测试请求",
                    memory=sample_memory
                )
    
    @pytest.mark.asyncio
    async def test_parse_empty_request(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试空请求"""
        mock_response = AIMessage(content="""{
            "intents": [],
            "confidence": 0.0,
            "clarification_needed": true,
            "clarification_question": "请说明您想要做什么修改"
        }""")
        
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.return_value = mock_response
            
            with pytest.raises(ValueError):
                await intent_parser.parse(
                    user_request="",
                    memory=sample_memory
                )


class TestMultiIntentParsing:
    """测试多意图解析"""
    
    @pytest.mark.asyncio
    async def test_parse_compound_request(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试复合请求解析"""
        mock_response = AIMessage(content="""{
            "intents": [
                {
                    "intent_type": "update_parameter",
                    "target_variable": "wgid",
                    "new_value": "ZQGY0175",
                    "confidence": 0.9
                },
                {
                    "intent_type": "refine_ai_content",
                    "target_variable": "analysis",
                    "refinement_instruction": "更详细",
                    "confidence": 0.85
                },
                {
                    "intent_type": "add_section",
                    "target_section": "风险评估",
                    "section_description": "评估项目风险",
                    "confidence": 0.9
                }
            ],
            "confidence": 0.88,
            "clarification_needed": false
        }""")
        
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.return_value = mock_response
            
            intents = await intent_parser.parse(
                user_request="把wgid改成ZQGY0175,让分析更详细,还要添加风险评估章节",
                memory=sample_memory
            )
            
            assert len(intents) == 3
            assert intents[0].intent_type == IntentType.UPDATE_PARAMETER
            assert intents[1].intent_type == IntentType.REFINE_AI_CONTENT
            assert intents[2].intent_type == IntentType.ADD_SECTION


class TestEdgeCases:
    """测试边界情况"""
    
    @pytest.mark.asyncio
    async def test_parse_very_long_request(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试超长请求"""
        long_request = "请" + "修改" * 1000 + "报告"
        
        mock_response = AIMessage(content="""{
            "intents": [],
            "confidence": 0.0,
            "clarification_needed": true,
            "clarification_question": "请求过长,请简化"
        }""")
        
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.return_value = mock_response
            
            with pytest.raises(ValueError):
                await intent_parser.parse(
                    user_request=long_request,
                    memory=sample_memory
                )
    
    @pytest.mark.asyncio
    async def test_parse_special_characters(
        self, 
        intent_parser, 
        sample_memory,
        mock_llm
    ):
        """测试特殊字符请求"""
        mock_response = AIMessage(content="""{
            "intents": [
                {
                    "intent_type": "update_parameter",
                    "target_variable": "wgid",
                    "new_value": "ZQGY@#$%0175",
                    "confidence": 0.8
                }
            ],
            "confidence": 0.8,
            "clarification_needed": false
        }""")
        
        with patch.object(intent_parser, 'llm', mock_llm):
            mock_llm.ainvoke.return_value = mock_response
            
            intents = await intent_parser.parse(
                user_request="把wgid改成ZQGY@#$%0175",
                memory=sample_memory
            )
            
            assert len(intents) == 1
            assert intents[0].new_value == "ZQGY@#$%0175"

