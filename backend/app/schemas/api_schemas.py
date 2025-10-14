"""API request/response schemas"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
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
    inputs: Dict[str, Any] = Field(..., description="User input values")


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


class AIConfigUpdate(BaseModel):
    provider: str = "openai"
    api_key: str


# Standard API response
class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

