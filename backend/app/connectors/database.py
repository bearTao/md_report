"""
数据库连接器模块

功能说明：
- 管理多个数据库连接
- 支持连接池管理
- 执行SQL查询并返回结果
- 自动类型转换（日期、Decimal等）
- 支持参数化查询（防SQL注入）
"""
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
    数据库连接管理器
    
    功能：
    1. 注册和管理多个数据库连接
    2. 使用连接池提高性能
    3. 执行SQL查询并格式化结果
    4. 自动转换非JSON类型（日期、Decimal等）
    5. 支持连接健康检查
    
    支持的数据库：
    - PostgreSQL
    - MySQL / MariaDB
    - SQL Server
    - SQLite
    - Oracle
    """
    
    def __init__(self):
        """初始化连接器，创建空的引擎字典"""
        self._engines: Dict[str, Any] = {}
    
    def _convert_to_serializable(self, obj: Any) -> Any:
        """
        将非JSON可序列化对象转换为可序列化格式
        
        转换规则：
        - datetime/date → ISO格式字符串（如：2024-01-01T12:00:00）
        - Decimal → float
        - bytes → UTF-8字符串
        - None → None
        - 其他 → 保持不变
        
        Args:
            obj: 需要转换的对象
            
        Returns:
            Any: JSON可序列化的对象
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
        注册数据库连接
        
        支持两种方式：
        1. 传入连接URL字符串（自动创建引擎和连接池）
        2. 传入已存在的Engine对象（直接使用）
        
        连接URL格式示例：
        - PostgreSQL: postgresql://user:pass@host:port/db
        - MySQL: mysql+pymysql://user:pass@host:port/db
        - SQL Server: mssql+pyodbc://user:pass@host:port/db
        - SQLite: sqlite:///path/to/db.sqlite
        
        Args:
            name: 连接名称（用于后续引用）
            connection_url_or_engine: 数据库URL或Engine对象
            pool_size: 连接池大小（仅用于URL字符串）
            max_overflow: 最大溢出连接数（仅用于URL字符串）
        """
        if isinstance(connection_url_or_engine, Engine):
            # 方式1：直接使用已存在的Engine
            self._engines[name] = connection_url_or_engine
        else:
            # 方式2：从URL创建新的Engine
            engine = create_engine(
                connection_url_or_engine,
                poolclass=QueuePool,  # 使用队列连接池
                pool_size=pool_size,  # 连接池大小
                max_overflow=max_overflow,  # 最大溢出连接数
                pool_pre_ping=True  # 使用前测试连接是否有效
            )
            self._engines[name] = engine
        
    def get_engine(self, name: str):
        """
        根据连接名称获取数据库引擎
        
        Args:
            name: 连接名称
        
        Returns:
            Engine: SQLAlchemy引擎对象
            
        Raises:
            ValueError: 连接未注册
        """
        if name not in self._engines:
            raise ValueError(f"Database connection '{name}' not registered")
        return self._engines[name]
        
    async def execute_query(self, connection_name: str, query: str, 
                           parameters: Optional[Dict[str, Any]] = None,
                           timeout: int = 10) -> List[Dict[str, Any]]:
        """
        执行SQL查询并返回结果（字典列表格式）
        
        执行流程：
        1. 获取数据库引擎
        2. 设置查询超时（根据数据库类型）
        3. 执行查询（支持参数化）
        4. 转换结果为JSON可序列化格式
        
        参数化查询示例：
            query = "SELECT * FROM users WHERE id = :user_id AND status = :status"
            parameters = {"user_id": 123, "status": "active"}
        
        Args:
            connection_name: 已注册的连接名称
            query: SQL查询语句
            parameters: 查询参数字典（用于参数化查询，防SQL注入）
            timeout: 查询超时时间（秒）
            
        Returns:
            List[Dict[str, Any]]: 结果行列表，每行是一个字典
            示例：[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
            
        Raises:
            Exception: SQL执行错误
        """
        engine = self.get_engine(connection_name)
        
        try:
            with engine.connect() as conn:
                # 设置查询超时（根据数据库类型）
                dialect_name = engine.dialect.name
                try:
                    if dialect_name == "postgresql":
                        # PostgreSQL: 使用statement_timeout（毫秒）
                        conn.execute(text(f"SET statement_timeout = {timeout * 1000}"))
                    elif dialect_name == "mysql":
                        # MySQL: 使用max_execution_time（毫秒）
                        conn.execute(text(f"SET SESSION max_execution_time = {timeout * 1000}"))
                    # 其他数据库：跳过超时设置
                except Exception:
                    # 如果设置超时失败，继续执行（不影响查询）
                    pass
                
                # 执行查询
                if parameters:
                    # 参数化查询（安全，防SQL注入）
                    result = conn.execute(text(query), parameters)
                else:
                    # 直接查询
                    result = conn.execute(text(query))
                
                # 转换结果为字典列表（JSON可序列化格式）
                rows = []
                for row in result:
                    row_dict = {}
                    for key, value in row._mapping.items():
                        # 转换特殊类型（datetime, Decimal等）
                        row_dict[key] = self._convert_to_serializable(value)
                    rows.append(row_dict)
                
                return rows
                
        except SQLAlchemyError as e:
            raise Exception(f"SQL execution error: {str(e)}") from e
            
    def test_connection(self, name: str) -> bool:
        """
        测试连接是否正常
        
        Args:
            name: 连接名称
        
        Returns:
            bool: True表示连接正常，False表示连接失败
        """
        try:
            engine = self.get_engine(name)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
            
    def close_all(self):
        """
        关闭所有数据库连接
        
        释放所有连接池资源，清空引擎字典
        """
        for engine in self._engines.values():
            engine.dispose()  # 释放连接池
        self._engines.clear()  # 清空字典


# Global instance
db_connector = DatabaseConnector()

