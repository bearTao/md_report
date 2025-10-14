"""Report generation and management API"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import uuid
import asyncio
from datetime import datetime

from app.database import get_db
from app.models.db_models import (
    Template, GenerationTask, Report, ReportStatus,
    GenerationTaskVariable, VariableSourceType, VariableStatusType
)
from app.schemas.api_schemas import (
    ReportGenerateRequest, ReportGenerateResponse,
    ReportResponse, ReportStatusEnum
)
from app.services.scheduler import ExecutionScheduler
from app.services.context import ExecutionContext
from app.services.renderer import template_renderer
from app.core.models import VariableMetadata, VariableStatus


router = APIRouter(prefix="/api/reports", tags=["reports"])


def get_ai_api_key(db: Session) -> Optional[str]:
    """Get OpenAI API key from config (simplified for P0)"""
    from app.models.db_models import AIProviderKey
    from cryptography.fernet import Fernet
    import os
    
    # For P0, try environment variable first
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key
    
    # Try database
    config = db.query(AIProviderKey).filter(
        AIProviderKey.provider == "openai"
    ).first()
    
    if config:
        # Decrypt API key (simplified - in production use proper KMS)
        try:
            # For P0, assume plaintext storage in dev
            return config.api_key_ciphertext
        except:
            return None
    
    return None


async def execute_report_generation(
    task_id: str,
    template_id: str,
    template_content: str,
    metadata: Dict[str, Any],
    user_inputs: Dict[str, Any],
    db_session: Session,
    openai_api_key: Optional[str] = None
):
    """Background task to execute report generation"""
    
    # Update task status to running
    task = db_session.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    if task:
        task.status = ReportStatus.RUNNING
        task.started_at = datetime.utcnow()
        db_session.commit()
    
    try:
        # Parse metadata to VariableMetadata objects
        parsed_metadata = {}
        for var_name, var_config in metadata.items():
            parsed_metadata[var_name] = VariableMetadata(**var_config)
        
        # Create execution context
        context = ExecutionContext(
            task_id=task_id,
            template_id=template_id,
            user_inputs=user_inputs,
            metadata=parsed_metadata
        )
        
        # Create scheduler
        scheduler = ExecutionScheduler(openai_api_key=openai_api_key)
        
        # Progress callback to save variable execution details
        async def progress_callback(var_name: str, status: VariableStatus, result):
            # Save variable execution record
            var_meta = parsed_metadata[var_name]
            
            if status == VariableStatus.RUNNING:
                var_record = GenerationTaskVariable(
                    task_id=task_id,
                    variable_name=var_name,
                    source=VariableSourceType(var_meta.source.value),
                    status=VariableStatusType.RUNNING,
                    started_at=datetime.utcnow()
                )
                db_session.add(var_record)
                db_session.commit()
            elif status in (VariableStatus.SUCCESS, VariableStatus.FAILED):
                # Update existing record
                var_record = db_session.query(GenerationTaskVariable).filter(
                    GenerationTaskVariable.task_id == task_id,
                    GenerationTaskVariable.variable_name == var_name
                ).first()
                
                if var_record:
                    var_record.status = VariableStatusType(status.value)
                    var_record.finished_at = datetime.utcnow()
                    if result:
                        var_record.duration_ms = result.duration_ms
                        if result.error:
                            var_record.error_message = result.error
                        # Store preview of result (limit size)
                        if result.value is not None:
                            import json
                            preview = json.dumps(result.value, ensure_ascii=False)[:500]
                            var_record.result_preview = {"preview": preview}
                    db_session.commit()
        
        # Execute all variables
        results = await scheduler.execute_all(context, progress_callback)
        
        # Render template
        all_variables = context.get_all_variables()
        markdown_content = template_renderer.render(template_content, all_variables)
        
        # Extract title from user inputs or use first line of markdown
        title = user_inputs.get("report_title") or user_inputs.get("title")
        if not title and markdown_content:
            first_line = markdown_content.split('\n')[0]
            title = first_line.strip('# ').strip()[:200]
        
        # Calculate duration
        task = db_session.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        duration_ms = None
        if task and task.started_at:
            duration_ms = int((datetime.utcnow() - task.started_at).total_seconds() * 1000)
        
        # Create report
        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        report = Report(
            id=report_id,
            template_id=template_id,
            task_id=task_id,
            title=title,
            status=ReportStatus.SUCCESS,
            markdown_content=markdown_content,
            duration_ms=duration_ms
        )
        db_session.add(report)
        
        # Update task status
        if task:
            task.status = ReportStatus.SUCCESS
            task.finished_at = datetime.utcnow()
        
        db_session.commit()
        
    except Exception as e:
        # Mark task as failed
        task = db_session.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if task:
            task.status = ReportStatus.FAILED
            task.finished_at = datetime.utcnow()
            db_session.commit()
        
        # Log error
        print(f"Report generation failed for task {task_id}: {str(e)}")
        import traceback
        traceback.print_exc()


@router.post("/generate", response_model=ReportGenerateResponse, status_code=202)
async def generate_report(
    request: ReportGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Start report generation task"""
    # Get template
    template = db.query(Template).filter(Template.id == request.template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Create task
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    task = GenerationTask(
        id=task_id,
        template_id=request.template_id,
        status=ReportStatus.PENDING,
        inputs_json=request.inputs
    )
    db.add(task)
    db.commit()
    
    # Get AI API key
    openai_api_key = get_ai_api_key(db)
    
    # Start background task
    background_tasks.add_task(
        execute_report_generation,
        task_id=task_id,
        template_id=request.template_id,
        template_content=template.template_content,
        metadata=template.metadata_json,
        user_inputs=request.inputs,
        db_session=db,
        openai_api_key=openai_api_key
    )
    
    return ReportGenerateResponse(
        task_id=task_id,
        status=ReportStatusEnum.PENDING
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    """Get report by ID"""
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return ReportResponse(
        id=report.id,
        template_id=report.template_id,
        task_id=report.task_id,
        title=report.title,
        status=ReportStatusEnum(report.status.value),
        markdown_content=report.markdown_content,
        cost_usd=float(report.cost_usd) if report.cost_usd else None,
        duration_ms=report.duration_ms,
        created_at=report.created_at,
        updated_at=report.updated_at
    )


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    """Download report as .md file"""
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Generate filename
    filename = f"{report.title or report.id}.md"
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))
    
    return Response(
        content=report.markdown_content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

