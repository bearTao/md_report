"""Template renderer service - P0"""
from typing import Dict, Any, Set, Optional
import re
import logging
from datetime import datetime, timezone
from jinja2 import Environment, BaseLoader, TemplateError
from jinja2.sandbox import SandboxedEnvironment
from jinja2 import tests as jinja2_tests
from app.core.exceptions import TemplateRenderError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TemplateRenderer:
    """
    Jinja2 template renderer with sandboxed environment
    """
    
    def __init__(self):
        # Use SandboxedEnvironment for security
        self.env = SandboxedEnvironment(
            autoescape=False,  # Markdown doesn't need HTML escaping
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Register all Jinja2 built-in tests for full compatibility
        # This includes: equalto, defined, undefined, etc.
        self.env.tests.update(jinja2_tests.TESTS)
        
        # Add custom tests for regex matching (removed in Jinja2 3.x)
        self.env.tests['search'] = self._test_search
        self.env.tests['match'] = self._test_match
        
        # Register custom filters (P1, basic ones for now)
        self.env.filters['json'] = self._json_filter
        
    def _json_filter(self, value, indent=2):
        """Convert value to JSON string"""
        import json
        return json.dumps(value, indent=indent, ensure_ascii=False)
    
    def _test_search(self, value, pattern, ignorecase=False):
        """Test if value contains pattern (regex search)"""
        import re
        flags = re.IGNORECASE if ignorecase else 0
        return bool(re.search(pattern, str(value), flags))
    
    def _test_match(self, value, pattern, ignorecase=False):
        """Test if value matches pattern from start (regex match)"""
        import re
        flags = re.IGNORECASE if ignorecase else 0
        return bool(re.match(pattern, str(value), flags))
    
    async def _resolve_includes(
        self,
        template_content: str,
        db_session: Session,
        nested_user_inputs: Dict[str, Dict[str, Any]],
        current_template_id: str,
        main_task_id: str,  # 主任务ID
        parent_path: str = "",  # 父级路径
        openai_api_key: Optional[str] = None,
        openai_api_base: Optional[str] = None,
        visited: Optional[Set[str]] = None,
        progress_callback = None  # 添加 progress_callback 参数
    ) -> str:
        """
        Resolve template includes with nested user_inputs structure
        
        Each template uses only its own user_inputs from nested_user_inputs[template_id]
        
        Args:
            template_content: Template content with potential include tags
            db_session: Database session
            nested_user_inputs: Nested structure {template_id: {var: value}}
            current_template_id: Current template ID for logging
            main_task_id: 主任务ID（所有子模板共享）
            parent_path: 父级路径（如 "主模板" 或 "主模板 > 子模板1"）
            openai_api_key: OpenAI API key
            openai_api_base: OpenAI API base URL
            visited: Set of template IDs to detect circular includes
            
        Returns:
            Template content with all includes resolved
        """
        if visited is None:
            visited = set()
        
        # Find all {% include "template_id" %} tags
        include_pattern = r'{%\s*include\s+"([^"]+)"\s*%}'
        matches = list(re.finditer(include_pattern, template_content))
        
        if not matches:
            return template_content
        
        # Process includes in reverse order to avoid index shifting
        result = template_content
        for match in reversed(matches):
            template_id = match.group(1)
            
            # Check for circular includes
            if template_id in visited:
                error_msg = f"<!-- ERROR: Circular include detected for template '{template_id}' -->"
                result = result[:match.start()] + error_msg + result[match.end():]
                continue
            
            try:
                # Load sub-template from database
                from app.models.db_models import Template
                sub_template = db_session.query(Template).filter(
                    Template.id == template_id
                ).first()
                
                if not sub_template:
                    error_msg = f"<!-- ERROR: Template '{template_id}' not found -->"
                    result = result[:match.start()] + error_msg + result[match.end():]
                    continue
                
                # Mark as visited
                new_visited = visited.copy()
                new_visited.add(template_id)
                
                # Get user inputs for this specific sub-template
                sub_user_inputs = nested_user_inputs.get(template_id, {})
                
                # 构建完整的模板路径
                if parent_path:
                    sub_template_path = f"{parent_path} > {sub_template.name or template_id}"
                else:
                    # 如果没有父路径，说明当前是主模板
                    sub_template_path = sub_template.name or template_id
                
                # Recursively resolve includes in sub-template
                resolved_sub_content = await self._resolve_includes(
                    sub_template.template_content,
                    db_session,
                    nested_user_inputs,
                    template_id,
                    main_task_id,
                    sub_template_path,  # 传递当前路径作为子模板的父路径
                    openai_api_key,
                    openai_api_base,
                    new_visited,
                    progress_callback  # 传递 progress_callback
                )
                
                # Execute and render sub-template with its own user_inputs
                rendered_sub_content = await self._execute_and_render_template(
                    template_id,
                    resolved_sub_content,
                    sub_template.metadata_json,
                    sub_user_inputs,  # Only use this template's user_inputs
                    db_session,
                    main_task_id,
                    sub_template_path,
                    openai_api_key,
                    openai_api_base,
                    progress_callback  # 传递 progress_callback
                )
                
                # Replace include tag with rendered sub-template
                result = result[:match.start()] + rendered_sub_content + result[match.end():]
                
            except Exception as e:
                error_msg = f"<!-- ERROR: Failed to include template '{template_id}': {str(e)} -->"
                result = result[:match.start()] + error_msg + result[match.end():]
                continue
        
        return result
    
    async def _execute_and_render_template(
        self,
        template_id: str,
        template_content: str,
        metadata_json: Dict[str, Any],
        user_inputs: Dict[str, Any],  # This template's own user_inputs only
        db_session: Session,
        main_task_id: str,  # 主任务ID
        template_path: str,  # 模板层级路径
        openai_api_key: Optional[str] = None,
        openai_api_base: Optional[str] = None,
        progress_callback = None  # 添加 progress_callback 参数
    ) -> str:
        """
        Execute variables and render a template with its own user_inputs
        
        Args:
            template_id: Template ID
            template_content: Template content (with includes already resolved)
            metadata_json: Variable metadata
            user_inputs: User inputs for THIS template only
            db_session: Database session
            main_task_id: 主任务ID（所有子模板共享）
            template_path: 完整层级路径
            openai_api_key: OpenAI API key
            openai_api_base: OpenAI API base URL
            
        Returns:
            Rendered template content
        """
        from app.services.context import ExecutionContext
        from app.services.scheduler import ExecutionScheduler
        from app.core.models import VariableMetadata
        
        # Parse metadata
        metadata = {
            name: VariableMetadata(**config)
            for name, config in metadata_json.items()
        }
        
        # Create execution context with this template's user_inputs
        # 使用主任务ID而不是临时ID
        context = ExecutionContext(
            task_id=main_task_id,
            template_id=template_id,
            user_inputs=user_inputs,  # Only this template's inputs
            metadata=metadata
        )
        
        # 设置模板信息到context，用于变量执行时记录
        context.template_id = template_id
        context.template_path = template_path
        
        # 调试日志
        logger.info(f"子模板 {template_id} context: user_inputs={list(user_inputs.keys())}, metadata={list(metadata.keys())}")
        
        # Create scheduler and execute variables
        scheduler = ExecutionScheduler(
            openai_api_key=openai_api_key,
            openai_api_base=openai_api_base
        )
        
        # 为子模板创建专用的 progress_callback
        # 直接使用子模板的元数据写入数据库，不依赖主模板的 progress_callback
        async def sub_template_progress_callback(var_name: str, status, result):
            if not progress_callback:
                return
            
            # 从子模板的 metadata 获取变量元数据
            if var_name not in metadata:
                logger.warning(f"变量 {var_name} 不在子模板 {template_id} 的元数据中")
                return
            
            var_meta = metadata[var_name]
            
            # 导入必要的模块
            from app.models.db_models import GenerationTaskVariable, VariableStatusType
            from app.services.websocket_manager import ws_manager
            from app.database import SessionLocal
            from datetime import datetime
            from app.core.models import VariableStatus
            
            db_session = SessionLocal()
            try:
                if status == VariableStatus.RUNNING:
                    var_record = GenerationTaskVariable(
                        task_id=main_task_id,
                        variable_name=var_name,
                        source=var_meta.source.value,
                        status='running',
                        started_at=datetime.now(timezone.utc),
                        template_id=template_id,
                        template_path=template_path
                    )
                    db_session.add(var_record)
                    db_session.commit()
                    
                    # Broadcast variable started event
                    await ws_manager.broadcast_variable_started(
                        task_id=main_task_id,
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
                        GenerationTaskVariable.task_id == main_task_id,
                        GenerationTaskVariable.variable_name == var_name,
                        GenerationTaskVariable.template_id == template_id
                    ).first()
                    
                    if var_record:
                        var_record.status = VariableStatusType(status.value)
                        var_record.finished_at = datetime.now(timezone.utc)
                        if result:
                            var_record.duration_ms = result.duration_ms
                            if result.error:
                                var_record.error_message = result.error
                            if result.value is not None:
                                var_record.result_preview = result.value
                        db_session.commit()
                        
                        # Broadcast variable completed or failed event
                        if status == VariableStatus.SUCCESS:
                            await ws_manager.broadcast_variable_completed(
                                task_id=main_task_id,
                                variable_name=var_name,
                                duration_ms=var_record.duration_ms or 0,
                                result_preview=var_record.result_preview
                            )
                        else:  # FAILED
                            await ws_manager.broadcast_variable_failed(
                                task_id=main_task_id,
                                variable_name=var_name,
                                error={"code": "EXECUTION_ERROR", "message": result.error if result else "Unknown error"},
                                duration_ms=var_record.duration_ms or 0
                            )
            except Exception as e:
                logger.error(f"子模板变量进度回调失败: {e}", exc_info=True)
            finally:
                db_session.close()
        
        # 传递子模板专用的 progress_callback
        logger.info(f"执行子模板 {template_id} (路径: {template_path}) 的变量, progress_callback: {progress_callback is not None}")
        await scheduler.execute_all(context, sub_template_progress_callback if progress_callback else None)
        
        # Render template with executed variables
        rendered = self.render(template_content, context.get_all_variables(), 
                             main_task_id, template_id, template_path)
        
        return rendered
        
    def render(self, template_content: str, variables: Dict[str, Any], task_id: Optional[str] = None, 
               template_id: Optional[str] = None, template_path: Optional[str] = None) -> str:
        """
        Render Jinja2 template with variables
        
        Args:
            template_content: Jinja2 template string
            variables: Dictionary of variables to inject
            task_id: Optional task ID for logging to database
            template_id: Optional template ID for logging
            template_path: Optional template path for logging
            
        Returns:
            Rendered Markdown string
        """
        # INFO 级别：记录渲染开始
        logger.info(f"Starting template render with {len(variables)} variables")
        self._log_to_db(task_id, "INFO", f"开始渲染模板，共 {len(variables)} 个变量", template_id, template_path)
        
        # DEBUG 级别：记录详细信息
        logger.debug(f"Template size: {len(template_content)} characters")
        logger.debug(f"Variables: {list(variables.keys())}")
        self._log_to_db(task_id, "DEBUG", f"模板大小: {len(template_content)} 字符，变量: {', '.join(list(variables.keys()))}", template_id, template_path)
        
        try:
            import time
            start_time = time.time()
            
            # Create template from string
            template = self.env.from_string(template_content)
            
            # Render with variables
            result = template.render(**variables)
            
            # Post-processing: clean up extra blank lines
            result = self._post_process(result)
            
            # INFO 级别：记录渲染成功
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Template rendered successfully in {duration_ms}ms, output size: {len(result)} characters")
            self._log_to_db(task_id, "INFO", f"模板渲染成功，耗时 {duration_ms}ms，输出大小 {len(result)} 字符", template_id, template_path)
            
            return result
            
        except TemplateError as e:
            # ERROR 级别：记录模板错误
            error_msg = f"模板语法错误: {str(e)}"
            logger.error(f"Template rendering failed: {str(e)}")
            logger.debug(f"Template content preview: {template_content[:500]}")
            self._log_to_db(task_id, "ERROR", error_msg, template_id, template_path)
            raise TemplateRenderError(f"Template rendering failed: {str(e)}") from e
        except Exception as e:
            # ERROR 级别：记录意外错误
            error_msg = f"渲染过程发生意外错误: {str(e)}"
            logger.error(f"Unexpected error during rendering: {str(e)}", exc_info=True)
            self._log_to_db(task_id, "ERROR", error_msg, template_id, template_path)
            raise TemplateRenderError(f"Unexpected error during rendering: {str(e)}") from e
    
    def _log_to_db(self, task_id: Optional[str], level: str, message: str, 
                    template_id: Optional[str] = None, template_path: Optional[str] = None):
        """将日志写入数据库"""
        if not task_id:
            return
        
        try:
            from app.database import SessionLocal
            from app.models.db_models import ExecutionLog, LogLevel
            
            db = SessionLocal()
            try:
                log_entry = ExecutionLog(
                    task_id=task_id,
                    variable_name="[渲染引擎]",  # 使用特殊标记表示这是渲染日志
                    level=LogLevel[level],
                    message=message,
                    template_id=template_id,
                    template_path=template_path
                )
                db.add(log_entry)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            # 日志写入失败不应该影响渲染过程
            logger.warning(f"Failed to write render log to database: {e}")
            
    def _post_process(self, content: str) -> str:
        """
        Post-process rendered content
        - Remove excessive blank lines (more than 2 consecutive)
        - Strip trailing whitespace from lines
        """
        lines = content.split('\n')
        
        # Strip trailing whitespace from each line
        lines = [line.rstrip() for line in lines]
        
        # Remove excessive blank lines
        result_lines = []
        blank_count = 0
        
        for line in lines:
            if line == '':
                blank_count += 1
                if blank_count <= 2:
                    result_lines.append(line)
            else:
                blank_count = 0
                result_lines.append(line)
        
        return '\n'.join(result_lines).strip() + '\n'
        
    def validate_template(self, template_content: str) -> tuple[bool, str]:
        """
        Validate template syntax
        Returns (is_valid, error_message)
        """
        try:
            self.env.from_string(template_content)
            return True, ""
        except TemplateError as e:
            return False, str(e)


# Global instance
template_renderer = TemplateRenderer()

