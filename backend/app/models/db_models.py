"""Database ORM models"""
from sqlalchemy import Column, String, Text, DateTime, Integer, JSON, Enum as SQLEnum, Numeric
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
    is_active = Column(String(10), default="true")  # Use string for boolean
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

