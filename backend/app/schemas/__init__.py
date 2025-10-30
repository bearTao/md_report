"""API schemas"""

from app.schemas.api_schemas import (
    # Enums
    ReportStatusEnum,
    VariableStatusEnum,
    DBEngineEnum,
    # Template schemas
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    TemplateListItem,
    TemplateListResponse,
    # Report schemas
    ReportGenerateRequest,
    ReportGenerateResponse,
    ReportResponse,
    ReportListItem,
    ReportListResponse,
    ReportUpdateRequest,
    # AI Config schemas
    AIConfigResponse,
    AIConfigUpdate,
    # Task status schemas
    TaskVariableDetail,
    TaskStatusResponse,
    # Standard API response
    APIResponse,
    # Database connection schemas
    DBConnectionCreate,
    DBConnectionUpdate,
    DBConnectionResponse,
    DBConnectionListItem,
    DBConnectionListResponse,
    DBConnectionTestResponse,
    # Task control schemas
    TaskCancelRequest,
    TaskCancelResponse,
    VariableRetryResponse,
    # Execution log schemas
    ExecutionLogItem,
    ExecutionLogListResponse,
    # Template validation schemas
    ValidationIssue,
    TemplateValidationResponse,
)

__all__ = [
    # Enums
    "ReportStatusEnum",
    "VariableStatusEnum",
    "DBEngineEnum",
    # Template schemas
    "TemplateCreate",
    "TemplateUpdate",
    "TemplateResponse",
    "TemplateListItem",
    "TemplateListResponse",
    # Report schemas
    "ReportGenerateRequest",
    "ReportGenerateResponse",
    "ReportResponse",
    "ReportListItem",
    "ReportListResponse",
    "ReportUpdateRequest",
    # AI Config schemas
    "AIConfigResponse",
    "AIConfigUpdate",
    # Task status schemas
    "TaskVariableDetail",
    "TaskStatusResponse",
    # Standard API response
    "APIResponse",
    # Database connection schemas
    "DBConnectionCreate",
    "DBConnectionUpdate",
    "DBConnectionResponse",
    "DBConnectionListItem",
    "DBConnectionListResponse",
    "DBConnectionTestResponse",
    # Task control schemas
    "TaskCancelRequest",
    "TaskCancelResponse",
    "VariableRetryResponse",
    # Execution log schemas
    "ExecutionLogItem",
    "ExecutionLogListResponse",
    # Template validation schemas
    "ValidationIssue",
    "TemplateValidationResponse",
]

