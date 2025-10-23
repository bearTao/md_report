"""Template validation service"""
from typing import List, Dict, Any, Optional
from jinja2 import Environment, meta, TemplateSyntaxError
from jinja2.sandbox import SandboxedEnvironment
import logging

logger = logging.getLogger(__name__)


class ValidationIssue:
    """Represents a single validation issue"""
    
    def __init__(
        self,
        level: str,  # "error" or "warning"
        category: str,  # "syntax", "metadata", "dependency", "schema"
        message: str,
        location: Optional[str] = None
    ):
        self.level = level
        self.category = category
        self.message = message
        self.location = location
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "level": self.level,
            "category": self.category,
            "message": self.message,
            "location": self.location
        }


class TemplateValidator:
    """
    Service for validating templates and their metadata
    
    Validates:
    1. Jinja2 syntax
    2. Variable references (template vs metadata)
    3. Metadata structure completeness
    4. Dependency graph (no cycles, all dependencies exist)
    5. Schema format (for AI variables)
    """
    
    def __init__(self):
        self.env = SandboxedEnvironment()
        self.issues: List[ValidationIssue] = []
    
    def validate_template(
        self,
        template_content: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate template and metadata
        
        Args:
            template_content: Jinja2 template content
            metadata: Variable metadata dictionary
        
        Returns:
            Dictionary with validation results:
            {
                "valid": bool,
                "issues": [{"level": str, "category": str, "message": str, "location": str}]
            }
        """
        self.issues = []
        
        # Run all validations
        self._validate_jinja2_syntax(template_content)
        self._validate_variable_references(template_content, metadata)
        self._validate_metadata_structure(metadata)
        self._validate_dependencies(metadata)
        self._validate_schemas(metadata)
        
        # Determine if valid (no errors, warnings are OK)
        has_errors = any(issue.level == "error" for issue in self.issues)
        
        return {
            "valid": not has_errors,
            "issues": [issue.to_dict() for issue in self.issues]
        }
    
    def _validate_jinja2_syntax(self, template_content: str):
        """Validate Jinja2 template syntax"""
        try:
            self.env.parse(template_content)
        except TemplateSyntaxError as e:
            self.issues.append(ValidationIssue(
                level="error",
                category="syntax",
                message=f"Jinja2 syntax error: {str(e)}",
                location=f"Line {e.lineno}" if e.lineno else None
            ))
        except Exception as e:
            self.issues.append(ValidationIssue(
                level="error",
                category="syntax",
                message=f"Template parsing error: {str(e)}"
            ))
    
    def _validate_variable_references(
        self,
        template_content: str,
        metadata: Dict[str, Any]
    ):
        """Check that template variables are defined in metadata"""
        try:
            # Parse template to find variables
            ast = self.env.parse(template_content)
            template_vars = meta.find_undeclared_variables(ast)
            
            # Get defined variables from metadata
            defined_vars = set(metadata.keys())
            
            # Find undefined variables
            undefined_vars = template_vars - defined_vars
            
            # Exclude common built-in variables
            builtins = {'loop', 'range', 'lipsum', 'cycler', 'joiner', 'namespace'}
            undefined_vars = undefined_vars - builtins
            
            for var in undefined_vars:
                self.issues.append(ValidationIssue(
                    level="error",
                    category="metadata",
                    message=f"Variable '{var}' is used in template but not defined in metadata",
                    location="template"
                ))
            
            # Find unused variables (warning only)
            unused_vars = defined_vars - template_vars
            for var in unused_vars:
                self.issues.append(ValidationIssue(
                    level="warning",
                    category="metadata",
                    message=f"Variable '{var}' is defined but not used in template",
                    location="metadata"
                ))
        
        except Exception as e:
            logger.error(f"Error parsing template variables: {str(e)}")
            self.issues.append(ValidationIssue(
                level="error",
                category="syntax",
                message=f"Unable to parse template variables: {str(e)}"
            ))
    
    def _validate_metadata_structure(self, metadata: Dict[str, Any]):
        """Validate metadata structure and required fields"""
        valid_sources = [
            "user_input", "sql", "api", "system",
            "ai_generation", "image", "vision_ai"
        ]
        
        for var_name, var_meta in metadata.items():
            if not isinstance(var_meta, dict):
                self.issues.append(ValidationIssue(
                    level="error",
                    category="metadata",
                    message=f"Variable '{var_name}' metadata must be a dictionary"
                ))
                continue
            
            # Check required fields
            if "type" not in var_meta:
                self.issues.append(ValidationIssue(
                    level="error",
                    category="metadata",
                    message=f"Variable '{var_name}' missing required field 'type'"
                ))
            
            if "source" not in var_meta:
                self.issues.append(ValidationIssue(
                    level="error",
                    category="metadata",
                    message=f"Variable '{var_name}' missing required field 'source'"
                ))
            else:
                # Validate source value
                source = var_meta["source"]
                if source not in valid_sources:
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="metadata",
                        message=f"Variable '{var_name}' has invalid source '{source}'. "
                                f"Valid sources: {', '.join(valid_sources)}"
                    ))
                else:
                    # Check for source-specific config
                    self._validate_source_config(var_name, var_meta, source)
    
    def _validate_source_config(self, var_name: str, var_meta: Dict, source: str):
        """Validate that required config exists for each source type"""
        config_map = {
            "sql": "sql_config",
            "api": "api_config",
            "ai_generation": "ai_config",
            "image": "image_config",
            "vision_ai": "vision_ai_config"
        }
        
        if source in config_map:
            config_key = config_map[source]
            if config_key not in var_meta:
                self.issues.append(ValidationIssue(
                    level="error",
                    category="metadata",
                    message=f"Variable '{var_name}' with source '{source}' missing required '{config_key}'"
                ))
            else:
                # Validate specific config fields
                config = var_meta[config_key]
                if source == "sql" and not isinstance(config, dict):
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="metadata",
                        message=f"Variable '{var_name}': sql_config must be a dictionary"
                    ))
                elif source == "sql" and isinstance(config, dict):
                    if "query" not in config:
                        self.issues.append(ValidationIssue(
                            level="error",
                            category="metadata",
                            message=f"Variable '{var_name}': sql_config missing required 'query' field"
                        ))
                
                if source == "api" and isinstance(config, dict):
                    if "endpoint" not in config:
                        self.issues.append(ValidationIssue(
                            level="error",
                            category="metadata",
                            message=f"Variable '{var_name}': api_config missing required 'endpoint' field"
                        ))
                
                if source == "ai_generation" and isinstance(config, dict):
                    if "prompt_template" not in config:
                        self.issues.append(ValidationIssue(
                            level="error",
                            category="metadata",
                            message=f"Variable '{var_name}': ai_config missing required 'prompt_template' field"
                        ))
                
                if source == "image" and isinstance(config, dict):
                    if "endpoint" not in config:
                        self.issues.append(ValidationIssue(
                            level="error",
                            category="metadata",
                            message=f"Variable '{var_name}': image_config missing required 'endpoint' field"
                        ))
                
                if source == "vision_ai" and isinstance(config, dict):
                    if "image_source" not in config:
                        self.issues.append(ValidationIssue(
                            level="error",
                            category="metadata",
                            message=f"Variable '{var_name}': vision_ai_config missing required 'image_source' field"
                        ))
                    if "prompt_template" not in config:
                        self.issues.append(ValidationIssue(
                            level="error",
                            category="metadata",
                            message=f"Variable '{var_name}': vision_ai_config missing required 'prompt_template' field"
                        ))
    
    def _validate_dependencies(self, metadata: Dict[str, Any]):
        """Validate dependency graph (check existence and cycles)"""
        # Build dependency graph
        graph = {}
        for var_name, var_meta in metadata.items():
            if isinstance(var_meta, dict):
                deps = var_meta.get("dependencies", [])
                graph[var_name] = deps if isinstance(deps, list) else []
            else:
                graph[var_name] = []
        
        # Check that all dependencies exist
        for var_name, deps in graph.items():
            for dep in deps:
                if dep not in metadata:
                    self.issues.append(ValidationIssue(
                        level="error",
                        category="dependency",
                        message=f"Variable '{var_name}' depends on undefined variable '{dep}'"
                    ))
        
        # Check for circular dependencies
        cycles = self._detect_cycles(graph)
        for cycle in cycles:
            cycle_str = " → ".join(cycle)
            self.issues.append(ValidationIssue(
                level="error",
                category="dependency",
                message=f"Circular dependency detected: {cycle_str}"
            ))
    
    def _detect_cycles(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """Detect cycles in dependency graph using DFS"""
        cycles = []
        visited = set()
        path = []
        path_set = set()
        
        def dfs(node: str):
            if node in path_set:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            path_set.add(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor)
            
            path.pop()
            path_set.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node)
        
        return cycles
    
    def _validate_schemas(self, metadata: Dict[str, Any]):
        """Validate schema format for AI variables"""
        for var_name, var_meta in metadata.items():
            if not isinstance(var_meta, dict):
                continue
            
            source = var_meta.get("source")
            if source in ["ai_generation", "vision_ai"]:
                schema = var_meta.get("schema")
                if schema:
                    if not isinstance(schema, dict):
                        self.issues.append(ValidationIssue(
                            level="error",
                            category="schema",
                            message=f"Variable '{var_name}': schema must be a dictionary"
                        ))
                    elif "type" not in schema:
                        self.issues.append(ValidationIssue(
                            level="warning",
                            category="schema",
                            message=f"Variable '{var_name}': schema missing 'type' field (recommended for AI output validation)"
                        ))


# Global instance
template_validator = TemplateValidator()

