"""
FastAPI主应用程序入口

功能说明：
- 初始化FastAPI应用
- 配置CORS跨域中间件
- 注册所有API路由
- 管理应用生命周期（启动和关闭）
- 初始化数据库连接
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.database import init_db
from app.api import templates, reports, config as config_api, websocket, db_connections, debug
from app.logging_config import setup_logging

# 配置日志系统 - 默认INFO级别，可通过环境变量LOG_LEVEL覆盖
logger = setup_logging(log_file="app.log")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器
    
    功能说明：
    - 应用启动时执行初始化操作（数据库、连接池等）
    - 应用关闭时执行清理操作
    - 使用异步上下文管理器确保资源正确释放
    
    执行时机：
    - yield之前：应用启动时执行
    - yield之后：应用关闭时执行
    """
    # 启动阶段
    logger.info("=" * 60)
    logger.info("Application starting...")
    logger.info("Initializing database...")
    init_db()  # 初始化数据库表结构
    logger.info("Database initialized successfully")
    logger.info("Application started and ready to serve requests")
    logger.info("=" * 60)
    yield
    # 关闭阶段
    logger.info("Application shutting down...")


# 创建FastAPI应用实例
app = FastAPI(
    title="Markdown Report Generator API",
    description="P0 Core APIs for report generation platform",
    version="1.0.0",
    lifespan=lifespan  # 绑定生命周期管理器
)

# 添加CORS跨域中间件
# 允许前端从不同域名访问API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源（生产环境应指定具体域名）
    allow_credentials=True,  # 允许携带凭证（cookies等）
    allow_methods=["*"],  # 允许所有HTTP方法（GET、POST等）
    allow_headers=["*"],  # 允许所有请求头
)

# 注册所有API路由模块
app.include_router(templates.router)  # 模板管理API
app.include_router(reports.router)  # 报告生成API
app.include_router(config_api.router)  # 配置管理API
app.include_router(websocket.router)  # WebSocket实时通信API
app.include_router(db_connections.router)  # 数据库连接管理API
app.include_router(debug.router)  # 调试工具API


@app.get("/")
async def root():
    """
    根路径接口
    
    返回API的基本信息和运行状态
    """
    return {
        "name": "Markdown Report Generator API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """
    健康检查接口
    
    用于监控系统检查服务是否正常运行
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

