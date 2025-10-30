"""Report generation and management API"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import uuid
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

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
    ReportUpdateRequest,
    TaskCancelRequest, TaskCancelResponse, VariableRetryResponse,
    ExecutionLogItem, ExecutionLogListResponse,
    DeleteReportResponse
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
        # Get template info for path construction
        from app.models.db_models import Template
        template = db_session.query(Template).filter_by(id=template_id).first()
        main_template_name = template.name if template else template_id
        main_template_path = main_template_name  # 主模板的路径就是它自己的名字
        

        # Detect if user_inputs is nested structure (for templates with includes)
        # Nested format: {"template_id": {"var": "value"}}
        # Flat format: {"var": "value"}
        nested_user_inputs = {}
        main_template_inputs = {}
        
        # Check if inputs contains template_id as keys (nested structure)
        if template_id in user_inputs and isinstance(user_inputs[template_id], dict):
            # Nested structure detected
            nested_user_inputs = user_inputs
            main_template_inputs = user_inputs.get(template_id, {})
        else:
            # Flat structure (backward compatibility)
            main_template_inputs = user_inputs
            nested_user_inputs = {template_id: user_inputs}
        
        # Update task status to running
        task = db_session.query(GenerationTask).filter(GenerationTask.id == task_id).first()
        if task:
            task.status = 'running'
            task.started_at = datetime.utcnow()
            
            # Update report status to RUNNING
            report = db_session.query(Report).filter(Report.task_id == task_id).first()
            if report:
                report.status = 'running'
            
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
                
                logger.info(f"Registered database connection: {db_conn.name}")
                
            except Exception as e:
                logger.error(f"Failed to register connection {db_conn.name}: {str(e)}")
        
        # Parse metadata to VariableMetadata objects
        parsed_metadata = {}
        for var_name, var_config in metadata.items():
            parsed_metadata[var_name] = VariableMetadata(**var_config)
        
        # Create execution context for main template
        context = ExecutionContext(
            task_id=task_id,
            template_id=template_id,
            user_inputs=main_template_inputs,  # Use main template's inputs only
            metadata=parsed_metadata
        )
        
        # 设置主模板的template信息
        context.template_id = template_id
        context.template_path = main_template_path
        
        # Create scheduler
        scheduler = ExecutionScheduler(
            openai_api_key=openai_api_key,
            openai_api_base=openai_api_base
        )
        
        # Progress callback to save variable execution details
        async def progress_callback(var_name: str, status: VariableStatus, result):
            # Save variable execution record
            var_meta = parsed_metadata[var_name]
            
            # 从context获取template信息（主模板或子模板）
            current_template_id = getattr(context, 'template_id', template_id)
            current_template_path = getattr(context, 'template_path', main_template_path)
            
            if status == VariableStatus.RUNNING:
                var_record = GenerationTaskVariable(
                    task_id=task_id,
                    variable_name=var_name,
                    source=var_meta.source.value,  # 直接使用字符串值
                    status='running',  # 直接使用字符串值
                    started_at=datetime.utcnow(),
                    template_id=current_template_id,
                    template_path=current_template_path
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
                # 注意：需要同时匹配 task_id, variable_name 和 template_id
                # 以支持不同模板中的同名变量
                var_record = db_session.query(GenerationTaskVariable).filter(
                    GenerationTaskVariable.task_id == task_id,
                    GenerationTaskVariable.variable_name == var_name,
                    GenerationTaskVariable.template_id == current_template_id
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
        
        # Resolve template includes before rendering
        try:
            resolved_template_content = await template_renderer._resolve_includes(
                template_content,
                db_session,
                nested_user_inputs,  # Pass full nested structure
                template_id,  # Current template ID
                task_id,  # 主任务ID
                main_template_path,  # 主模板路径
                openai_api_key,
                openai_api_base,
                None,  # visited set
                progress_callback  # 传递 progress_callback 以便记录子模板的变量执行
            )
        except Exception as e:
            logger.error(f"Failed to resolve template includes for task {task_id}: {str(e)}")
            # Fall back to original template if include resolution fails
            resolved_template_content = template_content
        
        # Render template
        try:
            # 广播渲染开始事件
            await ws_manager.broadcast_render_started(task_id)
            
            all_variables = context.get_all_variables()
            # 传入 task_id 和模板信息以便记录渲染日志到数据库
            markdown_content = template_renderer.render(
                resolved_template_content, 
                all_variables, 
                task_id=task_id,
                template_id=template_id,
                template_path=main_template_path
            )
            
            # 广播渲染完成事件
            await ws_manager.broadcast_render_completed(task_id, len(markdown_content))
        except TemplateRenderError as e:
            # 渲染错误 - 保存到任务记录并广播
            logger.error(f"Template rendering failed for task {task_id}: {str(e)}")
            
            # 保存渲染错误到数据库
            task = db_session.query(GenerationTask).filter(GenerationTask.id == task_id).first()
            if task:
                task.render_error = {
                    "error_type": "TemplateRenderError",
                    "error_message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                task.status = 'failed'
                task.finished_at = datetime.utcnow()
            
            # 同时更新报告状态
            report = db_session.query(Report).filter(Report.task_id == task_id).first()
            if report:
                report.status = 'failed'
            
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
                status='success',
                markdown_content=markdown_content,
                duration_ms=duration_ms
            )
            db_session.add(report)
        else:
            # Update existing report
            report_id = report.id
            report.title = title
            report.status = 'success'
            report.markdown_content = markdown_content
            report.duration_ms = duration_ms
        
        # Update task status
        if task:
            task.status = 'success'
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
        logger.error(f"Report generation failed for task {task_id}: {str(e)}", exc_info=True)
        
        try:
            # Rollback failed transaction
            db_session.rollback()
            
            # Mark task as failed
            task = db_session.query(GenerationTask).filter(GenerationTask.id == task_id).first()
            duration_ms = None
            if task:
                task.status = 'failed'
                task.finished_at = datetime.utcnow()
                if task.started_at:
                    duration_ms = int((task.finished_at - task.started_at).total_seconds() * 1000)
            
            # Update report status to FAILED
            report = db_session.query(Report).filter(Report.task_id == task_id).first()
            if report:
                report.status = 'failed'
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
            logger.error(f"Failed to update task status: {commit_error}", exc_info=True)
    
    finally:
        # Always close the session
        db_session.close()
        logger.debug(f"Database session closed for task {task_id}")


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
        status='pending',
        inputs_json=request.inputs
    )
    db.add(task)
    
    # Create report record immediately with PENDING status
    report_id = f"rpt_{uuid.uuid4().hex[:12]}"
    
    # 生成报告标题：使用用户提供的名称，或自动生成
    if request.report_name:
        report_title = request.report_name
    else:
        # 生成默认名称：模板名称 - YYYY-MM-DD HH:mm:ss
        from datetime import datetime
        report_title = f"{template.name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    report = Report(
        id=report_id,
        template_id=request.template_id,
        task_id=task_id,
        title=report_title,
        status='pending',
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
            logger.error(f"UNCAUGHT EXCEPTION in background task {task_id}: {str(e)}", exc_info=True)
    
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
        # 直接使用字符串过滤（status列现在是VARCHAR）
        query = query.filter(Report.status == status)
    
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
            status=ReportStatusEnum(r.status),  # 直接使用字符串值
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
        status=ReportStatusEnum(report.status),  # 直接使用字符串值
        markdown_content=report.markdown_content,
        cost_usd=float(report.cost_usd) if report.cost_usd else None,
        duration_ms=report.duration_ms,
        created_at=created_at,
        updated_at=updated_at
    )


@router.patch("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: str,
    request: ReportUpdateRequest,
    db: Session = Depends(get_db)
):
    """更新报告标题"""
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # 更新标题
    report.title = request.title
    report.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(report)
    
    # 返回更新后的报告信息
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
        status=ReportStatusEnum(report.status),
        markdown_content=report.markdown_content,
        cost_usd=float(report.cost_usd) if report.cost_usd else None,
        duration_ms=report.duration_ms,
        created_at=created_at,
        updated_at=updated_at
    )


@router.delete("/{report_id}", response_model=DeleteReportResponse)
async def delete_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    """
    删除报告及其关联的任务和变量记录
    
    删除顺序（避免外键约束）：
    1. 删除报告记录 (reports)
    2. 删除变量执行记录 (generation_task_variables)
    3. 删除执行日志 (execution_logs)
    4. 删除任务记录 (generation_tasks)
    
    Args:
        report_id: 报告ID
        db: 数据库会话
        
    Returns:
        DeleteReportResponse: 删除结果和统计信息
        
    Raises:
        HTTPException: 报告不存在时返回404
    """
    # 检查报告是否存在
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    task_id = report.task_id
    deleted_counts = {
        'reports': 0,
        'tasks': 0,
        'variables': 0,
        'logs': 0
    }
    
    try:
        # 1. 删除报告记录
        db.delete(report)
        deleted_counts['reports'] = 1
        
        # 2. 如果有关联的任务，删除相关记录
        if task_id:
            # 2a. 删除变量执行记录
            vars_deleted = db.query(GenerationTaskVariable).filter(
                GenerationTaskVariable.task_id == task_id
            ).delete()
            deleted_counts['variables'] = vars_deleted
            
            # 2b. 删除执行日志
            logs_deleted = db.query(ExecutionLog).filter(
                ExecutionLog.task_id == task_id
            ).delete()
            deleted_counts['logs'] = logs_deleted
            
            # 2c. 删除任务记录
            task = db.query(GenerationTask).filter(
                GenerationTask.id == task_id
            ).first()
            if task:
                db.delete(task)
                deleted_counts['tasks'] = 1
        
        # 提交所有删除操作
        db.commit()
        
        return DeleteReportResponse(
            success=True,
            message=f"成功删除报告 {report_id} 及其关联数据",
            deleted_items=deleted_counts
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"删除报告失败: {str(e)}"
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
    if report.status != 'success':
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot convert report with status '{report.status}'. Only successful reports can be converted."
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
    # 使用原生SQL查询避免枚举转换问题
    from sqlalchemy import text
    
    # 查询任务
    task_query = text("""
        SELECT id, template_id, status, inputs_json, started_at, finished_at, created_at
        FROM generation_tasks
        WHERE id = :task_id
    """)
    task_result = db.execute(task_query, {"task_id": task_id}).fetchone()
    
    if not task_result:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 查询变量
    vars_query = text("""
        SELECT variable_name, source, status, started_at, finished_at, 
               duration_ms, error_message, result_preview, template_id, template_path
        FROM generation_task_variables
        WHERE task_id = :task_id
        ORDER BY id
    """)
    vars_result = db.execute(vars_query, {"task_id": task_id}).fetchall()
    
    # 查询报告
    report_query = text("""
        SELECT id FROM reports WHERE task_id = :task_id
    """)
    report_result = db.execute(report_query, {"task_id": task_id}).fetchone()
    
    # 构建变量详情列表
    variable_details = [
        TaskVariableDetail(
            variable_name=var[0],
            source=var[1],  # 直接使用字符串值
            status=VariableStatusEnum(var[2]),  # status 值
            started_at=var[3],
            finished_at=var[4],
            duration_ms=var[5],
            error_message=var[6],
            result_preview=var[7],
            template_id=var[8],      # 添加 template_id
            template_path=var[9]     # 添加 template_path
        )
        for var in vars_result
    ]
    
    # 解析JSON字段
    import json
    inputs_json = task_result[3]
    if isinstance(inputs_json, str):
        inputs_json = json.loads(inputs_json)
    
    return TaskStatusResponse(
        task_id=task_result[0],
        template_id=task_result[1],
        status=ReportStatusEnum(task_result[2]),  # status 值
        inputs_json=inputs_json,
        started_at=task_result[4],
        finished_at=task_result[5],
        created_at=task_result[6],
        report_id=report_result[0] if report_result else None,
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
    if task.status not in ['pending', 'running']:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel task in status: {task.status}"
        )
    
    # Set cancellation flag in execution context
    ExecutionContext.set_cancellation_flag(task_id)
    
    # Update task status
    task.status = 'cancelled'
    task.finished_at = datetime.utcnow()
    
    # Update report status to CANCELLED
    report = db.query(Report).filter(Report.task_id == task_id).first()
    if report:
        report.status = 'cancelled'
    
    # Update running variables to cancelled
    running_vars = db.query(GenerationTaskVariable).filter(
        GenerationTaskVariable.task_id == task_id,
        GenerationTaskVariable.status == 'running'
    ).all()
    
    for var in running_vars:
        var.status = 'cancelled'
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
    # 注意：如果有多个模板有同名变量，需要检查是否有歧义
    vars = db.query(GenerationTaskVariable).filter(
        GenerationTaskVariable.task_id == task_id,
        GenerationTaskVariable.variable_name == variable_name
    ).all()
    
    if not vars:
        raise HTTPException(status_code=404, detail="Variable not found")
    
    if len(vars) > 1:
        # 有多个同名变量（来自不同模板），需要明确指定
        template_paths = [v.template_path or '主模板' for v in vars]
        raise HTTPException(
            status_code=400, 
            detail=f"发现多个名为 '{variable_name}' 的变量（位于: {', '.join(template_paths)}），请在前端使用唯一标识符来指定要重试的变量"
        )
    
    var = vars[0]
    
    # Check if variable can be retried
    # Allow retry for FAILED, CANCELLED, and stuck PENDING (no started_at or started > 5 min ago)
    can_retry = False
    
    if var.status in ['failed', 'cancelled']:
        can_retry = True
    elif var.status == 'pending':
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
            detail=f"Cannot retry variable in status: {var.status}. Variable is currently running or completed."
        )
    
    # Reset variable status
    var.status = 'pending'
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
            logger.error(f"Task {task_id} not found for retry")
            return
        
        template = db_session.query(Template).filter_by(id=task.template_id).first()
        if not template:
            logger.error(f"Template {task.template_id} not found for retry")
            return
        
        # Parse metadata
        metadata_dict = template.metadata_json if isinstance(template.metadata_json, dict) else {}
        metadata = {
            name: VariableMetadata(**config) 
            for name, config in metadata_dict.items()
        }
        
        variable_meta = metadata.get(variable_name)
        if not variable_meta:
            logger.error(f"Variable {variable_name} not found in metadata")
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
            GenerationTaskVariable.status == 'success'
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
        # 使用 template_id 来确保找到正确的变量（支持同名变量）
        var_record = db_session.query(GenerationTaskVariable).filter(
            GenerationTaskVariable.task_id == task_id,
            GenerationTaskVariable.variable_name == variable_name,
            GenerationTaskVariable.template_id == var.template_id
        ).first()
        
        if not var_record:
            raise HTTPException(status_code=404, detail="Variable record not found for update")
        
        var_record.status = 'running'
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
        var_record.status = result.status.value  # 直接使用枚举的字符串值
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
            all_success = all(v.status == 'success' for v in all_vars)
            
            if all_success:
                # Continue with report generation
                logger.info(f"All variables successful after retry, continuing with report generation for task {task_id}")
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
        logger.error(f"Error during variable retry: {str(e)}", exc_info=True)
        
        # Update variable to failed
        try:
            # 使用 template_id 来确保找到正确的变量（支持同名变量）
            var_record = db_session.query(GenerationTaskVariable).filter(
                GenerationTaskVariable.task_id == task_id,
                GenerationTaskVariable.variable_name == variable_name,
                GenerationTaskVariable.template_id == var.template_id
            ).first()
            if var_record:
                var_record.status = 'failed'
                var_record.error_message = str(e)
                var_record.finished_at = datetime.utcnow()
                db_session.commit()
                
                await ws_manager.broadcast_variable_failed(
                    task_id=task_id,
                    variable_name=variable_name,
                    error_message=str(e)
                )
        except Exception as commit_error:
            logger.error(f"Failed to update variable status: {commit_error}", exc_info=True)
    
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
            GenerationTaskVariable.status == 'success'
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
                status='success',
                markdown_content=markdown_content,
                cost_usd=0,
                duration_ms=duration_ms
            )
            db_session.add(report)
        else:
            # Update existing report
            report_id = report.id
            report.title = f"Report for {template.name}"
            report.status = 'success'
            report.markdown_content = markdown_content
            report.duration_ms = duration_ms
        
        # Update task status
        task.status = 'success'
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
        logger.error(f"Error continuing report generation: {str(e)}", exc_info=True)
        
        # Mark task as failed
        task.status = 'failed'
        task.finished_at = datetime.utcnow()
        
        # Update report status to FAILED
        report = db_session.query(Report).filter(Report.task_id == task_id).first()
        if report:
            report.status = 'failed'
        
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
            created_at=log.created_at,
            template_id=log.template_id,      # 添加 template_id
            template_path=log.template_path   # 添加 template_path
        )
        for log in logs
    ]
    
    return ExecutionLogListResponse(
        logs=log_items,
        total=total
    )

