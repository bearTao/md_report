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

from app.core.agent_config import get_config
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
from app.services.websocket_manager import WebSocketManager
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
        websocket_manager: Optional[WebSocketManager] = None
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
        
        # 加载配置
        config = get_config()
        logger.info(f"Agent配置已加载 - 日志级别: {config.log_level}")
        
        # 初始化子组件(Phase 2)
        # 所有配置现在从配置文件中读取
        try:
            self.intent_parser = IntentParser()
            logger.info("IntentParser初始化成功")
        except Exception as e:
            logger.warning(f"IntentParser初始化失败: {str(e)}")
            self.intent_parser = None
        
        self.operation_planner = OperationPlanner()
        self.operation_executor = OperationExecutor(db)
        self.explanation_generator = ExplanationGenerator()
    
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
        
        """
        template = memory.report_state.template_content
        variables = {name: var.value for name, var in memory.report_state.variables.items()}
        if not template:
            return memory.report_state.markdown_content
        try:
            content = self.template_renderer.render(template, variables)
            return content
        except Exception as e:
            logger.warning(f"模板渲染失败,回退到现有内容: {str(e)}")
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
                from app.services.websocket_manager import WSEventType
                await self.websocket_manager.send_event(
                    task_id=report_id,
                    event_type=WSEventType.VARIABLE_PROGRESS,
                    data={"message": message}
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
        # 安全获取当前版本号
        current_version = 0
        try:
            # 避免在session_id为"unknown"时创建新memory
            safe_session_id = None if session_id == "unknown" else session_id
            memory = self.memory_manager.get_or_create_memory(report_id, safe_session_id)
            current_version = memory.current_version
        except Exception as e:
            logger.warning(f"获取版本号失败: {str(e)}, 使用默认值0")
        
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
                from_version=current_version,
                to_version=current_version
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
    
    # ========== 删除章节功能 ==========
    
    async def plan_delete_sections(
        self,
        user_message: str,
        conversation_id: str
    ) -> "BatchDeletePlan":
        """
        生成删除计划（不执行）
        
        流程：
        1. 后端精确解析 Markdown 结构
        2. LLM 识别要删除的章节路径
        3. 后端验证和定位
        4. 生成确认信息
        
        Args:
            user_message: 用户删除请求
            conversation_id: 会话ID
        
        Returns:
            BatchDeletePlan: 删除计划
        
        Raises:
            ValueError: 无法定位任何章节
        """
        import json
        import uuid
        from app.services.agent.section_locator import SectionLocator
        from app.services.agent.delete_section_prompts import (
            SECTION_DELETE_SYSTEM_PROMPT,
            format_delete_prompt
        )
        from app.schemas.modification_schemas import (
            BatchDeletePlan,
            SectionDeleteConfirmation
        )
        
        logger.info(f"开始生成删除计划: {user_message}")
        
        # 1. 获取记忆
        memory = self.memory_manager.get_or_create_memory(
            conversation_id=conversation_id,
            session_id=conversation_id
        )
        
        # 2. 后端精确解析结构
        locator = SectionLocator()
        all_sections = locator.parse_markdown_structure(
            memory.report_state.markdown_content
        )
        
        logger.info(f"解析到 {len(all_sections)} 个章节")
        
        if not all_sections:
            raise ValueError("报告中没有章节可以删除")
        
        # 3. 构建章节结构（给LLM看）
        section_structure = locator.build_section_structure_for_llm(
            memory.report_state.markdown_content
        )
        
        # 4. LLM 识别删除目标（只返回路径）
        user_prompt = format_delete_prompt(
            section_structure=section_structure,
            report_content=memory.report_state.markdown_content,
            user_request=user_message
        )
        
        messages = [
            {"role": "system", "content": SECTION_DELETE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await self.intent_parser.llm.ainvoke(messages)
        
        # 5. 解析 LLM 输出
        try:
            llm_result = json.loads(response.content)
            
            if "sections_to_delete" not in llm_result:
                raise ValueError("LLM 输出缺少 sections_to_delete 字段")
            
            if not isinstance(llm_result["sections_to_delete"], list):
                raise ValueError("sections_to_delete 必须是列表")
            
            logger.info(f"LLM 识别到 {len(llm_result['sections_to_delete'])} 个删除目标")
            
        except json.JSONDecodeError as e:
            logger.error(f"LLM 输出不是有效的 JSON: {response.content}")
            raise ValueError(f"LLM 输出格式错误: {str(e)}")
        
        # 6. 后端精确定位和验证
        confirmations = []
        failed_paths = []
        
        for path in llm_result['sections_to_delete']:
            try:
                # 后端定位
                section = locator.locate_section_by_path(all_sections, path)
                
                # 生成确认信息
                confirmation = SectionDeleteConfirmation(
                    section_path=section.path,
                    content_preview=locator.extract_content_preview(
                        memory.report_state.markdown_content,
                        section.start_line,
                        section.end_line,
                        max_chars=200
                    ),
                    section_id=section.id,
                    start_line=section.start_line,
                    end_line=section.end_line
                )
                
                confirmations.append(confirmation)
                
            except ValueError as e:
                logger.error(f"无法定位章节: {path}, 错误: {e}")
                failed_paths.append(path)
                continue
        
        # 7. 验证：至少要有一个可定位的章节
        if not confirmations:
            raise ValueError(
                f"无法定位任何章节。"
                f"LLM 识别了 {len(llm_result['sections_to_delete'])} 个路径，"
                f"但后端都无法精确定位。失败的路径: {failed_paths}"
            )
        
        if failed_paths:
            logger.warning(f"以下路径无法定位，已跳过: {failed_paths}")
        
        # 8. 生成计划
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        
        plan = BatchDeletePlan(
            plan_id=plan_id,
            conversation_id=conversation_id,
            sections=confirmations,
            total_count=len(confirmations),
            will_lock_report=True,
            lock_warning=(
                f"删除章节后，报告将锁定为静态版本"
                f"（保留数据时间：{memory.report_state.generated_at.strftime('%Y-%m-%d %H:%M')}），"
                f"无法再修改参数。"
            )
        )
        
        # 9. 临时保存计划（缓存到内存中）
        self._save_delete_plan(plan_id, plan)
        
        logger.info(f"删除计划生成完成: {plan_id}, 共 {len(confirmations)} 个章节")
        
        return plan
    
    async def execute_delete_plan(
        self,
        plan_id: str,
        action: str,
        decisions: list
    ) -> "DeleteExecutionResult":
        """
        执行删除计划
        
        Args:
            plan_id: 计划ID
            action: "delete_and_lock" | "regenerate_without"
            decisions: 用户决策列表
        
        Returns:
            DeleteExecutionResult: 执行结果
        
        Raises:
            ValueError: 计划不存在或操作类型未知
        """
        from app.schemas.modification_schemas import DeleteExecutionResult, UserDecision
        
        logger.info(f"开始执行删除计划: {plan_id}, 操作: {action}")
        
        # 1. 加载计划
        plan = self._load_delete_plan(plan_id)
        
        if action == "delete_and_lock":
            return await self._delete_and_lock(plan, decisions)
        elif action == "regenerate_without":
            # TODO: 实现重新生成功能
            raise NotImplementedError("重新生成功能暂未实现")
        else:
            raise ValueError(f"未知操作: {action}")
    
    async def _delete_and_lock(
        self,
        plan: "BatchDeletePlan",
        decisions: list
    ) -> "DeleteExecutionResult":
        """
        删除章节并锁定报告
        
        Args:
            plan: 删除计划
            decisions: 用户决策列表
        
        Returns:
            DeleteExecutionResult: 执行结果
        """
        from app.schemas.modification_schemas import DeleteExecutionResult
        
        # 1. 获取记忆
        memory = self.memory_manager.get_or_create_memory(
            conversation_id=plan.conversation_id,
            session_id=plan.conversation_id
        )
        
        # 2. 筛选要删除的章节
        sections_to_delete = []
        skipped_sections = []
        
        for decision in decisions:
            decision_obj = decision if isinstance(decision, dict) else decision.dict()
            
            if decision_obj["decision"] == "execute":
                section = next(
                    (s for s in plan.sections if s.section_id == decision_obj["section_id"]),
                    None
                )
                if section:
                    sections_to_delete.append(section)
            elif decision_obj["decision"] == "skip":
                section = next(
                    (s for s in plan.sections if s.section_id == decision_obj["section_id"]),
                    None
                )
                if section:
                    skipped_sections.append(section.section_path)
        
        if not sections_to_delete:
            return DeleteExecutionResult(
                success=True,
                action_taken="none",
                deleted_sections=[],
                skipped_sections=skipped_sections,
                report_state=self._get_report_state_dict(memory.report_state),
                message="未删除任何章节"
            )
        
        # 3. 锁定报告
        memory.report_state.lock_for_content_edit("用户删除章节")
        
        # 4. 按行号倒序删除（避免行号偏移）
        markdown_lines = memory.report_state.markdown_content.split('\n')
        
        sections_sorted = sorted(
            sections_to_delete,
            key=lambda s: s.start_line,
            reverse=True
        )
        
        deleted_paths = []
        for section in sections_sorted:
            # 删除行范围
            del markdown_lines[section.start_line:section.end_line]
            deleted_paths.append(section.section_path)
            
            logger.info(
                f"已删除章节: {section.section_path} "
                f"(行 {section.start_line}-{section.end_line})"
            )
        
        # 5. 更新内容
        memory.report_state.markdown_content = '\n'.join(markdown_lines)
        memory.current_version += 1
        memory.report_state.version = memory.current_version
        
        # 6. 保存状态
        self.memory_manager.save_memory(memory)
        
        # 7. 清理临时计划
        self._delete_delete_plan(plan.plan_id)
        
        logger.info(f"删除执行完成: 已删除 {len(deleted_paths)} 个章节")
        
        # 8. 返回结果
        return DeleteExecutionResult(
            success=True,
            action_taken="delete_and_lock",
            deleted_sections=deleted_paths,
            skipped_sections=skipped_sections,
            report_state=self._get_report_state_dict(memory.report_state),
            message=(
                f"已删除 {len(deleted_paths)} 个章节。"
                f"报告已锁定为静态版本（数据时间：{memory.report_state.generated_at.strftime('%Y-%m-%d %H:%M')}），"
                f"无法再修改参数。"
            ),
            available_operations=["delete_section", "modify_text"],
            unavailable_operations=["update_parameter", "add_section"]
        )
    
    def _get_report_state_dict(self, state: "ReportState") -> Dict[str, Any]:
        """获取报告状态字典"""
        return {
            "edit_mode": state.edit_mode,
            "generated_at": state.generated_at.isoformat(),
            "locked_at": state.locked_at.isoformat() if state.locked_at else None,
            "lock_reason": state.lock_reason,
            "version": state.version
        }
    
    # 临时计划缓存（生产环境应使用 Redis）
    _delete_plans_cache: Dict[str, "BatchDeletePlan"] = {}
    
    def _save_delete_plan(self, plan_id: str, plan: "BatchDeletePlan"):
        """保存删除计划到缓存"""
        self._delete_plans_cache[plan_id] = plan
        logger.debug(f"删除计划已缓存: {plan_id}")
    
    def _load_delete_plan(self, plan_id: str) -> "BatchDeletePlan":
        """从缓存加载删除计划"""
        if plan_id not in self._delete_plans_cache:
            raise ValueError(f"删除计划不存在: {plan_id}")
        return self._delete_plans_cache[plan_id]
    
    def _delete_delete_plan(self, plan_id: str):
        """删除缓存的删除计划"""
        if plan_id in self._delete_plans_cache:
            del self._delete_plans_cache[plan_id]
            logger.debug(f"删除计划已清理: {plan_id}")

