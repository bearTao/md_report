"""API request/response schemas"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum


# Enums
class ReportStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Template schemas
class TemplateCreate(BaseModel):
    name: str = Field(..., description="Template name")
    description: Optional[str] = None
    template_content: str = Field(..., description="Jinja2 template content")
    metadata: Dict[str, Any] = Field(..., description="Variable metadata")


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    template_content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    template_content: str
    metadata_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TemplateListItem(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    items: List[TemplateListItem]
    total: int


# Report generation schemas
class ReportGenerateRequest(BaseModel):
    template_id: str = Field(..., description="Template ID")
    inputs: Dict[str, Any] = Field(..., description="User input values (supports nested structure for templates with includes)")


class ReportGenerateResponse(BaseModel):
    task_id: str
    status: ReportStatusEnum


class ReportResponse(BaseModel):
    id: str
    template_id: str
    task_id: Optional[str]
    title: Optional[str]
    status: ReportStatusEnum
    markdown_content: str
    cost_usd: Optional[float]
    duration_ms: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ReportListItem(BaseModel):
    id: str
    template_id: str
    task_id: Optional[str] = None  # 用于跳转到生成进度页面
    title: Optional[str]
    status: ReportStatusEnum
    created_at: datetime
    
    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    items: List[ReportListItem]
    total: int


# AI Config schemas
class AIConfigResponse(BaseModel):
    configured: bool
    provider: Optional[str] = "openai"
    api_base: Optional[str] = None


class AIConfigUpdate(BaseModel):
    provider: str = "openai"
    api_key: str
    api_base: Optional[str] = None


# Task status schemas
class VariableStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class TaskVariableDetail(BaseModel):
    variable_name: str
    source: str
    status: VariableStatusEnum
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_ms: Optional[int]
    error_message: Optional[str]
    # Allow dict, list, or primitive types for result preview
    # This supports various variable types (objects, arrays, strings, etc.)
    result_preview: Optional[Union[Dict[str, Any], List[Any], str, int, float, bool]]
    
    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    task_id: str
    template_id: str
    status: ReportStatusEnum
    inputs_json: Dict[str, Any]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime
    report_id: Optional[str] = None
    variables: List[TaskVariableDetail] = []
    
    class Config:
        from_attributes = True


# Standard API response
class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


# Database connection schemas
class DBEngineEnum(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLSERVER = "sqlserver"
    ORACLE = "oracle"


class DBConnectionCreate(BaseModel):
    name: str = Field(..., description="Connection name (unique)")
    engine: DBEngineEnum = Field(..., description="Database engine type")
    host: str = Field(..., description="Database host")
    port: int = Field(..., description="Database port")
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")
    options: Optional[Dict[str, Any]] = Field(None, description="Additional connection options")
    is_active: bool = Field(True, description="Whether the connection is active")


class DBConnectionUpdate(BaseModel):
    name: Optional[str] = None
    engine: Optional[DBEngineEnum] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class DBConnectionResponse(BaseModel):
    id: str
    name: str
    engine: DBEngineEnum
    host: str
    port: int
    database: str
    username: str
    options: Optional[Dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DBConnectionListItem(BaseModel):
    id: str
    name: str
    engine: DBEngineEnum
    host: str
    port: int
    database: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class DBConnectionListResponse(BaseModel):
    items: List[DBConnectionListItem]
    total: int


class DBConnectionTestResponse(BaseModel):
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


# Task control schemas
class TaskCancelRequest(BaseModel):
    """Request to cancel a task"""
    reason: Optional[str] = Field(None, description="Reason for cancellation")


class TaskCancelResponse(BaseModel):
    """Response for task cancellation"""
    task_id: str
    status: str
    cancelled_at: datetime


class VariableRetryResponse(BaseModel):
    """Response for variable retry"""
    task_id: str
    variable_name: str
    retry_status: str


# Execution log schemas
class ExecutionLogItem(BaseModel):
    """Single execution log item"""
    id: int
    task_id: str
    variable_name: Optional[str]
    level: str
    message: str
    context: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ExecutionLogListResponse(BaseModel):
    """List of execution logs"""
    logs: List[ExecutionLogItem]
    total: int


# Template validation schemas
class ValidationIssue(BaseModel):
    """Single validation issue"""
    level: str = Field(..., description="Issue level: error or warning")
    category: str = Field(..., description="Issue category: syntax, metadata, dependency, schema")
    message: str = Field(..., description="Detailed issue message")
    location: Optional[str] = Field(None, description="Location of the issue")


class TemplateValidationResponse(BaseModel):
    """Template validation result"""
    valid: bool
    issues: List[ValidationIssue]


# Debug schemas
class DebugRenderRequest(BaseModel):
    """Request for template debug rendering"""
    template_content: str = Field(..., description="Jinja2 template content to render")
    metadata_yaml: str = Field(..., description="Variable metadata in YAML format")
    user_inputs: Dict[str, Any] = Field(default_factory=dict, description="User input values")


class DebugVariableResult(BaseModel):
    """Result of a single variable execution in debug mode"""
    variable_name: str
    status: str
    value: Any
    duration_ms: int
    error_message: Optional[str] = None


class DebugRenderResponse(BaseModel):
    """Response for template debug rendering"""
    success: bool
    rendered_markdown: Optional[str] = None
    variables: List[DebugVariableResult]
    error: Optional[str] = None


class DeleteReportResponse(BaseModel):
    """删除报告响应"""
    success: bool
    message: str
    deleted_items: Dict[str, int] = Field(..., description="各表删除的记录数")

