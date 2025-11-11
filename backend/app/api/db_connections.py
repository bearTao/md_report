"""Database connection management API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import uuid
from datetime import datetime, timezone

from app.database import get_db
from app.models.db_models import DBConnection, DBEngineType
from app.schemas.api_schemas import (
    DBConnectionCreate, DBConnectionUpdate, DBConnectionResponse,
    DBConnectionListResponse, DBConnectionListItem, DBConnectionTestResponse,
    DBEngineEnum
)

router = APIRouter(prefix="/api/config/db-connections", tags=["database-connections"])


@router.get("/", response_model=DBConnectionListResponse)
async def list_db_connections(
    db: Session = Depends(get_db)
):
    """Get list of database connections"""
    connections = db.query(DBConnection).order_by(DBConnection.created_at.desc()).all()
    
    items = [
        DBConnectionListItem(
            id=conn.id,
            name=conn.name,
            engine=DBEngineEnum(conn.engine.value),
            host=conn.host,
            port=conn.port,
            database=conn.database,
            is_active=conn.is_active == "true",
            created_at=conn.created_at
        )
        for conn in connections
    ]
    
    return DBConnectionListResponse(items=items, total=len(items))


@router.post("/", response_model=DBConnectionResponse, status_code=201)
async def create_db_connection(
    request: DBConnectionCreate,
    db: Session = Depends(get_db)
):
    """Create a new database connection"""
    # Check if name already exists
    existing = db.query(DBConnection).filter(DBConnection.name == request.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Connection name '{request.name}' already exists")
    
    # Create connection
    conn_id = f"dbconn_{uuid.uuid4().hex[:12]}"
    
    # For P1, store password in plaintext (should encrypt in production)
    connection = DBConnection(
        id=conn_id,
        name=request.name,
        engine=DBEngineType(request.engine.value),
        host=request.host,
        port=request.port,
        database=request.database,
        username=request.username,
        password_ciphertext=request.password,  # TODO: Encrypt password
        options_json=request.options,
        is_active="true" if request.is_active else "false"
    )
    
    db.add(connection)
    db.commit()
    db.refresh(connection)
    
    return DBConnectionResponse(
        id=connection.id,
        name=connection.name,
        engine=DBEngineEnum(connection.engine.value),
        host=connection.host,
        port=connection.port,
        database=connection.database,
        username=connection.username,
        options=connection.options_json,
        is_active=connection.is_active == "true",
        created_at=connection.created_at,
        updated_at=connection.updated_at
    )


@router.get("/{connection_id}", response_model=DBConnectionResponse)
async def get_db_connection(
    connection_id: str,
    db: Session = Depends(get_db)
):
    """Get database connection by ID"""
    connection = db.query(DBConnection).filter(DBConnection.id == connection_id).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Database connection not found")
    
    return DBConnectionResponse(
        id=connection.id,
        name=connection.name,
        engine=DBEngineEnum(connection.engine.value),
        host=connection.host,
        port=connection.port,
        database=connection.database,
        username=connection.username,
        options=connection.options_json,
        is_active=connection.is_active == "true",
        created_at=connection.created_at,
        updated_at=connection.updated_at
    )


@router.put("/{connection_id}", response_model=DBConnectionResponse)
async def update_db_connection(
    connection_id: str,
    request: DBConnectionUpdate,
    db: Session = Depends(get_db)
):
    """Update database connection"""
    connection = db.query(DBConnection).filter(DBConnection.id == connection_id).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Database connection not found")
    
    # Check if new name conflicts with existing
    if request.name and request.name != connection.name:
        existing = db.query(DBConnection).filter(DBConnection.name == request.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Connection name '{request.name}' already exists")
    
    # Update fields
    if request.name is not None:
        connection.name = request.name
    if request.engine is not None:
        connection.engine = DBEngineType(request.engine.value)
    if request.host is not None:
        connection.host = request.host
    if request.port is not None:
        connection.port = request.port
    if request.database is not None:
        connection.database = request.database
    if request.username is not None:
        connection.username = request.username
    if request.password is not None:
        connection.password_ciphertext = request.password  # TODO: Encrypt
    if request.options is not None:
        connection.options_json = request.options
    if request.is_active is not None:
        connection.is_active = "true" if request.is_active else "false"
    
    connection.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(connection)
    
    return DBConnectionResponse(
        id=connection.id,
        name=connection.name,
        engine=DBEngineEnum(connection.engine.value),
        host=connection.host,
        port=connection.port,
        database=connection.database,
        username=connection.username,
        options=connection.options_json,
        is_active=connection.is_active == "true",
        created_at=connection.created_at,
        updated_at=connection.updated_at
    )


@router.delete("/{connection_id}", status_code=204)
async def delete_db_connection(
    connection_id: str,
    db: Session = Depends(get_db)
):
    """Delete database connection"""
    connection = db.query(DBConnection).filter(DBConnection.id == connection_id).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Database connection not found")
    
    db.delete(connection)
    db.commit()
    
    return None


@router.post("/{connection_id}/test", response_model=DBConnectionTestResponse)
async def test_db_connection(
    connection_id: str,
    db: Session = Depends(get_db)
):
    """Test database connection"""
    connection = db.query(DBConnection).filter(DBConnection.id == connection_id).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Database connection not found")
    
    # Build connection URL
    engine_dialects = {
        "postgresql": "postgresql+psycopg2",
        "mysql": "mysql+pymysql",
        "sqlserver": "mssql+pyodbc",
        "oracle": "oracle+cx_oracle"
    }
    
    dialect = engine_dialects.get(connection.engine.value, connection.engine.value)
    password = connection.password_ciphertext  # TODO: Decrypt
    
    from urllib.parse import quote_plus
    connection_url = f"{dialect}://{connection.username}:{quote_plus(password)}@{connection.host}:{connection.port}/{connection.database}"
    
    # Try to connect
    try:
        from sqlalchemy import create_engine, text
        test_engine = create_engine(connection_url, pool_pre_ping=True)
        
        with test_engine.connect() as conn:
            # Execute a simple query
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        test_engine.dispose()
        
        return DBConnectionTestResponse(
            success=True,
            message="Connection successful",
            details={
                "host": connection.host,
                "port": connection.port,
                "database": connection.database,
                "engine": connection.engine.value
            }
        )
    
    except Exception as e:
        return DBConnectionTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}",
            details={
                "error": str(e),
                "error_type": type(e).__name__
            }
        )

