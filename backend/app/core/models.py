"""Core data models for variable execution"""
from typing import Any, Dict, List, Optional, Literal, Union
from enum import Enum
from pydantic import BaseModel, Field


class VariableSource(str, Enum):
    """Variable data source types"""
    USER_INPUT = "user_input"
    SQL = "sql"
    API = "api"
    AI_GENERATION = "ai_generation"
    SYSTEM = "system"
    CONSTANT = "constant"  # Fixed constant values
    IMAGE = "image"
    VISION_AI = "vision_ai"


class VariableStatus(str, Enum):
    """Variable execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class SqlResultMode(str, Enum):
    """SQL result return mode"""
    FIRST_ROW = "first_row"        # 返回第一行作为对象 {col1: val1, col2: val2}
    ALL_ROWS = "all_rows"          # 返回所有行作为数组 [{row1}, {row2}, ...]
    FIRST_VALUE = "first_value"    # 返回第一行第一列的值（标量）
    FIRST_COLUMN = "first_column"  # 返回第一列的所有值 [val1, val2, ...]
    AUTO = "auto"                  # 根据type自动判断（默认）


class SqlConfig(BaseModel):
    """SQL variable configuration"""
    connection: str
    query: str
    parameters: Optional[List[str]] = []
    timeout: Optional[int] = 10
    result_mode: Optional[SqlResultMode] = SqlResultMode.AUTO  # 结果返回模式


class ApiConfig(BaseModel):
    """API variable configuration - Enhanced with JMESPath and retry support"""
    endpoint: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = {}
    parameters: Optional[Dict[str, Any]] = {}  # Changed from Dict[str, str] to support any type
    body: Optional[Dict[str, Any]] = {}
    
    # Response mapping: supports three modes
    # - None or {}: return full response
    # - str: extract single path (returns any type: object/array/string/number)
    # - Dict[str, str]: map multiple fields to new object
    response_mapping: Optional[Union[str, Dict[str, str]]] = None
    
    cache_ttl: Optional[int] = None
    timeout: Optional[int] = 10
    
    # Retry configuration
    retry_count: Optional[int] = 0  # Number of retries, 0 means no retry
    retry_status_codes: Optional[List[int]] = None  # HTTP status codes to retry on
    retry_backoff: Optional[float] = 1.0  # Backoff factor in seconds


class AiConfig(BaseModel):
    """AI generation configuration"""
    model: str
    prompt_template: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000
    response_format: Optional[str] = "json_object"


class SystemConfig(BaseModel):
    """System variable configuration"""
    fields: Dict[str, Dict[str, Any]]


class UiConfig(BaseModel):
    """UI configuration for user input"""
    input_type: str
    placeholder: Optional[str] = None


class ImageConfig(BaseModel):
    """Image variable configuration"""
    endpoint: str  # API endpoint, supports variable interpolation
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    parameters: Optional[Dict[str, Any]] = None
    output_format: Literal["base64", "url", "bytes"] = "base64"
    multiple: bool = False  # Whether to fetch multiple images
    timeout: Optional[int] = 30
    
    class Config:
        extra = "forbid"


class VisionAiConfig(BaseModel):
    """Vision AI configuration"""
    model: str = "gpt-4o"
    image_source: str  # Name of the image variable to analyze
    prompt_template: str  # Prompt template with variable interpolation
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 500
    system_prompt: Optional[str] = None  # Optional system prompt
    
    class Config:
        extra = "forbid"


class VariableMetadata(BaseModel):
    """Variable metadata definition"""
    type: str  # string, number, boolean, array, object
    source: VariableSource
    required: bool = False
    description: str
    default: Optional[Any] = None
    dependencies: Optional[List[str]] = []
    schema: Optional[Dict[str, Any]] = None
    
    # For constant variables: the fixed value
    value: Optional[Any] = None
    
    # Source-specific configs
    sql_config: Optional[SqlConfig] = None
    api_config: Optional[ApiConfig] = None
    ai_config: Optional[AiConfig] = None
    system_config: Optional[SystemConfig] = None
    ui_config: Optional[UiConfig] = None
    image_config: Optional[ImageConfig] = None
    vision_ai_config: Optional[VisionAiConfig] = None


class VariableExecutionResult(BaseModel):
    """Result of variable execution"""
    variable_name: str
    status: VariableStatus
    value: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = {}  # execution details


class TaskContext(BaseModel):
    """Execution task context"""
    task_id: str
    template_id: str
    user_inputs: Dict[str, Any]
    variables: Dict[str, Any] = {}  # Variable results
    metadata: Dict[str, VariableMetadata]

