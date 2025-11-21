"""
数据库工具函数模块

功能说明：
- 从模板元数据中提取所需的数据库连接名称
- 按需注册数据库连接（避免重复注册）
- 提供统一的连接注册入口
"""
from typing import Dict, Set, List
from urllib.parse import quote_plus
from sqlalchemy.orm import Session
import logging

from app.core.models import VariableMetadata, VariableSource
from app.models.db_models import DBConnection
from app.connectors.database import db_connector

logger = logging.getLogger(__name__)


def extract_required_connections(metadata: Dict[str, VariableMetadata]) -> Set[str]:
    """
    从模板的变量元数据中提取所需的数据库连接名称
    
    Args:
        metadata: 变量元数据字典 {变量名: VariableMetadata}
    
    Returns:
        Set[str]: 所需的数据库连接名称集合
        
    Example:
        metadata = {
            "user_info": VariableMetadata(
                type="object",
                source=VariableSource.SQL,
                sql_config=SqlConfig(connection="user_db", ...)
            ),
            "sales_data": VariableMetadata(
                type="array",
                source=VariableSource.SQL,
                sql_config=SqlConfig(connection="analytics_db", ...)
            ),
            "report_title": VariableMetadata(
                type="string",
                source=VariableSource.USER_INPUT
            )
        }
        # 返回: {"user_db", "analytics_db"}
    """
    required_connections = set()
    
    for var_name, var_metadata in metadata.items():
        # 兼容字典和对象两种形式
        if isinstance(var_metadata, dict):
            source = var_metadata.get('source')
            sql_config = var_metadata.get('sql_config')
        else:
            source = var_metadata.source
            sql_config = var_metadata.sql_config
        
        # 只处理SQL类型的变量
        if source == VariableSource.SQL.value or source == VariableSource.SQL:
            if sql_config:
                # 兼容字典和对象两种形式
                connection = sql_config.get('connection') if isinstance(sql_config, dict) else sql_config.connection
                if connection:
                    required_connections.add(connection)
    
    return required_connections


def register_required_connections(
    connection_names: Set[str],
    db_session: Session
) -> Dict[str, bool]:
    """
    按需注册指定的数据库连接（避免重复注册）
    
    工作流程：
    1. 检查每个连接是否已注册
    2. 如果未注册，从数据库查询配置并注册
    3. 返回注册结果
    
    Args:
        connection_names: 需要注册的连接名称集合
        db_session: 数据库会话
    
    Returns:
        Dict[str, bool]: 注册结果字典 {连接名: 是否成功}
        
    Example:
        result = register_required_connections(
            connection_names={"user_db", "analytics_db"},
            db_session=db
        )
        # 返回: {"user_db": True, "analytics_db": True}
    """
    registration_results = {}
    
    # 如果没有需要注册的连接，直接返回
    if not connection_names:
        logger.info("No database connections required for this template")
        return registration_results
    
    logger.info(f"Required database connections: {connection_names}")
    
    for conn_name in connection_names:
        # 检查是否已注册
        if db_connector.is_registered(conn_name):
            logger.info(f"Database connection '{conn_name}' already registered, skipping")
            registration_results[conn_name] = True
            continue
        
        # 未注册，从数据库查询配置
        try:
            db_conn = db_session.query(DBConnection).filter(
                DBConnection.name == conn_name
            ).first()
            
            if not db_conn:
                logger.error(f"Database connection '{conn_name}' not found in configuration")
                registration_results[conn_name] = False
                continue
            
            # 检查连接是否激活
            is_active = getattr(db_conn, "is_active", True)
            if not (is_active is True or (isinstance(is_active, str) and is_active.lower() in ("true", "1"))):
                logger.warning(f"Database connection '{conn_name}' is not active")
                registration_results[conn_name] = False
                continue
            
            # 构建连接URL
            engine_dialects = {
                "postgresql": "postgresql+psycopg2",
                "mysql": "mysql+pymysql",
                "sqlserver": "mssql+pyodbc",
                "oracle": "oracle+cx_oracle"
            }
            
            dialect = engine_dialects.get(db_conn.engine.value, db_conn.engine.value)
            password = db_conn.password_ciphertext  # TODO: Decrypt if encrypted
            
            connection_url = (
                f"{dialect}://{db_conn.username}:{quote_plus(password)}"
                f"@{db_conn.host}:{db_conn.port}/{db_conn.database}"
            )
            
            # 注册连接
            db_connector.register_connection(
                name=db_conn.name,
                connection_url_or_engine=connection_url,
                pool_size=5,
                max_overflow=10
            )
            
            logger.info(f"Successfully registered database connection: {conn_name}")
            registration_results[conn_name] = True
            
        except Exception as e:
            logger.error(f"Failed to register connection '{conn_name}': {str(e)}", exc_info=True)
            registration_results[conn_name] = False
    
    return registration_results


def ensure_connections_registered(
    metadata: Dict[str, VariableMetadata],
    db_session: Session
) -> Dict[str, bool]:
    """
    确保模板所需的所有数据库连接已注册（高层封装函数）
    
    这是一个便捷函数，组合了 extract_required_connections 和 register_required_connections
    
    Args:
        metadata: 变量元数据字典
        db_session: 数据库会话
    
    Returns:
        Dict[str, bool]: 注册结果字典 {连接名: 是否成功}
    
    Example:
        # 在报告生成或修改函数中使用
        result = ensure_connections_registered(
            metadata=template.metadata_json,
            db_session=db
        )
        
        # 检查是否有注册失败的连接
        failed = [name for name, success in result.items() if not success]
        if failed:
            raise Exception(f"Failed to register connections: {failed}")
    """
    # 提取所需连接
    required_connections = extract_required_connections(metadata)
    
    # 按需注册
    return register_required_connections(required_connections, db_session)
