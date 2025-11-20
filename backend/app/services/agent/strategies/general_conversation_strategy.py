"""
通用对话策略

处理通用对话类操作，如问候、感谢、咨询等。
"""
from typing import Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from app.services.agent.strategies.base import ExecutionStrategy
from app.schemas.modification_schemas import (
    OperationStep,
    Operation,
    OperationType,
    ConversationMemory,
    GeneralConversationDetails
)

logger = logging.getLogger(__name__)


class GeneralConversationStrategy(ExecutionStrategy):
    """
    通用对话操作执行策略
    
    处理各种通用对话，如：
    - greeting: 问候
    - thanks: 感谢
    - question: 咨询问题
    - feedback: 反馈意见
    - suggestion_request: 请求建议
    """
    
    def __init__(self, db: Session):
        """
        初始化通用对话策略
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    async def execute(
        self,
        step: OperationStep,
        memory: ConversationMemory
    ) -> Operation:
        """
        执行通用对话操作
        
        Args:
            step: 操作步骤
            memory: 对话记忆
        
        Returns:
            Operation: 操作结果
        """
        start_time = datetime.now()
        
        try:
            conversation_context = step.parameters.get("conversation_context", "一般对话")
            query_details = step.parameters.get("query_details", {})
            
            logger.info(f"处理通用对话: {conversation_context}")
            
            # 生成响应
            response = self._generate_response(
                conversation_context,
                memory,
                query_details
            )
            
            # 计算执行时长
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 创建对话详情
            details = GeneralConversationDetails(
                user_message=conversation_context,
                system_response=response,
                conversation_type=self._classify_conversation_type(conversation_context)
            )
            
            return self._create_operation_result(
                operation_type=OperationType.GENERAL_CONVERSATION,
                details=details,
                success=True,
                duration_ms=duration_ms
            )
        
        except Exception as e:
            logger.error(f"通用对话处理失败: {str(e)}", exc_info=True)
            
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 返回失败结果
            details = GeneralConversationDetails(
                user_message=step.parameters.get("conversation_context", "未知"),
                system_response="抱歉，我暂时无法回复您的消息。",
                conversation_type="error"
            )
            
            return self._create_operation_result(
                operation_type=OperationType.GENERAL_CONVERSATION,
                details=details,
                success=False,
                error_message=f"对话处理失败: {str(e)}",
                duration_ms=duration_ms
            )
    
    def _generate_response(
        self,
        conversation_context: str,
        memory: ConversationMemory,
        query_details: Dict[str, Any]
    ) -> str:
        """
        生成对话响应
        
        Args:
            conversation_context: 对话上下文
            memory: 对话记忆
            query_details: 查询详情
        
        Returns:
            str: 系统响应
        """
        conversation_type = self._classify_conversation_type(conversation_context)
        
        if conversation_type == "greeting":
            return self._handle_greeting(memory)
        
        elif conversation_type == "thanks":
            return self._handle_thanks()
        
        elif conversation_type == "question":
            return self._handle_question(conversation_context, memory)
        
        elif conversation_type == "feedback":
            return self._handle_feedback(conversation_context)
        
        elif conversation_type == "suggestion_request":
            return self._handle_suggestion_request(memory)
        
        else:
            return self._handle_general(conversation_context, memory)
    
    def _classify_conversation_type(self, context: str) -> str:
        """
        分类对话类型
        
        Args:
            context: 对话上下文
        
        Returns:
            str: 对话类型
        """
        context_lower = context.lower()
        
        # 问候
        greeting_keywords = ["你好", "您好", "hi", "hello", "早上好", "下午好", "晚上好"]
        if any(keyword in context_lower for keyword in greeting_keywords):
            return "greeting"
        
        # 感谢
        thanks_keywords = ["谢谢", "感谢", "多谢", "thanks", "thank you"]
        if any(keyword in context_lower for keyword in thanks_keywords):
            return "thanks"
        
        # 请求建议
        suggestion_keywords = ["建议", "推荐", "怎么样", "如何", "suggestion", "recommend"]
        if any(keyword in context_lower for keyword in suggestion_keywords):
            return "suggestion_request"
        
        # 反馈
        feedback_keywords = ["很好", "不错", "有问题", "bug", "错误"]
        if any(keyword in context_lower for keyword in feedback_keywords):
            return "feedback"
        
        # 咨询问题（默认）
        return "question"
    
    def _handle_greeting(self, memory: ConversationMemory) -> str:
        """处理问候"""
        return (
            f"您好！我是报告修改助手。\n\n"
            f"当前您正在编辑报告 `{memory.report_id}`（版本 v{memory.current_version}）。\n\n"
            f"我可以帮您：\n"
            f"- 修改报告参数和内容\n"
            f"- 优化AI生成的文本\n"
            f"- 添加、修改或删除章节\n"
            f"- 查询报告信息和统计数据\n\n"
            f"请告诉我您需要什么帮助！"
        )
    
    def _handle_thanks(self) -> str:
        """处理感谢"""
        return "不客气！很高兴能帮到您。如果还有其他需要，随时告诉我！"
    
    def _handle_question(self, context: str, memory: ConversationMemory) -> str:
        """处理咨询问题"""
        return (
            f"关于您的问题：{context}\n\n"
            f"我可以帮您：\n"
            f"1. 修改报告参数（如时间范围、对象ID等）\n"
            f"2. 优化AI生成的内容（让分析更详细、增加数据支撑等）\n"
            f"3. 调整报告结构（添加、修改或删除章节）\n"
            f"4. 查询报告信息（内容、参数、章节、统计等）\n\n"
            f"请具体告诉我您想做什么，我会尽力帮助您！"
        )
    
    def _handle_feedback(self, context: str) -> str:
        """处理反馈"""
        return (
            f"感谢您的反馈：{context}\n\n"
            f"您的意见对我们很重要。如果遇到问题或有改进建议，"
            f"请随时告诉我，我会尽力为您解决！"
        )
    
    def _handle_suggestion_request(self, memory: ConversationMemory) -> str:
        """处理建议请求"""
        report_state = memory.report_state
        
        suggestions = []
        
        # 根据报告状态提供建议
        if report_state.edit_mode == "template":
            suggestions.append("- 您可以尝试调整参数，查看不同数据下的报告效果")
            suggestions.append("- 如果某些AI生成的内容不够详细，可以要求我优化")
        
        if len(report_state.variables) > 0:
            suggestions.append("- 使用「显示所有参数」查看当前可修改的参数")
            suggestions.append("- 使用「列出所有变量」了解报告的数据来源")
        
        suggestions.append("- 使用「显示章节结构」查看报告的组织方式")
        suggestions.append("- 使用「获取统计信息」了解报告的详细数据")
        
        result = "**报告优化建议**:\n\n"
        result += "\n".join(suggestions)
        result += "\n\n请告诉我您想尝试哪个建议，或者有其他需求！"
        
        return result
    
    def _handle_general(self, context: str, memory: ConversationMemory) -> str:
        """处理一般对话"""
        return (
            f"我理解您的意思。作为报告修改助手，我主要负责：\n\n"
            f"- **修改操作**: 更新参数、优化内容、调整结构\n"
            f"- **查询操作**: 显示内容、列出参数、查看统计\n"
            f"- **对话交流**: 回答问题、提供建议\n\n"
            f"如果您需要具体的帮助，请告诉我！"
        )
