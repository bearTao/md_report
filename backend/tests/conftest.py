"""Pytest configuration and fixtures"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（从 backend 目录）
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from app.database import Base, get_db
# 导入所有模型以确保它们注册到 Base.metadata 中（必须在导入 app.main 之前）
from app.models import db_models  # noqa: F401
from app.main import app


# 测试数据库配置
# 默认使用 SQLite (快速单元测试)，可通过环境变量切换到 PostgreSQL (集成测试)
if os.getenv("INTEGRATION_TEST") or os.getenv("CI"):
    # 集成测试：使用 PostgreSQL
    TEST_DB_HOST = os.getenv("TEST_DB_HOST", "10.10.20.10")
    TEST_DB_PORT = os.getenv("TEST_DB_PORT", "14632")
    TEST_DB_USER = os.getenv("TEST_DB_USER", "microgrid")
    TEST_DB_PASSWORD = os.getenv("TEST_DB_PASSWORD", "microgrid123")
    TEST_DB_NAME = os.getenv("TEST_DB_NAME", "new_md_agent_test")
    SQLALCHEMY_DATABASE_URL = f"postgresql://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:{TEST_DB_PORT}/{TEST_DB_NAME}"
else:
    # 单元测试：使用 SQLite 临时文件数据库（在测试之间共享表定义）
    import tempfile
    test_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    test_db_file.close()
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{test_db_file.name}"

# 创建引擎配置
engine_kwargs = {
    "poolclass": NullPool,  # 不使用连接池，测试时每次创建新连接
    "echo": False
}

# SQLite 需要额外配置
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)

# 在创建引擎后立即创建所有表（只创建一次）
Base.metadata.create_all(bind=engine)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    # Create tables if not exist
    # 注意：对于 SQLite 内存数据库，表只需创建一次，但为了兼容性每次测试都创建
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        # Cleanup: truncate all tables after each test
        db.rollback()
        
        # 根据数据库类型使用不同的清理策略
        dialect_name = engine.dialect.name
        
        if dialect_name == "sqlite":
            # SQLite: 使用 DELETE (内存数据库，速度快)
            for table in reversed(Base.metadata.sorted_tables):
                try:
                    db.execute(text(f"DELETE FROM {table.name}"))
                except Exception:
                    # 表可能不存在，忽略错误
                    pass
        elif dialect_name == "postgresql":
            # PostgreSQL: 使用 TRUNCATE
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(text(f"TRUNCATE TABLE {table.name} RESTART IDENTITY CASCADE"))
        elif dialect_name == "mysql":
            # MySQL: 使用 TRUNCATE 并禁用外键检查
            db.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(text(f"TRUNCATE TABLE {table.name}"))
            db.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        
        db.commit()
        db.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database session override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_template_data():
    """Sample template data for testing"""
    return {
        "name": "Test Template",
        "description": "A test template",
        "template_content": "# {{title}}\n\nContent: {{content}}",
        "metadata": {
            "title": {
                "type": "string",
                "source": "user_input",
                "required": True,
                "description": "Title"
            },
            "content": {
                "type": "string",
                "source": "user_input",
                "required": True,
                "description": "Content"
            }
        }
    }


@pytest.fixture
def sample_template_with_system(sample_template_data):
    """Template with system variables"""
    template_data = sample_template_data.copy()
    template_data["template_content"] = """# {{title}}

Generated: {{generated_at}}

{{content}}
"""
    template_data["metadata"]["generated_at"] = {
        "type": "string",
        "source": "system",
        "required": True,
        "description": "Generation timestamp",
        "system_config": {
            "fields": {
                "timestamp": {
                    "generator": "datetime",
                    "format": "%Y-%m-%d %H:%M:%S"
                }
            }
        }
    }
    return template_data

