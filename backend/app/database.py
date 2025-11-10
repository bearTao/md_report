"""
数据库配置和会话管理模块

功能说明：
- 创建数据库连接引擎
- 管理数据库会话的生命周期
- 提供数据库依赖注入功能
- 初始化数据库表结构
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator
import os

# 从环境变量获取数据库URL，如果未设置则使用默认的MySQL连接
# MySQL连接格式: mysql+pymysql://用户名:密码@主机:端口/数据库名?charset=utf8mb4
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "mysql+pymysql://root:123456@10.10.20.10:24406/md_agent?charset=utf8mb4"
)

# 创建数据库引擎的配置参数
engine_kwargs = {
    "pool_pre_ping": True,      # 启用连接健康检查，每次使用前先ping测试
    "pool_recycle": 3600,        # 连接回收时间：1小时后回收（对应MySQL的wait_timeout）
    "pool_size": 5,              # 连接池大小：默认保持5个连接
    "max_overflow": 10,          # 最大溢出连接数（总最大连接数 = pool_size + max_overflow = 15）
    "pool_timeout": 30,          # 从连接池获取连接的超时时间（秒）
    "echo": False,               # 是否输出SQL语句到日志（调试时可设为True）
}

# 如果使用SQLite，添加SQLite专用配置
# check_same_thread=False 允许多线程共享同一个SQLite连接
if "sqlite" in DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

# 创建数据库引擎实例
engine = create_engine(DATABASE_URL, **engine_kwargs)

# 会话工厂：用于创建数据库会话
# autocommit=False: 不自动提交事务，需要显式调用commit
# autoflush=False: 不自动刷新，手动控制数据同步
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ORM模型基类：所有数据库模型都继承自这个类
Base = declarative_base()


def get_db() -> Generator:
    """
    获取数据库会话的依赖函数（FastAPI依赖注入）
    
    功能说明：
    - 创建一个新的数据库会话
    - 使用yield返回会话供请求处理使用
    - 请求结束后自动关闭会话，释放资源
    
    使用示例：
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    
    Returns:
        Generator: 数据库会话生成器
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库表结构
    
    功能说明：
    - 根据所有已定义的ORM模型创建数据库表
    - 如果表已存在则跳过
    - 在应用启动时调用
    
    注意：
    - 这个方法只创建表，不做数据迁移
    - 生产环境建议使用Alembic等迁移工具
    """
    Base.metadata.create_all(bind=engine)

