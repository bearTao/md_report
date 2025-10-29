"""Template renderer service - P0"""
from typing import Dict, Any, Set, Optional
import re
import logging
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
        openai_api_key: Optional[str] = None,
        openai_api_base: Optional[str] = None,
        visited: Optional[Set[str]] = None
    ) -> str:
        """
        Resolve template includes with nested user_inputs structure
        
        Each template uses only its own user_inputs from nested_user_inputs[template_id]
        
        Args:
            template_content: Template content with potential include tags
            db_session: Database session
            nested_user_inputs: Nested structure {template_id: {var: value}}
            current_template_id: Current template ID for logging
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
                
                # Recursively resolve includes in sub-template
                resolved_sub_content = await self._resolve_includes(
                    sub_template.template_content,
                    db_session,
                    nested_user_inputs,
                    template_id,
                    openai_api_key,
                    openai_api_base,
                    new_visited
                )
                
                # Execute and render sub-template with its own user_inputs
                rendered_sub_content = await self._execute_and_render_template(
                    template_id,
                    resolved_sub_content,
                    sub_template.metadata_json,
                    sub_user_inputs,  # Only use this template's user_inputs
                    db_session,
                    openai_api_key,
                    openai_api_base
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
        openai_api_key: Optional[str] = None,
        openai_api_base: Optional[str] = None
    ) -> str:
        """
        Execute variables and render a template with its own user_inputs
        
        Args:
            template_id: Template ID
            template_content: Template content (with includes already resolved)
            metadata_json: Variable metadata
            user_inputs: User inputs for THIS template only
            db_session: Database session
            openai_api_key: OpenAI API key
            openai_api_base: OpenAI API base URL
            
        Returns:
            Rendered template content
        """
        from app.services.context import ExecutionContext
        from app.services.scheduler import ExecutionScheduler
        from app.core.models import VariableMetadata
        import uuid
        
        # Create temporary task ID for sub-template
        task_id = f"include_{template_id}_{uuid.uuid4().hex[:8]}"
        
        # Parse metadata
        metadata = {
            name: VariableMetadata(**config)
            for name, config in metadata_json.items()
        }
        
        # Create execution context with this template's user_inputs
        context = ExecutionContext(
            task_id=task_id,
            template_id=template_id,
            user_inputs=user_inputs,  # Only this template's inputs
            metadata=metadata
        )
        
        # Create scheduler and execute variables
        scheduler = ExecutionScheduler(
            openai_api_key=openai_api_key,
            openai_api_base=openai_api_base
        )
        
        await scheduler.execute_all(context)
        
        # Render template with executed variables
        rendered = self.render(template_content, context.get_all_variables())
        
        return rendered
        
    def render(self, template_content: str, variables: Dict[str, Any], task_id: Optional[str] = None) -> str:
        """
        Render Jinja2 template with variables
        
        Args:
            template_content: Jinja2 template string
            variables: Dictionary of variables to inject
            task_id: Optional task ID for logging to database
            
        Returns:
            Rendered Markdown string
        """
        # INFO 级别：记录渲染开始
        logger.info(f"Starting template render with {len(variables)} variables")
        self._log_to_db(task_id, "INFO", f"开始渲染模板，共 {len(variables)} 个变量")
        
        # DEBUG 级别：记录详细信息
        logger.debug(f"Template size: {len(template_content)} characters")
        logger.debug(f"Variables: {list(variables.keys())}")
        self._log_to_db(task_id, "DEBUG", f"模板大小: {len(template_content)} 字符，变量: {', '.join(list(variables.keys()))}")
        
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
            self._log_to_db(task_id, "INFO", f"模板渲染成功，耗时 {duration_ms}ms，输出大小 {len(result)} 字符")
            
            return result
            
        except TemplateError as e:
            # ERROR 级别：记录模板错误
            error_msg = f"模板语法错误: {str(e)}"
            logger.error(f"Template rendering failed: {str(e)}")
            logger.debug(f"Template content preview: {template_content[:500]}")
            self._log_to_db(task_id, "ERROR", error_msg)
            raise TemplateRenderError(f"Template rendering failed: {str(e)}") from e
        except Exception as e:
            # ERROR 级别：记录意外错误
            error_msg = f"渲染过程发生意外错误: {str(e)}"
            logger.error(f"Unexpected error during rendering: {str(e)}", exc_info=True)
            self._log_to_db(task_id, "ERROR", error_msg)
            raise TemplateRenderError(f"Unexpected error during rendering: {str(e)}") from e
    
    def _log_to_db(self, task_id: Optional[str], level: str, message: str):
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
                    message=message
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

