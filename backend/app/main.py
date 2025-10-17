"""Main FastAPI application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.database import init_db
from app.api import templates, reports, config as config_api
from app.logging_config import setup_logging

# 配置日志 - 默认INFO，可通过环境变量LOG_LEVEL覆盖
logger = setup_logging(log_file="app.log")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("=" * 60)
    logger.info("Application starting...")
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")
    logger.info("Application started and ready to serve requests")
    logger.info("=" * 60)
    yield
    # Shutdown
    logger.info("Application shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Markdown Report Generator API",
    description="P0 Core APIs for report generation platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(templates.router)
app.include_router(reports.router)
app.include_router(config_api.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Markdown Report Generator API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

