"""Execution logger service for task and variable logging"""
from typing import Optional, Dict, Any
import logging
from app.database import SessionLocal
from app.models.db_models import ExecutionLog, LogLevel

# Standard Python logger
logger = logging.getLogger(__name__)


class ExecutionLogger:
    """
    Service for logging task and variable execution events
    
    Logs are written to both:
    1. Database (execution_logs table) for querying and analysis
    2. Standard Python logger for real-time monitoring
    """
    
    @staticmethod
    def log(
        task_id: str,
        message: str,
        level: str = "INFO",
        variable_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Write a log entry
        
        Args:
            task_id: Task identifier
            message: Log message
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            variable_name: Variable name (None for task-level logs)
            context: Additional context information (dict)
        """
        db = SessionLocal()
        try:
            # Validate and normalize level
            level_upper = level.upper()
            if level_upper not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
                level_upper = "INFO"
            
            # Create log entry
            log_entry = ExecutionLog(
                task_id=task_id,
                variable_name=variable_name,
                level=LogLevel[level_upper],
                message=message,
                context_json=context
            )
            db.add(log_entry)
            db.commit()
            
            # Also log to standard Python logger
            log_prefix = f"[{task_id}]"
            if variable_name:
                log_prefix += f" [{variable_name}]"
            
            log_method = getattr(logger, level_upper.lower(), logger.info)
            log_method(f"{log_prefix} {message}")
            
        except Exception as e:
            logger.error(f"Failed to write execution log: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    @staticmethod
    def debug(task_id: str, message: str, **kwargs):
        """Log DEBUG level message"""
        ExecutionLogger.log(task_id, message, "DEBUG", **kwargs)
    
    @staticmethod
    def info(task_id: str, message: str, **kwargs):
        """Log INFO level message"""
        ExecutionLogger.log(task_id, message, "INFO", **kwargs)
    
    @staticmethod
    def warning(task_id: str, message: str, **kwargs):
        """Log WARNING level message"""
        ExecutionLogger.log(task_id, message, "WARNING", **kwargs)
    
    @staticmethod
    def error(task_id: str, message: str, **kwargs):
        """Log ERROR level message"""
        ExecutionLogger.log(task_id, message, "ERROR", **kwargs)


# Global instance for convenient access
execution_logger = ExecutionLogger()

