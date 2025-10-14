"""Database connector - P0"""
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
import time


class DatabaseConnector:
    """
    Database connection manager
    Supports PostgreSQL, MySQL, SQL Server, etc.
    """
    
    def __init__(self):
        self._engines: Dict[str, Any] = {}
        
    def register_connection(self, name: str, connection_url: str, 
                           pool_size: int = 5, max_overflow: int = 10):
        """Register a database connection"""
        engine = create_engine(
            connection_url,
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
                # For PostgreSQL/MySQL: statement_timeout
                conn.execute(text(f"SET statement_timeout = {timeout * 1000}"))
                
                # Execute query
                if parameters:
                    result = conn.execute(text(query), parameters)
                else:
                    result = conn.execute(text(query))
                
                # Convert to list of dicts
                rows = []
                for row in result:
                    rows.append(dict(row._mapping))
                
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

