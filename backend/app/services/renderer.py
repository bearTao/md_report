"""Template renderer service - P0"""
from typing import Dict, Any
from jinja2 import Environment, BaseLoader, TemplateError
from jinja2.sandbox import SandboxedEnvironment
from app.core.exceptions import TemplateRenderError


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
        
        # Register custom filters (P1, basic ones for now)
        self.env.filters['json'] = self._json_filter
        
    def _json_filter(self, value, indent=2):
        """Convert value to JSON string"""
        import json
        return json.dumps(value, indent=indent, ensure_ascii=False)
        
    def render(self, template_content: str, variables: Dict[str, Any]) -> str:
        """
        Render Jinja2 template with variables
        
        Args:
            template_content: Jinja2 template string
            variables: Dictionary of variables to inject
            
        Returns:
            Rendered Markdown string
        """
        try:
            # Create template from string
            template = self.env.from_string(template_content)
            
            # Render with variables
            result = template.render(**variables)
            
            # Post-processing: clean up extra blank lines
            result = self._post_process(result)
            
            return result
            
        except TemplateError as e:
            raise TemplateRenderError(f"Template rendering failed: {str(e)}") from e
        except Exception as e:
            raise TemplateRenderError(f"Unexpected error during rendering: {str(e)}") from e
            
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

