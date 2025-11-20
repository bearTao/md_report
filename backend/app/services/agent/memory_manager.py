"""
对话记忆管理器

本模块负责管理报告修改会话的记忆和状态,包括:
- 加载和保存会话状态
- 管理对话历史
- 生成上下文总结
- 清理过期会话
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import uuid
import json
import os
import logging

logger = logging.getLogger(__name__)

from app.models.db_models import (
    ConversationSession,
    ConversationTurn,
    ReportState as DBReportState,
    Report
)
from app.schemas.modification_schemas import (
    ConversationMemory,
    ConversationTurn as ConversationTurnSchema,
    ReportState,
    VariableInfo,
    VariableType,
    ModificationIntent,
    Operation
)


class MemoryManager:
    """
    对话记忆管理器类
    
    负责管理报告修改会话的完整生命周期,包括会话创建、状态持久化、
    对话历史管理和上下文总结生成。
    
    Attributes:
        db: 数据库会话
        max_history_turns: 最大保留的对话轮次数
        context_summary_threshold: 触发上下文总结的轮次阈值
    """
    
    def __init__(
        self, 
        db: Session,
        max_history_turns: int = 10,
        context_summary_threshold: int = 10,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None
    ):
        """
        初始化记忆管理器
        
        Args:
            db: 数据库会话
            max_history_turns: 内存中保留的最大对话轮次数（默认10轮）
            context_summary_threshold: 触发上下文总结的轮次阈值（默认10轮）
            api_key: OpenAI API密钥（可选,用于上下文总结）
            api_base: OpenAI API基础URL（可选）
        """
        self.db = db
        self.max_history_turns = max_history_turns
        self.context_summary_threshold = context_summary_threshold
        
        # 初始化LLM（用于上下文总结）
        self.llm = None
        try:
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            api_base = api_base or os.getenv("OPENAI_API_BASE")
            
            if api_key:
                llm_kwargs = {
                    "model": "gpt-4",
                    "temperature": 0.1,
                    "api_key": api_key
                }
                if api_base:
                    llm_kwargs["base_url"] = api_base
                
                self.llm = ChatOpenAI(**llm_kwargs)
                logger.info("记忆管理器已启用LLM上下文总结功能")
            else:
                logger.warning("未配置OpenAI API密钥,上下文总结将使用简单模式")
        except Exception as e:
            logger.warning(f"初始化LLM失败: {str(e)},上下文总结将使用简单模式")
    
    def get_or_create_memory(
        self, 
        report_id: str, 
        session_id: Optional[str] = None
    ) -> ConversationMemory:
        """
        获取或创建对话记忆
        
        如果提供了session_id,则加载现有会话;否则创建新会话。
        
        Args:
            report_id: 报告ID
            session_id: 会话ID（可选）
        
        Returns:
            ConversationMemory: 对话记忆对象
        
        Raises:
            ValueError: 如果报告不存在或会话ID无效
        """
        # 验证报告是否存在
        report = self.db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise ValueError(f"报告不存在: {report_id}")
        
        if session_id:
            # 加载现有会话
            return self._load_memory_from_db(session_id, report_id)
        else:
            # 创建新会话
            return self._create_new_memory(report_id, report)
    
    def _create_new_memory(self, report_id: str, report: Report) -> ConversationMemory:
        """
        创建新的对话记忆
        
        Args:
            report_id: 报告ID
            report: 报告对象
        
        Returns:
            ConversationMemory: 新创建的对话记忆
        """
        # 生成会话ID
        session_id = f"session_{uuid.uuid4().hex[:16]}"
        
        # 创建会话记录
        db_session = ConversationSession(
            id=session_id,
            report_id=report_id,
            status="active",
            last_activity_at=datetime.now()
        )
        self.db.add(db_session)
        
        # 从报告构建初始状态
        report_state = self._build_initial_state(report)
        
        # 保存初始状态到数据库
        db_report_state = DBReportState(
            report_id=report_id,
            session_id=session_id,
            version=1,
            template_id=report.template_id,
            template_content=None,  # 初始状态使用原始模板
            template_metadata=None,
            variables_state=self._serialize_variables(report_state.variables),
            markdown_content=report.markdown_content
        )
        self.db.add(db_report_state)
        self.db.commit()
        
        # 创建ConversationMemory对象
        memory = ConversationMemory(
            session_id=session_id,
            report_id=report_id,
            report_state=report_state,
            conversation_history=[],
            context_summary=None,
            current_version=1
        )
        
        return memory
    
    def _load_memory_from_db(self, session_id: str, report_id: str) -> ConversationMemory:
        """
        从数据库加载对话记忆
        
        Args:
            session_id: 会话ID
            report_id: 报告ID
        
        Returns:
            ConversationMemory: 加载的对话记忆
        
        Raises:
            ValueError: 如果会话不存在或不匹配报告
        """
        # 加载会话
        db_session = self.db.query(ConversationSession).filter(
            ConversationSession.id == session_id
        ).first()
        
        if not db_session:
            raise ValueError(f"会话不存在: {session_id}")
        
        if db_session.report_id != report_id:
            raise ValueError(f"会话 {session_id} 不属于报告 {report_id}")
        
        # 加载最新的报告状态
        latest_state = self.db.query(DBReportState).filter(
            DBReportState.session_id == session_id
        ).order_by(DBReportState.version.desc()).first()
        
        if not latest_state:
            raise ValueError(f"会话 {session_id} 没有报告状态")
        
        # 加载对话历史（最近N轮）
        db_turns = self.db.query(ConversationTurn).filter(
            ConversationTurn.session_id == session_id
        ).order_by(
            ConversationTurn.turn_number.desc()
        ).limit(self.max_history_turns).all()
        
        # 反转顺序（从旧到新）
        db_turns = list(reversed(db_turns))
        
        # 构建ReportState对象
        report_state = ReportState(
            report_id=report_id,
            version=latest_state.version,
            template_id=latest_state.template_id,
            template_content=latest_state.template_content,
            template_metadata=latest_state.template_metadata,
            variables=self._deserialize_variables(latest_state.variables_state),
            markdown_content=latest_state.markdown_content
        )
        
        # 构建ConversationTurn列表
        conversation_history = [
            self._db_turn_to_schema(turn) for turn in db_turns
        ]
        
        # 创建ConversationMemory对象
        memory = ConversationMemory(
            session_id=session_id,
            report_id=report_id,
            report_state=report_state,
            conversation_history=conversation_history,
            context_summary=db_session.context_summary,
            current_version=latest_state.version
        )
        
        # 更新最后活跃时间
        db_session.last_activity_at = datetime.now()
        self.db.commit()
        
        return memory
    
    def update_memory(
        self,
        memory: ConversationMemory,
        user_request: str,
        parsed_intents: List[ModificationIntent],
        operations: List[Operation],
        system_response: str,
        new_markdown_content: str
    ) -> ConversationMemory:
        """
        更新对话记忆（添加新的对话轮次）
        
        Args:
            memory: 当前的对话记忆
            user_request: 用户请求
            parsed_intents: 解析的意图列表
            operations: 执行的操作列表
            system_response: 系统响应
            new_markdown_content: 新的Markdown内容
        
        Returns:
            ConversationMemory: 更新后的对话记忆
        """
        # 增加版本号
        new_version = memory.current_version + 1
        
        # 更新报告状态
        memory.report_state.version = new_version
        memory.report_state.markdown_content = new_markdown_content
        
        # 创建新的对话轮次
        turn_number = len(memory.conversation_history) + 1
        new_turn = ConversationTurnSchema(
            turn_number=turn_number,
            user_request=user_request,
            parsed_intents=parsed_intents,
            operations=operations,
            system_response=system_response,
            report_version=new_version,
            timestamp=datetime.now()
        )
        
        # 添加到对话历史
        memory.conversation_history.append(new_turn)
        
        # 如果对话历史超过最大长度,移除最旧的
        if len(memory.conversation_history) > self.max_history_turns:
            memory.conversation_history.pop(0)
        
        # 检查是否需要生成上下文总结
        if turn_number >= self.context_summary_threshold and turn_number % 5 == 0:
            memory.context_summary = self._generate_context_summary(memory)
        
        # 更新当前版本
        memory.current_version = new_version
        
        # 保存到数据库
        self._save_memory_to_db(memory, new_turn)
        
        return memory
    
    def save_state_snapshot(
        self,
        memory: ConversationMemory
    ) -> None:
        """
        保存报告状态快照到数据库
        
        Args:
            memory: 对话记忆对象
        """
        db_state = DBReportState(
            report_id=memory.report_id,
            session_id=memory.session_id,
            version=memory.current_version,
            template_id=memory.report_state.template_id,
            template_content=memory.report_state.template_content,
            template_metadata=memory.report_state.template_metadata,
            variables_state=self._serialize_variables(memory.report_state.variables),
            markdown_content=memory.report_state.markdown_content
        )
        self.db.add(db_state)
        self.db.commit()
    
    def _save_memory_to_db(
        self,
        memory: ConversationMemory,
        new_turn: ConversationTurnSchema
    ) -> None:
        """
        保存对话记忆到数据库
        
        Args:
            memory: 对话记忆
            new_turn: 新的对话轮次
        """
        # 保存新的报告状态
        self.save_state_snapshot(memory)
        
        # 保存新的对话轮次
        db_turn = ConversationTurn(
            session_id=memory.session_id,
            turn_number=new_turn.turn_number,
            user_request=new_turn.user_request,
            parsed_intents=[intent.model_dump() for intent in new_turn.parsed_intents],
            operations_executed=[op.model_dump() for op in new_turn.operations],
            system_response=new_turn.system_response,
            report_version=new_turn.report_version
        )
        self.db.add(db_turn)
        
        # 更新会话的上下文总结和最后活跃时间
        db_session = self.db.query(ConversationSession).filter(
            ConversationSession.id == memory.session_id
        ).first()
        
        if db_session:
            db_session.context_summary = memory.context_summary
            db_session.last_activity_at = datetime.now()
        
        self.db.commit()
    
    def cleanup_inactive_sessions(self, hours: int = 24, inactive_hours: int = None, days: int = None) -> int:
        """
        清理不活跃的会话
        
        将超过指定时间未活跃的会话标记为inactive。
        
        Args:
            inactive_hours: 不活跃时间阈值（小时）
        
        Returns:
            int: 清理的会话数量
        """
        threshold_hours = inactive_hours if inactive_hours is not None else (days * 24 if days is not None else hours)
        threshold = datetime.now() - timedelta(hours=threshold_hours)
        
        inactive_sessions = self.db.query(ConversationSession).filter(
            ConversationSession.status == "active",
            ConversationSession.last_activity_at < threshold
        ).all()
        
        count = 0
        for session in inactive_sessions:
            session.status = "inactive"
            count += 1
        
        self.db.commit()
        return count
    
    def _build_initial_state(self, report: Report) -> ReportState:
        """
        从报告构建初始状态
        
        Args:
            report: 报告对象
        
        Returns:
            ReportState: 初始报告状态
        """
        from app.models.db_models import Template, GenerationTask
        variables: Dict[str, VariableInfo] = {}
        template_content = None
        template_metadata = None
        
        # 加载模板
        template = self.db.query(Template).filter(Template.id == report.template_id).first()
        if template:
            template_content = template.template_content
            template_metadata = template.metadata_json or {}
            
            # 先从模板元数据构建变量（使用默认值）
            for name, cfg in (template_metadata or {}).items():
                default_val = cfg.get("default") if isinstance(cfg, dict) else None
                if default_val is None and isinstance(cfg, dict):
                    default_val = cfg.get("default_value")
                variables[name] = VariableInfo(
                    name=name,
                    value=default_val,
                    source=(cfg.get("source") if isinstance(cfg, dict) else "user_input"),
                    variable_type=VariableType.TEMPLATE,
                    metadata=cfg if isinstance(cfg, dict) else {},
                    last_updated=None,
                )
        
        # 从关联的任务中加载实际的参数值
        if report.task_id:
            task = self.db.query(GenerationTask).filter(GenerationTask.id == report.task_id).first()
            if task and task.inputs_json:
                logger.info(f"从任务 {task.id} 加载实际参数值: {task.inputs_json}")
                # 用实际值覆盖变量的默认值
                for param_name, param_value in task.inputs_json.items():
                    if param_name in variables:
                        # 更新已存在的变量值
                        variables[param_name].value = param_value
                        variables[param_name].last_updated = task.created_at
                        logger.debug(f"更新变量 {param_name} 的值: {param_value}")
                    else:
                        # 添加新的用户输入变量
                        variables[param_name] = VariableInfo(
                            name=param_name,
                            value=param_value,
                            source="user_input",
                            variable_type=VariableType.TEMPLATE,
                            metadata={},
                            last_updated=task.created_at,
                        )
                        logger.debug(f"添加新变量 {param_name}: {param_value}")
        
        return ReportState(
            report_id=report.id,
            version=1,
            template_id=report.template_id,
            template_content=template_content,
            template_metadata=template_metadata,
            variables=variables,
            markdown_content=report.markdown_content
        )
    
    def _serialize_variables(self, variables: Dict[str, VariableInfo]) -> Dict[str, Any]:
        """
        序列化变量信息为JSON格式
        
        Args:
            variables: 变量信息字典
        
        Returns:
            Dict[str, Any]: 可序列化的字典
        """
        return {
            name: var.model_dump(mode='json')
            for name, var in variables.items()
        }
    
    def _deserialize_variables(self, variables_json: Dict[str, Any]) -> Dict[str, VariableInfo]:
        """
        从JSON反序列化变量信息
        
        Args:
            variables_json: JSON格式的变量数据
        
        Returns:
            Dict[str, VariableInfo]: 变量信息字典
        """
        return {
            name: VariableInfo(**var_data)
            for name, var_data in variables_json.items()
        }
    
    def _db_turn_to_schema(self, db_turn: ConversationTurn) -> ConversationTurnSchema:
        """
        将数据库对话轮次转换为Schema对象
        
        Args:
            db_turn: 数据库对话轮次
        
        Returns:
            ConversationTurnSchema: Schema对象
        """
        return ConversationTurnSchema(
            turn_number=db_turn.turn_number,
            user_request=db_turn.user_request,
            parsed_intents=[
                ModificationIntent(**intent) 
                for intent in (db_turn.parsed_intents or [])
            ],
            operations=[
                Operation(**op) 
                for op in (db_turn.operations_executed or [])
            ],
            system_response=db_turn.system_response or "",
            report_version=db_turn.report_version or 1,
            timestamp=db_turn.created_at
        )
    
    def _generate_context_summary(self, memory: ConversationMemory) -> str:
        """
        生成对话上下文总结
        
        使用LLM对长对话历史进行总结,提取关键信息。
        
        Args:
            memory: 对话记忆
        
        Returns:
            str: 上下文总结
        """
        if self.llm:
            try:
                return self._generate_llm_summary(memory)
            except Exception as e:
                logger.error(f"LLM总结生成失败: {str(e)},回退到简单模式")
        
        # 简单模式总结
        return self._generate_simple_summary(memory)
    
    def _generate_llm_summary(self, memory: ConversationMemory) -> str:
        """
        使用LLM生成智能上下文总结
        
        Args:
            memory: 对话记忆
        
        Returns:
            str: LLM生成的总结
        """
        # 构建对话历史文本
        conversation_text = []
        for turn in memory.conversation_history:
            conversation_text.append(f"用户: {turn.user_request}")
            conversation_text.append(f"系统: {turn.system_response[:200]}...")
            conversation_text.append("")
        
        history_str = "\n".join(conversation_text)
        
        # 构建提示词
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """你是一个对话总结专家。请总结以下报告修改对话的关键信息。

总结要求:
1. 简洁明了,突出关键修改内容
2. 记录用户的主要意图和操作
3. 提及重要的变量或章节修改
4. 保持在200字以内

对话历史:
{history}

请提供简洁的总结:"""),
            ("user", "总结对话")
        ])
        
        prompt = prompt_template.format_messages(history=history_str)
        response = self.llm.invoke(prompt)
        
        summary = response.content.strip()
        logger.info(f"生成LLM上下文总结 ({len(summary)} 字符)")
        
        return summary
    
    def _generate_simple_summary(self, memory: ConversationMemory) -> str:
        """
        生成简单的文本总结（不使用LLM）
        
        Args:
            memory: 对话记忆
        
        Returns:
            str: 简单总结
        """
        summary_parts = [
            f"报告ID: {memory.report_id}",
            f"当前版本: {memory.current_version}",
            f"对话轮次: {len(memory.conversation_history)}轮",
        ]
        
        # 总结最近的修改
        recent_operations = []
        for turn in memory.conversation_history[-5:]:
            ops = getattr(turn, "operations", [])
            if isinstance(ops, list):
                for op in ops:
                    recent_operations.append(f"- {op.operation_type}: {turn.user_request[:50]}")
        
        if recent_operations:
            summary_parts.append("\n最近的修改:\n" + "\n".join(recent_operations))
        
        return "\n".join(summary_parts)
    
    def format_recent_context(
        self,
        memory: ConversationMemory,
        limit: int = 3
    ) -> str:
        """
        格式化最近的对话上下文（用于意图解析）
        
        Args:
            memory: 对话记忆
            max_turns: 最大轮次数（默认3轮）
        
        Returns:
            str: 格式化的上下文文本
        """
        context_parts = []
        
        # 添加总体摘要（如果有）
        if memory.context_summary:
            context_parts.append(f"对话摘要:\n{memory.context_summary}\n")
        
        # 添加最近N轮对话
        recent_turns = memory.conversation_history[-limit:] if memory.conversation_history else []
        
        if recent_turns:
            context_parts.append("最近的对话:")
            for turn in recent_turns:
                context_parts.append(f"  [{turn.turn_number}] 用户: {turn.user_request}")
                context_parts.append(f"      系统: {turn.system_response[:100]}...")
        else:
            context_parts.append("（首次对话,无历史上下文）")
        
        return "\n".join(context_parts)

