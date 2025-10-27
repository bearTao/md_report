"""Report generation and management API"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import uuid
import asyncio
from datetime import datetime

from app.database import get_db
from app.models.db_models import (
    Template, GenerationTask, Report, ReportStatus,
    GenerationTaskVariable, VariableSourceType, VariableStatusType,
    ExecutionLog, LogLevel
)
from app.schemas.api_schemas import (
    ReportGenerateRequest, ReportGenerateResponse,
    ReportResponse, ReportStatusEnum,
    TaskStatusResponse, TaskVariableDetail, VariableStatusEnum,
    ReportListResponse, ReportListItem,
    TaskCancelRequest, TaskCancelResponse, VariableRetryResponse,
    ExecutionLogItem, ExecutionLogListResponse
)
from app.services.scheduler import ExecutionScheduler
from app.services.context import ExecutionContext
from app.services.renderer import template_renderer
from app.core.models import VariableMetadata, VariableStatus
from app.services.websocket_manager import ws_manager
from app.core.exceptions import (
    TemplateRenderError, SqlExecutionError, AiGenerationError,
    VariableExecutionError, DependencyError, ValidationError
)


router = APIRouter(prefix="/api/reports", tags=["reports"])


def get_ai_config(db: Session) -> tuple[Optional[str], Optional[str]]:
    """
    Get OpenAI API config from environment or database
    
    Returns:
        tuple: (api_key, api_base)
    """
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
        # For P0, assume plaintext storage in dev
        try:
            return config.api_key_ciphertext, config.api_base
        except:
            return None, None
    
    return None, None


def _format_error_details(e: Exception) -> Dict[str, Any]:
    """
    Format exception details for frontend display
    
    Returns a dictionary with:
    - code: Error type code
    - message: User-friendly error message
    - details: Detailed technical information
    - suggestion: Optional suggestion for fixing the error
    """
    import traceback
    import re
    
    error_info = {
        "code": "UNKNOWN_ERROR",
        "message": str(e),
        "details": {},
        "suggestion": None
    }
    
    # Get traceback for detailed information
    tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
    tb_str = ''.join(tb_lines)
    
    # Detect error type and format accordingly
    if isinstance(e, TemplateRenderError):
        error_info["code"] = "TEMPLATE_RENDER_ERROR"
        error_info["message"] = "模板渲染失败"
        
        # Try to extract line number from Jinja2 error
        line_match = re.search(r'line (\d+)', str(e))
        if line_match:
            line_number = line_match.group(1)
            error_info["details"]["line"] = int(line_number)
            error_info["message"] = f"模板渲染失败（第{line_number}行）"
        
        # Extract specific error type
        error_str = str(e)
        if "'NoneType' object" in error_str or "has no attribute" in error_str:
            error_info["details"]["type"] = "null_value_error"
            error_info["details"]["description"] = "尝试访问空值(None)的属性或进行运算"
            error_info["suggestion"] = "检查变量是否为空，使用 'or' 提供默认值，如：{{ value or 0 }}"
            
            # Try to extract field name
            attr_match = re.search(r"has no attribute '(\w+)'", error_str)
            if attr_match:
                field_name = attr_match.group(1)
                error_info["details"]["field"] = field_name
                error_info["suggestion"] = f"字段 '{field_name}' 不存在或为空。使用 .get('{field_name}', default_value) 安全访问"
        
        elif "unsupported operand type" in error_str:
            error_info["details"]["type"] = "type_error"
            error_info["details"]["description"] = "类型不匹配，通常是None参与了数值运算"
            error_info["suggestion"] = "确保所有数值运算的变量都有默认值，如：{% set sum = (a or 0) + (b or 0) %}"
        
        elif "division by zero" in error_str or "ZeroDivisionError" in error_str:
            error_info["details"]["type"] = "division_by_zero"
            error_info["details"]["description"] = "除数为0"
            error_info["suggestion"] = "添加除数检查：{% set ratio = (a / b) if b != 0 else 0 %}"
        
        elif "not subscriptable" in error_str:
            error_info["details"]["type"] = "subscript_error"
            error_info["details"]["description"] = "尝试对不支持索引的对象使用[]或[:n]"
            error_info["suggestion"] = "检查变量类型，字符串切片前确认是字符串，如：{{ date[:10] if date else '-' }}"
        
        elif "'dict object' has no attribute" in error_str:
            error_info["details"]["type"] = "dict_access_error"
            error_info["details"]["description"] = "尝试用点号访问字典的键，但该键可能是保留字"
            error_info["suggestion"] = "使用 .get() 方法或方括号访问字典：{{ dict.get('key', default) }} 或 {{ dict['key'] }}"
        
        elif "must be real number" in error_str or "TypeError" in tb_str and "format" in tb_str:
            error_info["details"]["type"] = "format_type_error"
            error_info["details"]["description"] = "格式化时类型不匹配，期望数字但得到字符串"
            error_info["suggestion"] = "在格式化前先转换类型：{{ '%.2f'|format(value|float) }} 或 {{ '%.2f'|format(value|int) }}"
            
            # Try to extract the problematic value
            type_match = re.search(r'must be real number, not (\w+)', error_str)
            if type_match:
                wrong_type = type_match.group(1)
                error_info["details"]["wrong_type"] = wrong_type
                error_info["message"] = f"模板渲染失败：格式化错误（得到{wrong_type}类型，期望数字）"
        
        else:
            error_info["details"]["type"] = "syntax_error"
            error_info["details"]["description"] = str(e)
        
        # Include the specific error message
        error_info["details"]["error"] = str(e).split(":")[-1].strip()
    
    elif isinstance(e, SqlExecutionError):
        error_info["code"] = "SQL_EXECUTION_ERROR"
        error_info["message"] = f"SQL查询执行失败: 变量 '{e.variable_name}'"
        error_info["details"]["variable"] = e.variable_name
        error_info["details"]["error"] = e.message
        
        error_str = str(e).lower()
        if "table" in error_str and "doesn't exist" in error_str:
            error_info["suggestion"] = "检查数据库连接和表名是否正确"
        elif "syntax error" in error_str:
            error_info["suggestion"] = "检查SQL语法，确保跨数据库兼容"
        elif "timeout" in error_str:
            error_info["suggestion"] = "查询超时，尝试优化SQL或增加timeout设置"
        elif "permission denied" in error_str or "access denied" in error_str:
            error_info["suggestion"] = "检查数据库连接权限"
        else:
            error_info["suggestion"] = "检查SQL查询语句和参数是否正确"
    
    elif isinstance(e, AiGenerationError):
        error_info["code"] = "AI_GENERATION_ERROR"
        error_info["message"] = f"AI生成失败: 变量 '{e.variable_name}'"
        error_info["details"]["variable"] = e.variable_name
        error_info["details"]["error"] = e.message
        
        error_str = str(e).lower()
        if "api key" in error_str or "authentication" in error_str:
            error_info["suggestion"] = "检查AI API密钥配置"
        elif "rate limit" in error_str:
            error_info["suggestion"] = "API调用频率超限，稍后重试"
        elif "timeout" in error_str:
            error_info["suggestion"] = "AI生成超时，尝试简化提示词或增加超时时间"
        else:
            error_info["suggestion"] = "检查AI配置和提示词"
    
    elif isinstance(e, VariableExecutionError):
        error_info["code"] = "VARIABLE_EXECUTION_ERROR"
        error_info["message"] = f"变量执行失败: '{e.variable_name}'"
        error_info["details"]["variable"] = e.variable_name
        error_info["details"]["error"] = e.message
        error_info["suggestion"] = "检查变量配置和依赖关系"
    
    elif isinstance(e, DependencyError):
        error_info["code"] = "DEPENDENCY_ERROR"
        error_info["message"] = "变量依赖关系错误"
        error_info["details"]["error"] = str(e)
        error_info["suggestion"] = "检查变量的dependencies配置，确保所有依赖变量都存在"
    
    elif isinstance(e, ValidationError):
        error_info["code"] = "VALIDATION_ERROR"
        error_info["message"] = "输入验证失败"
        error_info["details"]["error"] = str(e)
        error_info["suggestion"] = "检查用户输入是否符合要求"
    
    else:
        # Generic error
        error_info["code"] = "EXECUTION_ERROR"
        error_info["message"] = f"执行失败: {str(e)}"
        error_info["details"]["error"] = str(e)
        error_info["details"]["type"] = type(e).__name__
    
    # Add truncated traceback (last 10 lines for context)
    tb_lines_list = tb_str.strip().split('\n')
    error_info["details"]["traceback"] = tb_lines_list[-10:]  # Last 10 lines
    
    return error_info


async def execute_report_generation(
    task_id: str,
    template_id: str,
    template_content: str,
    metadata: Dict[str, Any],
    user_inputs: Dict[str, Any],
    openai_api_key: Optional[str] = None,
    openai_api_base: Optional[str] = None
):
    """Background task to execute report generation"""
    
    # Create new database session for background task
    from app.database import SessionLocal
    db_session = SessionLocal()
    
    try:
        # Update task status to running
        task = db_session.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if task:
            task.status = ReportStatus.RUNNING
            task.started_at = datetime.utcnow()
            
            # Update report status to RUNNING
            report = db_session.query(Report).filter(Report.task_id == task_id).first()
            if report:
                report.status = ReportStatus.RUNNING
            
            db_session.commit()
            
            # Broadcast task started event
            await ws_manager.broadcast_task_started(
                task_id=task_id,
                template_id=template_id,
                queued_at=task.created_at,
                started_at=task.started_at
            )
        # Load database connections from database
        from app.models.db_models import DBConnection
        from app.connectors.database import db_connector
        
        db_connections = db_session.query(DBConnection).filter(
            DBConnection.is_active == "true"
        ).all()
        
        for db_conn in db_connections:
            try:
                # Build connection URL
                engine_dialects = {
                    "postgresql": "postgresql+psycopg2",
                    "mysql": "mysql+pymysql",
                    "sqlserver": "mssql+pyodbc",
                    "oracle": "oracle+cx_oracle"
                }
                
                dialect = engine_dialects.get(db_conn.engine.value, db_conn.engine.value)
                from urllib.parse import quote_plus
                password = db_conn.password_ciphertext  # TODO: Decrypt if encrypted
                
                connection_url = f"{dialect}://{db_conn.username}:{quote_plus(password)}@{db_conn.host}:{db_conn.port}/{db_conn.database}"
                
                # Register connection
                db_connector.register_connection(
                    name=db_conn.name,
                    connection_url_or_engine=connection_url,
                    pool_size=5,
                    max_overflow=10
                )
                
                print(f"Registered database connection: {db_conn.name}")
                
            except Exception as e:
                print(f"Failed to register connection {db_conn.name}: {str(e)}")
        
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
        scheduler = ExecutionScheduler(
            openai_api_key=openai_api_key,
            openai_api_base=openai_api_base
        )
        
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
                
                # Broadcast variable started event
                await ws_manager.broadcast_variable_started(
                    task_id=task_id,
                    variable_name=var_name,
                    source=var_meta.source.value,
                    dependencies=var_meta.dependencies or [],
                    started_at=var_record.started_at
                )
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
                        # Store complete result value for context reuse (e.g., in retry scenarios)
                        # JSON field can store dict, list, str, int, float, bool, None
                        if result.value is not None:
                            var_record.result_preview = result.value
                    db_session.commit()
                    
                    # Broadcast variable completed or failed event
                    if status == VariableStatus.SUCCESS:
                        await ws_manager.broadcast_variable_completed(
                            task_id=task_id,
                            variable_name=var_name,
                            duration_ms=var_record.duration_ms or 0,
                            result_preview=var_record.result_preview
                        )
                    else:  # FAILED
                        await ws_manager.broadcast_variable_failed(
                            task_id=task_id,
                            variable_name=var_name,
                            error={"code": "EXECUTION_ERROR", "message": result.error if result else "Unknown error"},
                            duration_ms=var_record.duration_ms or 0
                        )
        
        # Execute all variables
        results = await scheduler.execute_all(context, progress_callback)
        
        # Render template
        try:
            all_variables = context.get_all_variables()
            markdown_content = template_renderer.render(template_content, all_variables)
        except TemplateRenderError as e:
            # 渲染错误 - 保存到任务记录并广播
            print(f"Template rendering failed for task {task_id}: {str(e)}")
            
            # 保存渲染错误到数据库
            task = db_session.query(GenerationTask).filter(GenerationTask.id == task_id).first()
            if task:
                task.render_error = {
                    "error_type": "TemplateRenderError",
                    "error_message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                task.status = ReportStatus.FAILED
                task.finished_at = datetime.utcnow()
                db_session.commit()
            
            # 广播渲染错误事件
            await ws_manager.broadcast_render_failed(
                task_id=task_id,
                error={
                    "code": "TEMPLATE_RENDER_ERROR",
                    "message": str(e),
                    "details": "模板渲染失败，请检查模板语法"
                }
            )
            
            db_session.close()
            return  # 提前返回
        
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
        
        # Update existing report with success status and content
        report = db_session.query(Report).filter(Report.task_id == task_id).first()
        if not report:
            # Fallback: create report if it doesn't exist (shouldn't happen normally)
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
        else:
            # Update existing report
            report_id = report.id
            report.title = title
            report.status = ReportStatus.SUCCESS
            report.markdown_content = markdown_content
            report.duration_ms = duration_ms
        
        # Update task status
        if task:
            task.status = ReportStatus.SUCCESS
            task.finished_at = datetime.utcnow()
        
        db_session.commit()
        
        # Broadcast task completed event
        await ws_manager.broadcast_task_completed(
            task_id=task_id,
            report_id=report_id,
            summary={
                "duration_ms": duration_ms,
                "ai_cost_usd": 0  # TODO: Calculate actual AI cost
            }
        )
        
    except Exception as e:
        # Log error first
        print(f"Report generation failed for task {task_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        
        try:
            # Rollback failed transaction
            db_session.rollback()
            
            # Mark task as failed
            task = db_session.query(GenerationTask).filter(GenerationTask.id == task_id).first()
            duration_ms = None
            if task:
                task.status = ReportStatus.FAILED
                task.finished_at = datetime.utcnow()
                if task.started_at:
                    duration_ms = int((task.finished_at - task.started_at).total_seconds() * 1000)
            
            # Update report status to FAILED
            report = db_session.query(Report).filter(Report.task_id == task_id).first()
            if report:
                report.status = ReportStatus.FAILED
                report.duration_ms = duration_ms
            
            db_session.commit()
            
            # Format detailed error information
            error_info = _format_error_details(e)
            
            # Broadcast task failed event
            await ws_manager.broadcast_task_failed(
                task_id=task_id,
                error=error_info,
                summary={"duration_ms": duration_ms or 0}
            )
        except Exception as commit_error:
            print(f"Failed to update task status: {commit_error}")
            traceback.print_exc()
    
    finally:
        # Always close the session
        db_session.close()
        print(f"Database session closed for task {task_id}")


@router.post("/generate", response_model=ReportGenerateResponse, status_code=202)
async def generate_report(
    request: ReportGenerateRequest,
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
    
    # Create report record immediately with PENDING status
    report_id = f"rpt_{uuid.uuid4().hex[:12]}"
    report = Report(
        id=report_id,
        template_id=request.template_id,
        task_id=task_id,
        title=f"Report - {template.name}",
        status=ReportStatus.PENDING,
        markdown_content=""  # Empty string for pending reports
    )
    db.add(report)
    db.commit()
    
    # Get AI config (api_key and api_base)
    openai_api_key, openai_api_base = get_ai_config(db)
    
    # Start background task using asyncio.create_task for proper async execution
    task = asyncio.create_task(
        execute_report_generation(
            task_id=task_id,
            template_id=request.template_id,
            template_content=template.template_content,
            metadata=template.metadata_json,
            user_inputs=request.inputs,
            openai_api_key=openai_api_key,
            openai_api_base=openai_api_base
        )
    )
    
    # Add exception handler to catch any uncaught exceptions in the background task
    def handle_task_exception(future: asyncio.Future):
        try:
            future.result()
        except Exception as e:
            print(f"UNCAUGHT EXCEPTION in background task {task_id}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    task.add_done_callback(handle_task_exception)
    
    return ReportGenerateResponse(
        task_id=task_id,
        status=ReportStatusEnum.PENDING
    )


@router.get("/", response_model=ReportListResponse)
async def list_reports(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    template_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get report history list with filters"""
    # Build query
    query = db.query(Report)
    
    # Apply filters
    if status:
        try:
            status_enum = ReportStatus(status)
            query = query.filter(Report.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    if template_id:
        query = query.filter(Report.template_id == template_id)
    
    # Order by created_at desc (newest first)
    query = query.order_by(Report.created_at.desc())
    
    # Count total
    total = query.count()
    
    # Pagination
    offset = (page - 1) * page_size
    reports = query.offset(offset).limit(page_size).all()
    
    items = []
    for r in reports:
        # Convert created_at to datetime if it's a string
        created_at = r.created_at
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = datetime.utcnow()
        
        items.append(ReportListItem(
            id=r.id,
            template_id=r.template_id,
            task_id=r.task_id,  # 添加task_id用于跳转到生成进度页面
            title=r.title,
            status=ReportStatusEnum(r.status.value),
            created_at=created_at
        ))
    
    return ReportListResponse(items=items, total=total)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    """Get report by ID"""
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Convert datetime fields if they're strings
    created_at = report.created_at
    updated_at = report.updated_at
    
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            created_at = datetime.utcnow()
    
    if isinstance(updated_at, str):
        try:
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            updated_at = datetime.utcnow()
    
    return ReportResponse(
        id=report.id,
        template_id=report.template_id,
        task_id=report.task_id,
        title=report.title,
        status=ReportStatusEnum(report.status.value),
        markdown_content=report.markdown_content,
        cost_usd=float(report.cost_usd) if report.cost_usd else None,
        duration_ms=report.duration_ms,
        created_at=created_at,
        updated_at=updated_at
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
    
    # Generate filename - use URL encoding for unicode characters
    from urllib.parse import quote
    filename = f"{report.title or report.id}.md"
    # Keep only safe characters
    safe_filename = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in filename)
    if not safe_filename.endswith('.md'):
        safe_filename += '.md'
    
    # Use UTF-8 encoding for the filename
    encoded_filename = quote(safe_filename)
    
    return Response(
        content=report.markdown_content.encode('utf-8'),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )


@router.get("/{report_id}/convert/word")
async def convert_report_to_word(
    report_id: str,
    db: Session = Depends(get_db)
):
    """Convert report to Word document (.docx)"""
    from app.utils.document_converter import (
        DocumentConverter, 
        PandocNotFoundError, 
        DocumentConversionError
    )
    from urllib.parse import quote
    
    # Get report from database
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Only allow conversion for successful reports
    if report.status != ReportStatus.SUCCESS:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot convert report with status '{report.status.value}'. Only successful reports can be converted."
        )
    
    # Check if report has content
    if not report.markdown_content or report.markdown_content.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="Report has no content to convert"
        )
    
    try:
        # Convert markdown to docx
        docx_bytes = DocumentConverter.markdown_to_docx(
            markdown_content=report.markdown_content,
            output_filename=report.title or report.id
        )
        
        # Generate filename
        filename = f"{report.title or report.id}.docx"
        safe_filename = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in filename)
        if not safe_filename.endswith('.docx'):
            safe_filename += '.docx'
        
        # Encode filename for headers
        encoded_filename = quote(safe_filename)
        
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
        
    except PandocNotFoundError as e:
        raise HTTPException(
            status_code=500,
            detail="Pandoc is not installed on the server. Please contact the administrator."
        )
    
    except DocumentConversionError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to convert document: {str(e)}"
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during conversion: {str(e)}"
        )


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Get task execution status and variable details"""
    task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get all variable execution records
    variables = db.query(GenerationTaskVariable).filter(
        GenerationTaskVariable.task_id == task_id
    ).all()
    
    # Get report if exists
    report = db.query(Report).filter(Report.task_id == task_id).first()
    
    variable_details = [
        TaskVariableDetail(
            variable_name=var.variable_name,
            source=var.source.value,
            status=VariableStatusEnum(var.status.value),
            started_at=var.started_at,
            finished_at=var.finished_at,
            duration_ms=var.duration_ms,
            error_message=var.error_message,
            result_preview=var.result_preview
        )
        for var in variables
    ]
    
    return TaskStatusResponse(
        task_id=task.id,
        template_id=task.template_id,
        status=ReportStatusEnum(task.status.value),
        inputs_json=task.inputs_json,
        started_at=task.started_at,
        finished_at=task.finished_at,
        created_at=task.created_at,
        report_id=report.id if report else None,
        variables=variable_details
    )


@router.post("/tasks/{task_id}/cancel", response_model=TaskCancelResponse)
async def cancel_task(
    task_id: str,
    request: Optional[TaskCancelRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Cancel a running task
    
    Cancels a pending or running task. The task status will be updated to 'cancelled'
    and all running variables will be stopped.
    """
    # Get task
    task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if task can be cancelled
    if task.status not in [ReportStatus.PENDING, ReportStatus.RUNNING]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel task in status: {task.status.value}"
        )
    
    # Set cancellation flag in execution context
    ExecutionContext.set_cancellation_flag(task_id)
    
    # Update task status
    task.status = ReportStatus.CANCELLED
    task.finished_at = datetime.utcnow()
    
    # Update report status to CANCELLED
    report = db.query(Report).filter(Report.task_id == task_id).first()
    if report:
        report.status = ReportStatus.CANCELLED
    
    # Update running variables to cancelled
    running_vars = db.query(GenerationTaskVariable).filter(
        GenerationTaskVariable.task_id == task_id,
        GenerationTaskVariable.status == VariableStatusType.RUNNING
    ).all()
    
    for var in running_vars:
        var.status = VariableStatusType.CANCELLED
        var.finished_at = datetime.utcnow()
        if var.started_at:
            var.duration_ms = int((var.finished_at - var.started_at).total_seconds() * 1000)
    
    db.commit()
    
    # Broadcast WebSocket event
    from app.services.websocket_manager import WSEventType
    await ws_manager.send_event(
        task_id,
        WSEventType.TASK_CANCELLED,
        {
            "reason": request.reason if request else None,
            "cancelled_at": task.finished_at.isoformat()
        }
    )
    
    return TaskCancelResponse(
        task_id=task_id,
        status="cancelled",
        cancelled_at=task.finished_at
    )


@router.post("/tasks/{task_id}/variables/{variable_name}/retry", response_model=VariableRetryResponse)
async def retry_variable(
    task_id: str,
    variable_name: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Retry a failed variable execution
    
    Retries execution of a single failed or cancelled variable.
    Other successfully executed variables will not be re-executed.
    """
    # Get task
    task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get variable
    var = db.query(GenerationTaskVariable).filter(
        GenerationTaskVariable.task_id == task_id,
        GenerationTaskVariable.variable_name == variable_name
    ).first()
    
    if not var:
        raise HTTPException(status_code=404, detail="Variable not found")
    
    # Check if variable can be retried
    # Allow retry for FAILED, CANCELLED, and stuck PENDING (no started_at or started > 5 min ago)
    can_retry = False
    
    if var.status in [VariableStatusType.FAILED, VariableStatusType.CANCELLED]:
        can_retry = True
    elif var.status == VariableStatusType.PENDING:
        # Allow retry if stuck in PENDING (task might be lost due to server restart)
        if var.started_at is None:
            can_retry = True
        else:
            # If started more than 5 minutes ago but still pending, consider it stuck
            time_since_start = (datetime.utcnow() - var.started_at).total_seconds()
            if time_since_start > 300:  # 5 minutes
                can_retry = True
    
    if not can_retry:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot retry variable in status: {var.status.value}. Variable is currently running or completed."
        )
    
    # Reset variable status
    var.status = VariableStatusType.PENDING
    var.started_at = None
    var.finished_at = None
    var.duration_ms = None
    var.error_code = None
    var.error_message = None
    var.result_preview = None
    db.commit()
    
    # Trigger retry in background using asyncio.create_task
    # This ensures the async function is properly executed
    asyncio.create_task(retry_variable_execution(task_id, variable_name))
    
    return VariableRetryResponse(
        task_id=task_id,
        variable_name=variable_name,
        retry_status="pending"
    )


async def retry_variable_execution(task_id: str, variable_name: str):
    """
    Retry execution of a single variable
    
    This function is called as a background task to retry variable execution.
    It reuses the results of successfully executed variables and only re-executes
    the specified variable.
    """
    from app.database import SessionLocal
    
    db_session = SessionLocal()
    
    try:
        # Get task and template
        task = db_session.query(GenerationTask).filter_by(id=task_id).first()
        if not task:
            print(f"Task {task_id} not found for retry")
            return
        
        template = db_session.query(Template).filter_by(id=task.template_id).first()
        if not template:
            print(f"Template {task.template_id} not found for retry")
            return
        
        # Parse metadata
        metadata_dict = template.metadata_json if isinstance(template.metadata_json, dict) else {}
        metadata = {
            name: VariableMetadata(**config) 
            for name, config in metadata_dict.items()
        }
        
        variable_meta = metadata.get(variable_name)
        if not variable_meta:
            print(f"Variable {variable_name} not found in metadata")
            return
        
        # Build context with existing successful variables
        context = ExecutionContext(
            task_id=task_id,
            template_id=task.template_id,
            user_inputs=task.inputs_json,
            metadata=metadata
        )
        
        # Load successful variables into context
        successful_vars = db_session.query(GenerationTaskVariable).filter(
            GenerationTaskVariable.task_id == task_id,
            GenerationTaskVariable.status == VariableStatusType.SUCCESS
        ).all()
        
        for var in successful_vars:
            if var.result_preview is not None:
                context.set_variable(var.variable_name, var.result_preview)
        
        # Get AI config
        openai_api_key, openai_api_base = get_ai_config(db_session)
        
        # Create executor
        scheduler = ExecutionScheduler(
            openai_api_key=openai_api_key,
            openai_api_base=openai_api_base
        )
        executor = scheduler.create_executor(variable_name, variable_meta, context)
        
        # Update variable status to running
        var_record = db_session.query(GenerationTaskVariable).filter_by(
            task_id=task_id,
            variable_name=variable_name
        ).first()
        
        var_record.status = VariableStatusType.RUNNING
        var_record.started_at = datetime.utcnow()
        db_session.commit()
        
        # Broadcast variable started
        await ws_manager.broadcast_variable_started(
            task_id=task_id,
            variable_name=variable_name,
            source=variable_meta.source.value,
            dependencies=variable_meta.dependencies or [],
            started_at=var_record.started_at
        )
        
        # Execute variable
        result = await executor.execute()
        
        # Update result
        var_record.status = VariableStatusType(result.status.value)
        var_record.finished_at = datetime.utcnow()
        var_record.duration_ms = result.duration_ms
        
        if result.status == VariableStatus.SUCCESS:
            # Store complete result value consistent with main execution flow
            # JSON field can store dict, list, str, int, float, bool, None
            var_record.result_preview = result.value
            db_session.commit()
            
            # Broadcast variable completed
            await ws_manager.broadcast_variable_completed(
                task_id=task_id,
                variable_name=variable_name,
                duration_ms=result.duration_ms
            )
            
            # Check if all variables are now successful
            all_vars = db_session.query(GenerationTaskVariable).filter_by(task_id=task_id).all()
            all_success = all(v.status == VariableStatusType.SUCCESS for v in all_vars)
            
            if all_success:
                # Continue with report generation
                print(f"All variables successful after retry, continuing with report generation for task {task_id}")
                # Re-trigger report generation
                await continue_report_generation(task_id, context, db_session)
        else:
            var_record.error_message = result.error
            db_session.commit()
            
            # Broadcast variable failed
            await ws_manager.broadcast_variable_failed(
                task_id=task_id,
                variable_name=variable_name,
                error_message=result.error
            )
    
    except Exception as e:
        print(f"Error during variable retry: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Update variable to failed
        try:
            var_record = db_session.query(GenerationTaskVariable).filter_by(
                task_id=task_id,
                variable_name=variable_name
            ).first()
            if var_record:
                var_record.status = VariableStatusType.FAILED
                var_record.error_message = str(e)
                var_record.finished_at = datetime.utcnow()
                db_session.commit()
                
                await ws_manager.broadcast_variable_failed(
                    task_id=task_id,
                    variable_name=variable_name,
                    error_message=str(e)
                )
        except Exception as commit_error:
            print(f"Failed to update variable status: {commit_error}")
    
    finally:
        db_session.close()


async def continue_report_generation(task_id: str, context: ExecutionContext, db_session: Session):
    """
    Continue report generation after successful variable retry
    
    This function continues the report generation process from where it left off
    after a variable retry succeeds.
    """
    try:
        # Get task and template
        task = db_session.query(GenerationTask).filter_by(id=task_id).first()
        template = db_session.query(Template).filter_by(id=task.template_id).first()
        
        # Reload ALL successful variables into context to ensure we have complete data
        # This is important because the context might have been created before the retry
        successful_vars = db_session.query(GenerationTaskVariable).filter(
            GenerationTaskVariable.task_id == task_id,
            GenerationTaskVariable.status == VariableStatusType.SUCCESS
        ).all()
        
        for var in successful_vars:
            if var.result_preview is not None:
                context.set_variable(var.variable_name, var.result_preview)
        
        # Render template
        markdown_content = template_renderer.render(
            template_content=template.template_content,
            variables=context.get_all_variables()
        )
        
        # Calculate duration
        duration_ms = None
        if task.started_at:
            duration_ms = int((datetime.utcnow() - task.started_at).total_seconds() * 1000)
        
        # Update existing report with success status and content
        report = db_session.query(Report).filter(Report.task_id == task_id).first()
        if not report:
            # Fallback: create report if it doesn't exist (shouldn't happen normally)
            report_id = f"report_{uuid.uuid4().hex[:12]}"
            report = Report(
                id=report_id,
                template_id=task.template_id,
                task_id=task_id,
                title=f"Report for {template.name}",
                status=ReportStatus.SUCCESS,
                markdown_content=markdown_content,
                cost_usd=0,
                duration_ms=duration_ms
            )
            db_session.add(report)
        else:
            # Update existing report
            report_id = report.id
            report.title = f"Report for {template.name}"
            report.status = ReportStatus.SUCCESS
            report.markdown_content = markdown_content
            report.duration_ms = duration_ms
        
        # Update task status
        task.status = ReportStatus.SUCCESS
        task.finished_at = datetime.utcnow()
        db_session.commit()
        
        # Broadcast completion
        await ws_manager.broadcast_task_completed(
            task_id=task_id,
            report_id=report_id,
            summary={
                "duration_ms": duration_ms,
                "ai_cost_usd": 0
            }
        )
    
    except Exception as e:
        print(f"Error continuing report generation: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Mark task as failed
        task.status = ReportStatus.FAILED
        task.finished_at = datetime.utcnow()
        
        # Update report status to FAILED
        report = db_session.query(Report).filter(Report.task_id == task_id).first()
        if report:
            report.status = ReportStatus.FAILED
        
        db_session.commit()
        
        await ws_manager.broadcast_task_failed(
            task_id=task_id,
            error={"message": str(e)},
            summary={}
        )


@router.get("/tasks/{task_id}/logs", response_model=ExecutionLogListResponse)
async def get_task_logs(
    task_id: str,
    level: Optional[str] = Query(None, description="Filter by log level (DEBUG, INFO, WARNING, ERROR)"),
    variable_name: Optional[str] = Query(None, description="Filter by variable name"),
    limit: int = Query(100, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    db: Session = Depends(get_db)
):
    """
    Get execution logs for a task
    
    Returns logs for the specified task, with optional filtering by level and variable name.
    Logs are ordered by creation time (oldest first).
    """
    # Build query
    query = db.query(ExecutionLog).filter(ExecutionLog.task_id == task_id)
    
    # Apply filters
    if level:
        level_upper = level.upper()
        if level_upper in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            query = query.filter(ExecutionLog.level == LogLevel[level_upper])
    
    if variable_name:
        query = query.filter(ExecutionLog.variable_name == variable_name)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    logs = query.order_by(ExecutionLog.created_at.asc())\
               .offset(offset)\
               .limit(limit)\
               .all()
    
    # Convert to response format
    log_items = [
        ExecutionLogItem(
            id=log.id,
            task_id=log.task_id,
            variable_name=log.variable_name,
            level=log.level.value,
            message=log.message,
            context=log.context_json,
            created_at=log.created_at
        )
        for log in logs
    ]
    
    return ExecutionLogListResponse(
        logs=log_items,
        total=total
    )

