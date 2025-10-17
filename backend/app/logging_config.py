"""Logging configuration"""
import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

# 日志级别映射
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}

# 彩色日志格式（控制台用）
class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式"""
    
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m',       # 重置
    }
    
    def format(self, record):
        # 添加颜色
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        # 格式化
        result = super().format(record)
        
        # 恢复原始levelname（避免影响其他handler）
        record.levelname = levelname
        
        return result


def setup_logging(log_file: str = "app.log", log_level: str = None):
    """
    配置日志系统
    - 输出到控制台（带颜色）
    - 输出到文件（详细信息）
    - 支持日志轮转
    
    Args:
        log_file: 日志文件名
        log_level: 日志级别，默认从环境变量LOG_LEVEL读取，没有则为INFO
    """
    # 创建日志目录
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_path = log_dir / log_file
    
    # 从环境变量读取日志级别，默认INFO
    if log_level is None:
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    else:
        log_level = log_level.upper()
    
    if log_level not in LOG_LEVELS:
        log_level = 'INFO'
    
    # 配置日志格式
    # 控制台格式（简洁，带颜色）
    console_format = ColoredFormatter(
        '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 文件格式（详细，包含文件位置）
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 获取root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVELS[log_level])
    
    # 清除现有的handlers
    root_logger.handlers.clear()
    
    # 控制台handler - 只显示INFO及以上级别
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    # 文件handler - 显示DEBUG及以上所有级别，支持轮转
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,           # 保留5个备份
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)
    
    # 记录启动信息
    root_logger.info(f"日志系统已初始化 - 级别: {log_level}")
    root_logger.info(f"日志文件: {log_path}")
    root_logger.info(f"控制台日志级别: INFO, 文件日志级别: DEBUG")
    
    return root_logger


# 创建应用专用logger
def get_logger(name: str, level: str = None):
    """
    获取命名logger
    
    Args:
        name: logger名称，通常使用 __name__
        level: 可选的日志级别覆盖
    
    Returns:
        logging.Logger
    """
    logger = logging.getLogger(name)
    
    if level:
        level_value = LOG_LEVELS.get(level.upper(), logging.INFO)
        logger.setLevel(level_value)
    
    return logger

