"""Template management API"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import yaml

from app.database import get_db
from app.models.db_models import Template
from app.schemas.api_schemas import (
    TemplateCreate, TemplateUpdate, TemplateResponse,
    TemplateListItem, TemplateListResponse,
    TemplateValidationResponse
)
from app.services.renderer import template_renderer


router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Search query"),
    db: Session = Depends(get_db)
):
    """Get template list with pagination and search"""
    query = db.query(Template)
    
    # Search filter
    if q:
        query = query.filter(
            (Template.name.contains(q)) | (Template.description.contains(q))
        )
    
    # Total count
    total = query.count()
    
    # Pagination
    offset = (page - 1) * page_size
    templates = query.order_by(Template.created_at.desc()).offset(offset).limit(page_size).all()
    
    items = [
        TemplateListItem(
            id=t.id,
            name=t.name,
            description=t.description,
            created_at=t.created_at
        )
        for t in templates
    ]
    
    return TemplateListResponse(items=items, total=total)


@router.post("", response_model=TemplateResponse, status_code=201)
async def create_template(
    template_data: TemplateCreate,
    db: Session = Depends(get_db)
):
    """Create a new template"""
    # Validate template syntax
    is_valid, error_msg = template_renderer.validate_template(template_data.template_content)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid template syntax: {error_msg}")
    
    # Validate metadata (basic check)
    if not isinstance(template_data.metadata, dict):
        raise HTTPException(status_code=400, detail="Metadata must be a dictionary")
    
    # Generate ID
    template_id = f"tpl_{uuid.uuid4().hex[:12]}"
    
    # Create template
    db_template = Template(
        id=template_id,
        name=template_data.name,
        description=template_data.description,
        template_content=template_data.template_content,
        metadata_json=template_data.metadata
    )
    
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    
    return TemplateResponse(
        id=db_template.id,
        name=db_template.name,
        description=db_template.description,
        template_content=db_template.template_content,
        metadata_json=db_template.metadata_json,
        created_at=db_template.created_at,
        updated_at=db_template.updated_at
    )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    db: Session = Depends(get_db)
):
    """Get template by ID"""
    template = db.query(Template).filter(Template.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        template_content=template.template_content,
        metadata_json=template.metadata_json,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    template_data: TemplateUpdate,
    db: Session = Depends(get_db)
):
    """Update template"""
    template = db.query(Template).filter(Template.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Update fields
    if template_data.name is not None:
        template.name = template_data.name
    if template_data.description is not None:
        template.description = template_data.description
    if template_data.template_content is not None:
        # Validate template syntax
        is_valid, error_msg = template_renderer.validate_template(template_data.template_content)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid template syntax: {error_msg}")
        template.template_content = template_data.template_content
    if template_data.metadata is not None:
        template.metadata_json = template_data.metadata
    
    db.commit()
    db.refresh(template)
    
    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        template_content=template.template_content,
        metadata_json=template.metadata_json,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: str,
    db: Session = Depends(get_db)
):
    """Delete template"""
    template = db.query(Template).filter(Template.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()
    
    return None


@router.post("/{template_id}/validate", response_model=TemplateValidationResponse)
async def validate_template(
    template_id: str,
    db: Session = Depends(get_db)
):
    """
    Validate template and metadata
    
    Performs comprehensive validation including:
    - Jinja2 syntax check
    - Variable reference validation
    - Metadata structure validation
    - Dependency graph validation (cycle detection)
    - Schema format validation for AI variables
    
    Returns validation result with list of issues (errors and warnings).
    Template is considered valid if there are no errors (warnings are acceptable).
    """
    from app.services.template_validator import template_validator
    
    # Get template
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Parse metadata
    try:
        if isinstance(template.metadata_json, str):
            metadata = yaml.safe_load(template.metadata_json)
        elif isinstance(template.metadata_json, dict):
            metadata = template.metadata_json
        else:
            return TemplateValidationResponse(
                valid=False,
                issues=[{
                    "level": "error",
                    "category": "metadata",
                    "message": "Invalid metadata format: must be a dictionary",
                    "location": None
                }]
            )
    except Exception as e:
        return TemplateValidationResponse(
            valid=False,
            issues=[{
                "level": "error",
                "category": "metadata",
                "message": f"Failed to parse metadata: {str(e)}",
                "location": None
            }]
        )
    
    # Perform validation
    result = template_validator.validate_template(
        template.template_content,
        metadata
    )
    
    return TemplateValidationResponse(
        valid=result["valid"],
        issues=result["issues"]
    )

