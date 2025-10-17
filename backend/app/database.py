"""Database configuration and session management"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator
import os

# Database URL from environment or use MySQL
# MySQL format: mysql+pymysql://user:password@host:port/database
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "mysql+pymysql://root:123456@10.10.20.10:24406/md_agent?charset=utf8mb4"
)

# Create engine with appropriate settings
engine_kwargs = {
    "pool_pre_ping": True,  # Enable connection health checks
    "pool_recycle": 3600,   # Recycle connections after 1 hour
    "echo": False,          # Set to True for SQL debugging
}

# Add SQLite-specific settings if using SQLite
if "sqlite" in DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator:
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

