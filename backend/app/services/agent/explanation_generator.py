"""
响应说明生成器

本模块负责生成用户友好的响应说明,解释系统执行的操作和结果。

功能:
- 根据操作结果生成自然语言响应
- 支持中文输出
- 可选择使用LLM生成或模板生成
"""
from typing import List, Optional
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import logging
import os

from app.schemas.modification_schemas import (
    Operation,
    ConversationMemory,
    ParameterUpdateDetails,
    AIRefinementDetails,
    TemplateModificationDetails
)

logger = logging.getLogger(__name__)


class ExplanationGenerator:
    """
    响应说明生成器类
    
    生成用户友好的自然语言响应,解释系统执行的修改操作。
    
    支持两种模式:
    1. 模板模式: 基于规则的快速生成（默认）
    2. LLM模式: 使用大语言模型生成更自然的响应
    
    Attributes:
        use_llm: 是否使用LLM生成
        llm: LangChain LLM实例（如果使用LLM）
    """
    
    def __init__(
        self,
        use_llm: bool = False,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7
    ):
        """
        初始化响应说明生成器
        
        Args:
            use_llm: 是否使用LLM生成（默认False,使用模板）
            api_key: OpenAI API密钥（如果使用LLM）
            api_base: OpenAI API基础URL（可选）
            model: 模型名称（默认gpt-3.5-turbo,成本较低）
            temperature: 生成温度（默认0.7,保持一定创造性）
        """
        self.use_llm = use_llm
        self.llm = None
        
        if use_llm:
            # 初始化LLM
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("LLM模式需要API密钥,回退到模板模式")
                self.use_llm = False
            else:
                llm_kwargs = {
                    "model": model,
                    "temperature": temperature,
                    "api_key": api_key
                }
                if api_base:
                    llm_kwargs["base_url"] = api_base
                
                self.llm = ChatOpenAI(**llm_kwargs)
    
    async def generate(
        self,
        user_request: str,
        operations: List[Operation],
        memory: ConversationMemory
    ) -> str:
        """
        生成响应说明
        
        Args:
            user_request: 用户的原始请求
            operations: 执行的操作列表
            memory: 对话记忆
        
        Returns:
            str: 用户友好的响应说明
        """
        if self.use_llm and self.llm:
            return await self._generate_with_llm(user_request, operations, memory)
        else:
            return self._generate_with_template(user_request, operations, memory)
    
    async def _generate_with_llm(
        self,
        user_request: str,
        operations: List[Operation],
        memory: ConversationMemory
    ) -> str:
        """
        使用LLM生成响应
        
        Args:
            user_request: 用户请求
            operations: 操作列表
            memory: 对话记忆
        
        Returns:
            str: 生成的响应
        """
        try:
            # 构建操作摘要
            operations_summary = self._build_operations_summary(operations)
            
            # 构建提示词
            prompt_template = ChatPromptTemplate.from_messages([
                ("system", """你是一个友好的报告修改助手。用户刚才提出了一个修改请求,系统已经执行完毕。
请用简洁、友好的中文向用户说明完成了哪些修改。

要求:
1. 使用第一人称("我已经...")
2. 简洁明了,突出重点
3. 如果有多个操作,分点说明
4. 如果有失败的操作,委婉地说明
5. 整体语气要积极、专业"""),
                ("user", """用户请求: {user_request}

执行的操作:
{operations_summary}

当前版本: {current_version}

请生成响应说明:""")
            ])
            
            # 调用LLM
            prompt = prompt_template.format_messages(
                user_request=user_request,
                operations_summary=operations_summary,
                current_version=memory.current_version
            )
            
            response = await self.llm.ainvoke(prompt)
            explanation = response.content.strip()
            
            logger.info(f"使用LLM生成响应: {explanation[:50]}...")
            return explanation
        
        except Exception as e:
            logger.error(f"LLM生成响应失败,回退到模板模式: {str(e)}")
            return self._generate_with_template(user_request, operations, memory)
    
    def _generate_with_template(
        self,
        user_request: str,
        operations: List[Operation],
        memory: ConversationMemory
    ) -> str:
        """
        使用模板生成响应
        
        基于规则的快速生成方法。
        
        Args:
            user_request: 用户请求
            operations: 操作列表
            memory: 对话记忆
        
        Returns:
            str: 生成的响应
        """
        parts = []
        
        # 统计成功和失败的操作
        success_ops = [op for op in operations if op.success]
        failed_ops = [op for op in operations if not op.success]
        
        # 开场白
        if success_ops:
            parts.append("我已经完成了以下修改:")
        else:
            parts.append("很抱歉,修改执行遇到了问题:")
        
        # 描述成功的操作
        for idx, op in enumerate(success_ops, 1):
            op_desc = self._describe_operation(op, memory)
            parts.append(f"{idx}. {op_desc}")
        
        # 描述失败的操作（如果有）
        if failed_ops:
            parts.append("\n以下操作执行失败:")
            for idx, op in enumerate(failed_ops, 1):
                error_msg = op.error_message or "未知错误"
                parts.append(f"{idx}. {op.operation_type}: {error_msg}")
        
        # 总结
        if success_ops and not failed_ops:
            parts.append(f"\n报告已更新到版本 {memory.current_version}。")
        elif success_ops and failed_ops:
            parts.append(
                f"\n报告已部分更新到版本 {memory.current_version},"
                f"但有{len(failed_ops)}个操作失败。"
            )
        
        explanation = "\n".join(parts)
        logger.info(f"使用模板生成响应: {explanation[:50]}...")
        
        return explanation
    
    def _describe_operation(
        self,
        operation: Operation,
        memory: ConversationMemory
    ) -> str:
        """
        描述单个操作
        
        Args:
            operation: 操作对象
            memory: 对话记忆
        
        Returns:
            str: 操作描述
        """
        details = operation.details
        
        if isinstance(details, ParameterUpdateDetails):
            # 参数更新操作
            if details.dependent_variables:
                dep_count = len(details.dependent_variables)
                return (
                    f"已将参数 `{details.variable_name}` 的值更新为 `{details.new_value}`, "
                    f"并重新执行了 {dep_count} 个依赖变量"
                )
            else:
                return f"已将参数 `{details.variable_name}` 的值更新为 `{details.new_value}`"
        
        elif isinstance(details, AIRefinementDetails):
            # AI内容优化操作
            if details.new_content_length and details.old_content_length:
                length_change = details.new_content_length - details.old_content_length
                if length_change > 0:
                    return (
                        f"已优化AI内容 `{details.variable_name}`, "
                        f"内容更加详细(增加了 {length_change} 字符)"
                    )
                else:
                    return f"已优化AI内容 `{details.variable_name}`, 内容更加精炼"
            else:
                return f"已根据您的要求优化了 `{details.variable_name}` 的内容"
        
        elif isinstance(details, TemplateModificationDetails):
            # 模板修改操作
            if details.modification_type == "add":
                return f"已添加新章节: {details.section_name}"
            elif details.modification_type == "modify":
                return f"已修改章节: {details.section_name}"
            elif details.modification_type == "remove":
                return f"已删除章节: {details.section_name}"
        
        # 默认描述
        return f"已完成 {operation.operation_type} 操作"
    
    def _build_operations_summary(self, operations: List[Operation]) -> str:
        """
        构建操作摘要
        
        Args:
            operations: 操作列表
        
        Returns:
            str: 格式化的操作摘要
        """
        lines = []
        for idx, op in enumerate(operations, 1):
            status = "✓ 成功" if op.success else "✗ 失败"
            line = f"{idx}. {op.operation_type} - {status}"
            if not op.success and op.error_message:
                line += f" ({op.error_message})"
            lines.append(line)
        
        return "\n".join(lines)

