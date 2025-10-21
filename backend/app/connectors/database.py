"""Database connector - P0"""
from typing import Any, Dict, List, Optional, Union
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
from datetime import datetime, date
from decimal import Decimal
import time


class DatabaseConnector:
    """
    Database connection manager
    Supports PostgreSQL, MySQL, SQL Server, etc.
    """
    
    def __init__(self):
        self._engines: Dict[str, Any] = {}
    
    def _convert_to_serializable(self, obj: Any) -> Any:
        """
        Convert non-JSON-serializable objects to serializable format
        
        Args:
            obj: Object to convert
            
        Returns:
            JSON-serializable object
        """
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, bytes):
            return obj.decode('utf-8', errors='ignore')
        elif obj is None:
            return None
        else:
            return obj
        
    def register_connection(self, name: str, connection_url_or_engine: Union[str, Engine], 
                           pool_size: int = 5, max_overflow: int = 10):
        """
        Register a database connection
        
        Args:
            name: Connection name
            connection_url_or_engine: Database URL string or Engine object
            pool_size: Connection pool size (only for URL strings)
            max_overflow: Max overflow connections (only for URL strings)
        """
        if isinstance(connection_url_or_engine, Engine):
            # Use existing engine directly
            self._engines[name] = connection_url_or_engine
        else:
            # Create new engine from URL
            engine = create_engine(
                connection_url_or_engine,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True  # Test connection before use
            )
            self._engines[name] = engine
        
    def get_engine(self, name: str):
        """Get engine by connection name"""
        if name not in self._engines:
            raise ValueError(f"Database connection '{name}' not registered")
        return self._engines[name]
        
    async def execute_query(self, connection_name: str, query: str, 
                           parameters: Optional[Dict[str, Any]] = None,
                           timeout: int = 10) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results as list of dicts
        
        Args:
            connection_name: Name of registered connection
            query: SQL query string
            parameters: Query parameters (for parameterized queries)
            timeout: Query timeout in seconds
            
        Returns:
            List of result rows as dictionaries
        """
        engine = self.get_engine(connection_name)
        
        try:
            with engine.connect() as conn:
                # Set query timeout (database-specific)
                dialect_name = engine.dialect.name
                try:
                    if dialect_name == "postgresql":
                        conn.execute(text(f"SET statement_timeout = {timeout * 1000}"))
                    elif dialect_name == "mysql":
                        # MySQL uses max_execution_time in milliseconds
                        conn.execute(text(f"SET SESSION max_execution_time = {timeout * 1000}"))
                    # For other databases, skip timeout setting
                except Exception:
                    # If setting timeout fails, continue without it
                    pass
                
                # Execute query
                if parameters:
                    result = conn.execute(text(query), parameters)
                else:
                    result = conn.execute(text(query))
                
                # Convert to list of dicts with JSON-serializable values
                rows = []
                for row in result:
                    row_dict = {}
                    for key, value in row._mapping.items():
                        row_dict[key] = self._convert_to_serializable(value)
                    rows.append(row_dict)
                
                return rows
                
        except SQLAlchemyError as e:
            raise Exception(f"SQL execution error: {str(e)}") from e
            
    def test_connection(self, name: str) -> bool:
        """Test if connection is alive"""
        try:
            engine = self.get_engine(name)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
            
    def close_all(self):
        """Close all connections"""
        for engine in self._engines.values():
            engine.dispose()
        self._engines.clear()


# Global instance
db_connector = DatabaseConnector()

