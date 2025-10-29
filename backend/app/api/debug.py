"""Template debugging API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import uuid
import asyncio
import yaml

from app.database import get_db
from app.schemas.api_schemas import (
    DebugRenderRequest, DebugRenderResponse, DebugVariableResult
)
from app.services.context import ExecutionContext
from app.services.scheduler import ExecutionScheduler
from app.services.renderer import template_renderer
from app.core.models import VariableMetadata, VariableStatus
from app.core.exceptions import TemplateRenderError

router = APIRouter(prefix="/api/debug", tags=["debug"])


def get_ai_config(db: Session) -> tuple[str | None, str | None]:
    """Get OpenAI API config from environment or database"""
    from app.models.db_models import AIProviderKey
    import os
    
    # Try environment variable first
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    if api_key:
        return api_key, api_base
    
    # Try database
    config = db.query(AIProviderKey).filter(
        AIProviderKey.provider == "openai"
    ).first()
    
    if config:
        try:
            return config.api_key_ciphertext, config.api_base
        except:
            return None, None
    
    return None, None


@router.post("/render", response_model=DebugRenderResponse)
async def debug_render(
    request: DebugRenderRequest,
    db: Session = Depends(get_db)
):
    """
    Debug template rendering with real variable execution
    
    This endpoint executes all variables (SQL/API/AI) with actual calls
    and renders the template to show the real output.
    """
    try:
        # Parse metadata YAML
        try:
            metadata_dict = yaml.safe_load(request.metadata_yaml)
            if not isinstance(metadata_dict, dict):
                raise ValueError("Metadata must be a YAML object/dictionary")
        except yaml.YAMLError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid YAML format: {str(e)}"
            )
        
        # Convert to VariableMetadata objects
        metadata = {}
        for var_name, var_config in metadata_dict.items():
            try:
                metadata[var_name] = VariableMetadata(**var_config)
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid metadata for variable '{var_name}': {str(e)}"
                )
        
        # Create temporary task ID
        task_id = f"debug_{uuid.uuid4().hex[:12]}"
        
        # Create execution context
        context = ExecutionContext(
            task_id=task_id,
            template_id="debug",
            user_inputs=request.user_inputs,
            metadata=metadata
        )
        
        # Get AI config
        openai_api_key, openai_api_base = get_ai_config(db)
        
        # Create scheduler and execute all variables
        scheduler = ExecutionScheduler(
            openai_api_key=openai_api_key,
            openai_api_base=openai_api_base
        )
        
        results = await scheduler.execute_all(context)
        
        # Convert results to DebugVariableResult
        variable_results: List[DebugVariableResult] = []
        for var_name, result in results.items():
            variable_results.append(DebugVariableResult(
                variable_name=var_name,
                status=result.status.value,
                value=result.value,
                duration_ms=result.duration_ms,
                error_message=result.error
            ))
        
        # Resolve includes (if any)
        try:
            resolved_template = await template_renderer._resolve_includes(
                request.template_content,
                db,
                request.user_inputs,
                openai_api_key,
                openai_api_base
            )
        except Exception as e:
            # If include resolution fails, fall back to original template
            resolved_template = request.template_content
        
        # Render template with all variables
        try:
            all_variables = context.get_all_variables()
            rendered_markdown = template_renderer.render(resolved_template, all_variables)
            
            return DebugRenderResponse(
                success=True,
                rendered_markdown=rendered_markdown,
                variables=variable_results,
                error=None
            )
        except TemplateRenderError as e:
            return DebugRenderResponse(
                success=False,
                rendered_markdown=None,
                variables=variable_results,
                error=f"Template rendering failed: {str(e)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        return DebugRenderResponse(
            success=False,
            rendered_markdown=None,
            variables=[],
            error=f"Unexpected error: {str(e)}"
        )

