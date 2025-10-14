"""Custom exceptions"""


class ExecutionError(Exception):
    """Base execution error"""
    pass


class VariableExecutionError(ExecutionError):
    """Variable execution failed"""
    def __init__(self, variable_name: str, message: str, original_error: Exception = None):
        self.variable_name = variable_name
        self.message = message
        self.original_error = original_error
        super().__init__(f"Variable '{variable_name}' execution failed: {message}")


class DependencyError(ExecutionError):
    """Dependency resolution error"""
    pass


class ValidationError(ExecutionError):
    """Validation error"""
    pass


class TemplateRenderError(ExecutionError):
    """Template rendering error"""
    pass


class SqlExecutionError(VariableExecutionError):
    """SQL execution error"""
    pass


class ApiExecutionError(VariableExecutionError):
    """API execution error"""
    pass


class AiGenerationError(VariableExecutionError):
    """AI generation error"""
    pass

