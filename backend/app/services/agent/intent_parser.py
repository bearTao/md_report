"""
意图解析器

本模块使用LLM(大语言模型)将用户的自然语言修改请求解析为结构化的意图列表。

主要功能:
- 解析用户请求中的修改意图
- 支持多意图识别
- 提供上下文感知的解析
- 生成结构化的ModificationIntent对象
"""
from typing import List, Dict, Any, Optional
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
import logging
import os

from app.core.agent_config import get_llm_kwargs, get_config
from app.schemas.modification_schemas import (
    ModificationIntent,
    IntentType,
    ConversationMemory
)

logger = logging.getLogger(__name__)


class IntentParserOutput(BaseModel):
    """
    意图解析器输出模型
    
    用于LLM的结构化输出。
    
    Attributes:
        intents: 解析出的意图列表
        confidence: 整体解析置信度
        clarification_needed: 是否需要用户澄清
        clarification_question: 澄清问题（如果需要）
    """
    intents: List[ModificationIntent] = Field(default_factory=list, description="解析出的意图列表")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="整体置信度")
    clarification_needed: bool = Field(False, description="是否需要澄清")
    clarification_question: Optional[str] = Field(None, description="澄清问题")


class IntentParser:
    """
    意图解析器类
    
    使用LLM将用户的自然语言请求解析为结构化的修改意图。
    
    Attributes:
        llm: LangChain LLM实例
        output_parser: Pydantic输出解析器
        prompt_template: 提示词模板
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ):
        """
        初始化意图解析器
        
        Args:
            api_key: OpenAI API密钥（如果不提供则从配置文件或环境变量读取）
            api_base: OpenAI API基础URL（如果不提供则从配置文件或环境变量读取）
            model: 模型名称（如果不提供则从配置文件读取，默认gpt-4）
            temperature: 生成温度（如果不提供则从配置文件读取，默认0.1）
        """
        # 从配置获取LLM参数
        llm_kwargs = get_llm_kwargs("intent_parser")
        
        # 允许通过参数覆盖配置
        if api_key:
            llm_kwargs["api_key"] = api_key
        if api_base:
            llm_kwargs["base_url"] = api_base
        if model:
            llm_kwargs["model"] = model
        if temperature is not None:
            llm_kwargs["temperature"] = temperature
        
        # 验证API密钥
        if not llm_kwargs.get("api_key"):
            raise ValueError(
                "OpenAI API密钥未配置,请通过以下方式之一设置:\n"
                "1. 环境变量 OPENAI_API_KEY\n"
                "2. 配置文件 config/agent_config.yaml\n"
                "3. 初始化参数 api_key"
            )
        
        # 初始化LLM
        self.llm = ChatOpenAI(**llm_kwargs)
        
        # 初始化输出解析器
        self.output_parser = PydanticOutputParser(pydantic_object=IntentParserOutput)
        
        # 构建提示词模板
        self.prompt_template = self._build_prompt_template()
        
        logger.info(
            f"IntentParser初始化完成 - "
            f"model: {llm_kwargs['model']}, "
            f"temperature: {llm_kwargs['temperature']}"
        )
    
    def _build_prompt_template(self) -> ChatPromptTemplate:
        """
        构建提示词模板
        
        Returns:
            ChatPromptTemplate: 提示词模板
        """
        system_prompt = """你是一个专业的报告修改意图解析助手。你的任务是理解用户的自然语言请求,并将其解析为结构化的意图列表。

**支持的意图类型:**

**【修改类意图】**

1. **update_parameter** - 更新参数值
   - 用户想要修改某个输入参数的值
   - 例如: "将时间范围改为最近一周", "把wgid改为ZQGY0175"
   - 需要识别: target_variable(参数名), new_value(新值)

2. **refine_ai_content** - 优化AI生成的内容
   - 用户想要改进某个AI生成的内容
   - 例如: "让分析更详细", "增加具体的数据支撑"
   - 需要识别: target_variable(AI变量名), refinement_instruction(优化指令)

3. **add_section** - 添加新章节
   - 用户想要在报告中添加新的内容章节
   - 例如: "添加竞争对手分析", "增加风险评估部分"
   - 需要识别: section_description(章节描述)

4. **modify_section** - 修改现有章节
   - 用户想要修改某个现有章节的内容或结构
   - 例如: "修改第一章的标题", "调整结论部分的格式"
   - 需要识别: target_section(章节名), section_description(修改说明)

5. **remove_section** - 删除章节
   - 用户想要删除某个章节
   - 例如: "删除附录部分", "去掉免责声明"
   - 需要识别: target_section(章节名)

**【查询和通用类意图】**

6. **query** - 查询报告信息
   - 用户想要查看或获取报告的某些信息
   - 例如: "输出当前报告内容", "显示所有参数", "列出所有章节", "当前报告有多少字"
   - 需要识别: query_type(查询类型), query_details(查询详情)
   - 常见查询类型:
     * show_content: 显示报告内容
     * list_variables: 列出所有变量
     * show_parameters: 显示参数列表
     * show_sections: 显示章节结构
     * get_statistics: 获取统计信息（字数、章节数等）
     * show_history: 显示修改历史

7. **general_conversation** - 通用对话
   - 用户进行一般性的交流，不涉及具体的修改或查询操作
   - 例如: "你好", "谢谢", "这个报告怎么样", "有什么建议吗"
   - 需要识别: conversation_context(对话上下文)
   - 常见对话类型:
     * greeting: 问候
     * thanks: 感谢
     * question: 咨询问题
     * feedback: 反馈意见
     * suggestion_request: 请求建议

**解析规则:**

1. 从用户请求中识别所有修改意图（可能有多个）
2. 为每个意图提取必要的参数
3. 如果参数名不明确,尝试从上下文中推断
4. 如果无法确定关键信息,设置clarification_needed=True并提出问题
5. 对于模糊的请求,选择最可能的意图类型
6. 支持中文理解和同义词识别

**引用解析（Reference Resolution）:**

- 代词引用: "它"、"这个"、"那个" → 从上下文推断指向最近操作的变量/章节
- 隐式引用: "更详细一些"、"改长一点" → 推断为最近一次AI生成的内容
- 相对引用: "上一个"、"刚才的" → 从对话历史中识别

**相对值处理（Relative Values）:**

- 时间增量: "延长一周"、"再增加3天" → 计算相对于当前值的新值
- 数值增量: "增加10个"、"减少20%" → 根据当前值计算新值
- 位置相对: "往前移"、"放到后面" → 计算相对位置

**多意图识别:**

- 识别用 "并且"、"同时"、"还要" 连接的多个意图
- 例如: "将时间改为一周,并且让分析更详细" → 两个意图

**上下文信息:**

{context_info}

**当前报告状态:**

- 报告ID: {report_id}
- 当前版本: {current_version}
- 已知变量: {known_variables}

**用户请求:**

{user_request}

**输出格式说明:**

{format_instructions}

请分析上述用户请求,解析出所有修改意图,并以JSON格式返回。"""

        return ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", "{user_request}")
        ])
    
    async def parse(
        self,
        user_request: str,
        memory: ConversationMemory
    ) -> List[ModificationIntent]:
        """
        解析用户请求
        
        将自然语言请求解析为结构化的意图列表。
        
        Args:
            user_request: 用户的修改请求
            memory: 对话记忆（提供上下文）
        
        Returns:
            List[ModificationIntent]: 解析出的意图列表
        
        Raises:
            ValueError: 如果解析失败或请求不明确
        """
        try:
            # 构建上下文信息
            context_info = self._build_context(memory)
            
            # 获取已知变量列表
            known_variables = list(memory.report_state.variables.keys())
            
            # 准备提示词参数
            prompt_values = {
                "user_request": user_request,
                "context_info": context_info,
                "report_id": memory.report_id,
                "current_version": memory.current_version,
                "known_variables": ", ".join(known_variables) if known_variables else "无",
                "format_instructions": self.output_parser.get_format_instructions()
            }
            
            # 调用LLM
            logger.info(f"开始解析用户请求: {user_request[:100]}...")
            
            prompt = self.prompt_template.format_messages(**prompt_values)
            response = await self.llm.ainvoke(prompt)
            
            # 解析输出
            result: IntentParserOutput = self.output_parser.parse(response.content)
            
            logger.info(
                f"解析完成,识别出 {len(result.intents)} 个意图, "
                f"置信度: {result.confidence:.2f}"
            )
            
            # 检查是否需要澄清
            if result.clarification_needed:
                raise ValueError(
                    f"请求不够明确,需要更多信息: {result.clarification_question}"
                )
            
            # 验证和过滤低置信度意图
            valid_intents = [
                intent for intent in result.intents
                if intent.confidence >= 0.5
            ]
            
            if not valid_intents:
                raise ValueError("无法理解您的修改请求,请提供更具体的说明")
            
            return valid_intents
        
        except Exception as e:
            logger.error(f"意图解析失败: {str(e)}")
            raise
    
    def _build_context(self, memory: ConversationMemory) -> str:
        """
        构建上下文信息
        
        从对话记忆中提取有用的上下文信息,包括:
        - 对话历史摘要
        - 最近的对话轮次
        - 最近修改的变量/章节信息（用于引用解析）
        
        Args:
            memory: 对话记忆
        
        Returns:
            str: 格式化的上下文信息
        """
        context_parts = []
        
        # 添加上下文总结（如果有）
        if memory.context_summary:
            context_parts.append(f"对话摘要: {memory.context_summary}")
        
        # 添加最近的对话历史（最近3轮）
        recent_turns = memory.conversation_history[-3:] if memory.conversation_history else []
        if recent_turns:
            context_parts.append("\n最近的对话:")
            for turn in recent_turns:
                context_parts.append(f"- 用户: {turn.user_request}")
                context_parts.append(f"  系统: {turn.system_response[:100]}...")
                
                # 添加最近操作的变量信息（用于引用解析）
                if turn.operations:
                    for op in turn.operations[-1:]:  # 最后一个操作
                        if hasattr(op.details, 'variable_name'):
                            context_parts.append(
                                f"  → 最近操作的变量: {op.details.variable_name}"
                            )
                        if hasattr(op.details, 'section_name'):
                            context_parts.append(
                                f"  → 最近操作的章节: {op.details.section_name}"
                            )
        
        if not context_parts:
            return "（首次对话,无历史上下文）"
        
        # 添加当前值信息（用于相对值计算）
        context_parts.append("\n当前值参考（用于相对值计算）:")
        context_parts.append("请从变量列表和对话历史中获取当前值")
        
        return "\n".join(context_parts)
    
    def parse_sync(
        self,
        user_request: str,
        memory: ConversationMemory
    ) -> List[ModificationIntent]:
        """
        同步版本的解析方法
        
        用于不支持异步的环境。
        
        Args:
            user_request: 用户的修改请求
            memory: 对话记忆
        
        Returns:
            List[ModificationIntent]: 解析出的意图列表
        """
        try:
            # 构建上下文信息
            context_info = self._build_context(memory)
            
            # 获取已知变量列表
            known_variables = list(memory.report_state.variables.keys())
            
            # 准备提示词参数
            prompt_values = {
                "user_request": user_request,
                "context_info": context_info,
                "report_id": memory.report_id,
                "current_version": memory.current_version,
                "known_variables": ", ".join(known_variables) if known_variables else "无",
                "format_instructions": self.output_parser.get_format_instructions()
            }
            
            # 调用LLM（同步）
            logger.info(f"开始解析用户请求（同步）: {user_request[:100]}...")
            
            prompt = self.prompt_template.format_messages(**prompt_values)
            response = self.llm.invoke(prompt)
            
            # 解析输出
            result: IntentParserOutput = self.output_parser.parse(response.content)
            
            logger.info(
                f"解析完成,识别出 {len(result.intents)} 个意图, "
                f"置信度: {result.confidence:.2f}"
            )
            
            # 检查是否需要澄清
            if result.clarification_needed:
                raise ValueError(
                    f"请求不够明确,需要更多信息: {result.clarification_question}"
                )
            
            # 验证和过滤低置信度意图
            valid_intents = [
                intent for intent in result.intents
                if intent.confidence >= 0.5
            ]
            
            if not valid_intents:
                raise ValueError("无法理解您的修改请求,请提供更具体的说明")
            
            return valid_intents
        
        except Exception as e:
            logger.error(f"意图解析失败: {str(e)}")
            raise

