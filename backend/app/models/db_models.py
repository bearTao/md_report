"""Database ORM models"""
from sqlalchemy import Column, String, Text, DateTime, Integer, JSON, Enum as SQLEnum, Numeric, Boolean
from sqlalchemy.sql import func
from datetime import datetime
import enum
from app.database import Base


class ReportStatus(str, enum.Enum):
    """Report/Task status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VariableSourceType(str, enum.Enum):
    """Variable source types"""
    USER_INPUT = "user_input"
    SQL = "sql"
    API = "api"
    AI_GENERATION = "ai_generation"
    SYSTEM = "system"
    CONSTANT = "constant"
    IMAGE = "image"
    VISION_AI = "vision_ai"


class VariableStatusType(str, enum.Enum):
    """Variable execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class LogLevel(str, enum.Enum):
    """Log level for execution logs"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Template(Base):
    """Template model"""
    __tablename__ = "templates"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    template_content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GenerationTask(Base):
    """Report generation task"""
    __tablename__ = "generation_tasks"
    
    id = Column(String(50), primary_key=True)
    template_id = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default='pending')  # 改为字符串避免枚举问题
    inputs_json = Column(JSON, nullable=False)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    render_error = Column(JSON, nullable=True)  # 模板渲染错误信息


class GenerationTaskVariable(Base):
    """Variable execution details for a task"""
    __tablename__ = "generation_task_variables"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), nullable=False, index=True)
    variable_name = Column(String(100), nullable=False)
    source = Column(String(50), nullable=False)  # 改为字符串避免枚举问题
    status = Column(String(50), nullable=False, default='pending')  # 改为字符串避免枚举问题
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)
    error_code = Column(String(50))
    error_message = Column(Text)
    result_preview = Column(JSON)
    template_id = Column(String(50), nullable=True)  # 所属模板ID
    template_path = Column(String(500), nullable=True)  # 完整层级路径


class Report(Base):
    """Generated report"""
    __tablename__ = "reports"
    
    id = Column(String(50), primary_key=True)
    template_id = Column(String(50), nullable=False)
    task_id = Column(String(50), unique=True)
    title = Column(String(200))
    status = Column(String(50), nullable=False)  # 改为字符串避免枚举问题
    markdown_content = Column(Text, nullable=False)
    cost_usd = Column(Numeric(10, 4))
    duration_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AIProviderKey(Base):
    """AI provider API keys"""
    __tablename__ = "ai_provider_keys"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False)
    api_key_ciphertext = Column(Text, nullable=False)
    api_base = Column(String(500), nullable=True)  # API base URL (e.g., for proxies)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DBEngineType(str, enum.Enum):
    """Database engine types"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLSERVER = "sqlserver"
    ORACLE = "oracle"


class DBConnection(Base):
    """Database connection configurations"""
    __tablename__ = "db_connections"
    
    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    engine = Column(SQLEnum(DBEngineType), nullable=False)
    host = Column(String(500), nullable=False)
    port = Column(Integer, nullable=False)
    database = Column(String(200), nullable=False)
    username = Column(String(200), nullable=False)
    password_ciphertext = Column(Text, nullable=False)
    options_json = Column(JSON)  # Additional connection options
    is_active = Column(Boolean, default=True)  # PostgreSQL 原生布尔类型
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ExecutionLog(Base):
    """Execution logs for tasks and variables"""
    __tablename__ = "execution_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), nullable=False, index=True)
    variable_name = Column(String(200), nullable=True, index=True)  # NULL for task-level logs
    level = Column(SQLEnum(LogLevel), nullable=False, index=True)
    message = Column(Text, nullable=False)
    context_json = Column(JSON, nullable=True)  # Additional context information
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    template_id = Column(String(50), nullable=True)  # 所属模板ID
    template_path = Column(String(500), nullable=True)  # 完整层级路径


class ConversationSessionStatus(str, enum.Enum):
    """对话会话状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"


class ConversationSession(Base):
    """
    对话会话模型
    
    用于管理报告修改的对话会话生命周期,每个报告可以有一个活跃的会话。
    会话包含多轮对话交互和上下文信息。
    """
    __tablename__ = "conversation_sessions"
    
    id = Column(String(50), primary_key=True)
    report_id = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="active")
    context_summary = Column(Text, nullable=True)  # 对话上下文总结（长对话时使用）
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ConversationTurn(Base):
    """
    对话轮次模型
    
    存储每一轮用户输入和系统响应,用于构建对话历史和上下文理解。
    """
    __tablename__ = "conversation_turns"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), nullable=False, index=True)
    turn_number = Column(Integer, nullable=False)  # 该会话中的轮次编号（从1开始）
    user_request = Column(Text, nullable=False)  # 用户的修改请求
    parsed_intents = Column(JSON, nullable=True)  # 解析出的意图列表
    operations_executed = Column(JSON, nullable=True)  # 执行的操作列表
    system_response = Column(Text, nullable=True)  # 系统响应说明
    report_version = Column(Integer, nullable=True)  # 关联的报告状态版本号
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class ReportState(Base):
    """
    报告状态模型
    
    存储报告在每个版本的完整状态,包括所有变量值、模板内容和元数据。
    支持状态回滚和版本追踪。
    """
    __tablename__ = "report_states"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(50), nullable=False, index=True)
    session_id = Column(String(50), nullable=False, index=True)
    version = Column(Integer, nullable=False)  # 版本号（从1开始递增）
    template_id = Column(String(50), nullable=False)  # 原始模板ID
    template_content = Column(Text, nullable=True)  # 临时模板内容（如果被修改）
    template_metadata = Column(JSON, nullable=True)  # 临时模板元数据（如果被修改）
    variables_state = Column(JSON, nullable=False)  # 所有变量的状态（包括模板变量和运行时变量）
    markdown_content = Column(Text, nullable=False)  # 该版本渲染后的Markdown内容
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OperationType(str, enum.Enum):
    """操作类型枚举"""
    UPDATE_PARAMETER = "update_parameter"
    REFINE_AI_CONTENT = "refine_ai_content"
    ADD_SECTION = "add_section"
    MODIFY_SECTION = "modify_section"
    REMOVE_SECTION = "remove_section"


class ReportModificationHistory(Base):
    """
    报告修改历史模型
    
    详细记录每次修改操作的审计信息,包括操作类型、影响范围、执行结果等。
    """
    __tablename__ = "report_modification_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(50), nullable=False, index=True)
    session_id = Column(String(50), nullable=False, index=True)
    turn_id = Column(Integer, nullable=False)  # 关联的对话轮次ID
    operation_type = Column(String(50), nullable=False)  # 操作类型
    operation_details = Column(JSON, nullable=False)  # 操作详细信息（包括目标变量、新值等）
    affected_variables = Column(JSON, nullable=True)  # 受影响的变量列表
    from_version = Column(Integer, nullable=False)  # 修改前的版本号
    to_version = Column(Integer, nullable=False)  # 修改后的版本号
    success = Column(Boolean, default=True)  # 操作是否成功
    error_message = Column(Text, nullable=True)  # 错误信息（如果失败）
    duration_ms = Column(Integer, nullable=True)  # 执行时长（毫秒）
    cost_usd = Column(Numeric(10, 4), nullable=True)  # LLM调用成本（美元）
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class AgentComponentType(str, enum.Enum):
    """Agent组件类型枚举"""
    INTENT_PARSER = "intent_parser"
    EXPLANATION_GENERATOR = "explanation_generator"
    AI_REFINEMENT = "ai_refinement"


class AgentLLMConfig(Base):
    """
    Agent LLM配置模型
    
    为每个Agent组件存储独立的LLM配置，包括模型、API密钥、base URL等。
    每个组件可以使用不同的LLM提供商和配置。
    """
    __tablename__ = "agent_llm_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    component = Column(String(50), nullable=False, unique=True)  # 组件类型：intent_parser, explanation_generator, ai_refinement
    model = Column(String(100), nullable=False)  # 模型名称，如 gpt-4, gpt-3.5-turbo, claude-3
    api_key = Column(Text, nullable=True)  # API密钥（可选，如果为空则使用全局配置）
    api_base = Column(String(500), nullable=True)  # API Base URL（可选）
    organization = Column(String(100), nullable=True)  # 组织ID（可选，用于OpenAI）
    temperature = Column(Numeric(3, 2), nullable=False, default=0.7)  # 生成温度
    max_tokens = Column(Integer, nullable=True)  # 最大生成token数
    timeout = Column(Integer, nullable=False, default=60)  # 请求超时时间（秒）
    enabled = Column(Boolean, default=True)  # 是否启用该组件
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

