"""
报告修改代理

本模块实现了报告修改代理的核心orchestration逻辑,协调各个子组件完成报告修改任务。

主要职责:
- 接收用户的修改请求
- 协调IntentParser解析用户意图
- 协调OperationPlanner规划执行步骤
- 协调OperationExecutor执行操作
- 管理会话状态和对话历史
- 生成用户友好的响应说明
"""
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from app.services.agent.memory_manager import MemoryManager
from app.services.agent.intent_parser import IntentParser
from app.services.agent.operation_planner import OperationPlanner
from app.services.agent.operation_executor import OperationExecutor
from app.services.agent.explanation_generator import ExplanationGenerator
from app.services.agent.utils import (
    llm_tracker,
    retry_on_failure,
    measure_time
)
from app.services.renderer import TemplateRenderer
from app.services.websocket_manager import ConnectionManager
from app.schemas.modification_schemas import (
    ModificationResult,
    ModificationMetadata,
    ConversationMemory,
    ModificationIntent,
    Operation,
    OperationStep
)
from app.models.db_models import AIProviderKey
import os

logger = logging.getLogger(__name__)


class ReportModificationAgent:
    """
    报告修改代理类
    
    核心orchestrator,协调意图解析、操作规划、操作执行等子组件完成报告修改任务。
    
    Attributes:
        db: 数据库会话
        memory_manager: 记忆管理器
        template_renderer: 模板渲染器
        websocket_manager: WebSocket连接管理器（用于进度推送）
    """
    
    def __init__(
        self,
        db: Session,
        websocket_manager: Optional[ConnectionManager] = None
    ):
        """
        初始化报告修改代理
        
        Args:
            db: 数据库会话
            websocket_manager: WebSocket管理器（可选）
        """
        self.db = db
        self.memory_manager = MemoryManager(db)
        self.template_renderer = TemplateRenderer()
        self.websocket_manager = websocket_manager
        
        # 获取AI配置
        api_key, api_base = self._get_ai_config()
        
        # 初始化子组件(Phase 2)
        try:
            self.intent_parser = IntentParser(
                api_key=api_key,
                api_base=api_base,
                model="gpt-4",
                temperature=0.1
            )
            logger.info("IntentParser初始化成功")
        except Exception as e:
            logger.warning(f"IntentParser初始化失败: {str(e)}")
            self.intent_parser = None
        
        self.operation_planner = OperationPlanner()
        self.operation_executor = OperationExecutor(db)
        self.explanation_generator = ExplanationGenerator(
            use_llm=False  # 默认使用模板模式,成本更低
        )
    
    def _get_ai_config(self) -> tuple[Optional[str], Optional[str]]:
        """
        获取OpenAI API配置
        
        Returns:
            tuple: (api_key, api_base)
        """
        # 先尝试环境变量
        api_key = os.getenv("OPENAI_API_KEY")
        api_base = os.getenv("OPENAI_API_BASE")
        if api_key:
            return api_key, api_base
        
        # 尝试从数据库获取
        try:
            config = self.db.query(AIProviderKey).filter(
                AIProviderKey.provider == "openai"
            ).first()
            
            if config:
                return config.api_key_ciphertext, config.api_base
        except Exception as e:
            logger.warning(f"从数据库获取AI配置失败: {str(e)}")
        
        return None, None
    
    async def modify_report(
        self,
        report_id: str,
        user_request: str,
        session_id: Optional[str] = None
    ) -> ModificationResult:
        """
        修改报告的主入口方法
        
        执行完整的报告修改流程:
        1. 加载或创建对话记忆
        2. 解析用户意图
        3. 规划操作步骤
        4. 执行操作
        5. 渲染新版本
        6. 生成响应说明
        7. 保存结果
        
        Args:
            report_id: 报告ID
            user_request: 用户的自然语言修改请求
            session_id: 会话ID（可选,不提供则创建新会话）
        
        Returns:
            ModificationResult: 修改结果
        
        Raises:
            ValueError: 如果报告不存在或请求无效
            Exception: 执行过程中的其他错误
        """
        start_time = datetime.now()
        operations = []
        
        try:
            # 步骤1: 加载或创建对话记忆
            await self._send_progress(report_id, "正在加载会话状态...")
            logger.info(f"开始修改报告 {report_id}, 请求: {user_request[:100]}")
            
            memory = self.memory_manager.get_or_create_memory(
                report_id=report_id,
                session_id=session_id
            )
            
            logger.info(f"会话 {memory.session_id} 已加载, 当前版本: {memory.current_version}")
            
            # 步骤2: 解析用户意图
            await self._send_progress(report_id, "正在理解您的需求...")
            parsed_intents = await self._parse_intents(user_request, memory)
            
            if not parsed_intents:
                return self._create_error_result(
                    report_id=report_id,
                    session_id=memory.session_id,
                    error_message="无法理解您的修改请求,请提供更具体的说明。"
                )
            
            logger.info(f"解析出 {len(parsed_intents)} 个意图")
            
            # 步骤3: 规划操作步骤
            await self._send_progress(report_id, "正在规划执行步骤...")
            operation_plan = await self._create_operation_plan(parsed_intents, memory)
            
            logger.info(f"规划了 {len(operation_plan)} 个操作步骤")
            
            # 步骤4: 执行操作
            await self._send_progress(report_id, "正在执行修改...")
            operations = await self._execute_operations(operation_plan, memory)
            
            # 检查是否有操作失败
            failed_operations = [op for op in operations if not op.success]
            if failed_operations:
                error_messages = [op.error_message for op in failed_operations]
                return self._create_error_result(
                    report_id=report_id,
                    session_id=memory.session_id,
                    error_message=f"部分操作失败: {'; '.join(error_messages)}"
                )
            
            logger.info(f"成功执行 {len(operations)} 个操作")
            
            # 步骤5: 渲染新版本
            await self._send_progress(report_id, "正在生成新版本...")
            new_markdown = await self._render_report(memory)
            
            # 步骤6: 生成响应说明
            await self._send_progress(report_id, "正在生成说明...")
            explanation = await self._generate_explanation(
                user_request=user_request,
                operations=operations,
                memory=memory
            )
            
            # 步骤7: 更新记忆并保存结果
            await self._send_progress(report_id, "正在保存结果...")
            updated_memory = self.memory_manager.update_memory(
                memory=memory,
                user_request=user_request,
                parsed_intents=parsed_intents,
                operations=operations,
                system_response=explanation,
                new_markdown_content=new_markdown
            )
            
            # 计算总时长和成本
            total_duration = int((datetime.now() - start_time).total_seconds() * 1000)
            total_cost = sum(op.cost_usd or 0.0 for op in operations)
            llm_calls = sum(1 for op in operations if op.cost_usd and op.cost_usd > 0)
            
            # 创建修改结果
            result = ModificationResult(
                success=True,
                report_id=report_id,
                session_id=updated_memory.session_id,
                operations=operations,
                explanation=explanation,
                new_markdown_content=new_markdown,
                metadata=ModificationMetadata(
                    total_duration_ms=total_duration,
                    total_cost_usd=total_cost,
                    operations_count=len(operations),
                    llm_calls_count=llm_calls,
                    from_version=memory.current_version,
                    to_version=updated_memory.current_version
                )
            )
            
            await self._send_progress(report_id, "修改完成!")
            logger.info(
                f"报告 {report_id} 修改完成, "
                f"版本: {memory.current_version} -> {updated_memory.current_version}, "
                f"耗时: {total_duration}ms, 成本: ${total_cost:.4f}"
            )
            
            return result
        
        except ValueError as e:
            logger.error(f"报告修改失败 (参数错误): {str(e)}")
            return self._create_error_result(
                report_id=report_id,
                session_id=session_id or "unknown",
                error_message=str(e)
            )
        
        except Exception as e:
            logger.exception(f"报告修改失败 (未知错误): {str(e)}")
            return self._create_error_result(
                report_id=report_id,
                session_id=session_id or "unknown",
                error_message=f"系统错误: {str(e)}"
            )
    
    @retry_on_failure(max_retries=2, delay_seconds=1.0)
    @measure_time
    async def _parse_intents(
        self,
        user_request: str,
        memory: ConversationMemory
    ) -> list[ModificationIntent]:
        """
        解析用户意图
        
        调用IntentParser将用户的自然语言请求解析为结构化的意图列表。
        支持重试机制以应对临时性失败。
        
        Args:
            user_request: 用户请求
            memory: 对话记忆
        
        Returns:
            List[ModificationIntent]: 解析出的意图列表
        """
        if not self.intent_parser:
            raise ValueError("IntentParser未初始化,无法解析用户意图")
        
        try:
            logger.info(f"开始解析意图: {user_request[:100]}...")
            intents = await self.intent_parser.parse(user_request, memory)
            logger.info(f"意图解析成功: 识别出 {len(intents)} 个意图")
            return intents
        except Exception as e:
            logger.error(f"意图解析失败: {str(e)}", exc_info=True)
            raise ValueError(f"无法理解您的请求: {str(e)}")
    
    async def _create_operation_plan(
        self,
        intents: list[ModificationIntent],
        memory: ConversationMemory
    ) -> list[OperationStep]:
        """
        创建操作计划
        
        根据解析的意图和当前状态,规划具体的操作步骤。
        
        Args:
            intents: 意图列表
            memory: 对话记忆
        
        Returns:
            List[OperationStep]: 操作步骤列表
        """
        try:
            operation_plan = self.operation_planner.create_plan(intents, memory)
            return operation_plan
        except Exception as e:
            logger.error(f"操作规划失败: {str(e)}")
            raise ValueError(f"无法规划执行步骤: {str(e)}")
    
    async def _execute_operations(
        self,
        operation_plan: list[OperationStep],
        memory: ConversationMemory
    ) -> list[Operation]:
        """
        执行操作计划
        
        按顺序执行规划的操作步骤,更新报告状态。
        
        Args:
            operation_plan: 操作计划
            memory: 对话记忆
        
        Returns:
            List[Operation]: 执行结果列表
        """
        try:
            operations = await self.operation_executor.execute(operation_plan, memory)
            return operations
        except Exception as e:
            logger.error(f"操作执行失败: {str(e)}")
            raise
    
    async def _render_report(self, memory: ConversationMemory) -> str:
        """
        渲染报告
        
        根据当前状态渲染完整的Markdown报告。
        
        Args:
            memory: 对话记忆
        
        Returns:
            str: 渲染后的Markdown内容
        
        Note:
            此方法在Phase 2实现完整逻辑,当前返回当前内容。
        """
        # TODO: Phase 2 - 集成TemplateRenderer
        logger.warning("TemplateRenderer集成未完成,返回当前内容")
        return memory.report_state.markdown_content
    
    async def _generate_explanation(
        self,
        user_request: str,
        operations: list[Operation],
        memory: ConversationMemory
    ) -> str:
        """
        生成用户友好的响应说明
        
        使用LLM或模板生成对修改结果的自然语言解释。
        
        Args:
            user_request: 用户请求
            operations: 执行的操作列表
            memory: 对话记忆
        
        Returns:
            str: 响应说明
        """
        try:
            explanation = await self.explanation_generator.generate(
                user_request=user_request,
                operations=operations,
                memory=memory
            )
            return explanation
        except Exception as e:
            logger.error(f"生成响应说明失败: {str(e)}")
            # 回退到简单文本
            return f"已完成您的修改请求,共执行了{len(operations)}个操作。"
    
    async def _send_progress(self, report_id: str, message: str) -> None:
        """
        发送进度更新
        
        通过WebSocket向客户端推送进度信息。
        
        Args:
            report_id: 报告ID
            message: 进度消息
        """
        if self.websocket_manager:
            try:
                await self.websocket_manager.send_message(
                    task_id=report_id,
                    message={
                        "type": "modification_progress",
                        "message": message,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            except Exception as e:
                logger.warning(f"发送进度更新失败: {str(e)}")
    
    def _create_error_result(
        self,
        report_id: str,
        session_id: str,
        error_message: str
    ) -> ModificationResult:
        """
        创建错误结果
        
        Args:
            report_id: 报告ID
            session_id: 会话ID
            error_message: 错误信息
        
        Returns:
            ModificationResult: 错误结果对象
        """
        return ModificationResult(
            success=False,
            report_id=report_id,
            session_id=session_id,
            operations=[],
            explanation="很抱歉,修改请求执行失败。",
            new_markdown_content="",
            metadata=ModificationMetadata(
                total_duration_ms=0,
                total_cost_usd=0.0,
                operations_count=0,
                llm_calls_count=0,
                from_version=0,
                to_version=0
            ),
            error_message=error_message
        )
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计信息
        
        返回LLM调用追踪器的统计数据,包括总调用次数、成本、时长等。
        
        Returns:
            Dict[str, Any]: 性能统计字典
        """
        return llm_tracker.get_stats()
    
    def reset_stats(self) -> None:
        """
        重置性能统计
        
        清空LLM调用追踪器的所有统计数据。
        """
        llm_tracker.reset()
        logger.info("性能统计已重置")

