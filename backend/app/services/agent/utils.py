"""
工具函数和装饰器

本模块提供通用的工具函数和装饰器,用于:
- LLM调用追踪
- 性能监控
- 错误重试
- 时间测量
"""
from typing import Callable, Any, Dict
from functools import wraps
import time
import logging
import asyncio

logger = logging.getLogger(__name__)


class LLMCallTracker:
    """
    LLM调用追踪器
    
    追踪和统计所有LLM调用的性能指标,包括:
    - 调用次数
    - 总成本
    - 平均延迟
    - 成功/失败率
    """
    
    def __init__(self):
        """初始化追踪器"""
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.total_cost_usd = 0.0
        self.total_duration_ms = 0
        self.call_history = []
    
    def track_call(
        self,
        operation: str,
        success: bool,
        duration_ms: int,
        cost_usd: float = 0.0,
        error: str = None
    ):
        """
        记录一次LLM调用
        
        Args:
            operation: 操作名称
            success: 是否成功
            duration_ms: 执行时长(毫秒)
            cost_usd: 成本(美元)
            error: 错误信息(如果失败)
        """
        self.total_calls += 1
        if success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
        
        self.total_cost_usd += cost_usd
        self.total_duration_ms += duration_ms
        
        self.call_history.append({
            "operation": operation,
            "success": success,
            "duration_ms": duration_ms,
            "cost_usd": cost_usd,
            "error": error,
            "timestamp": time.time()
        })
        
        # 只保留最近100条记录
        if len(self.call_history) > 100:
            self.call_history.pop(0)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计字典
        """
        avg_duration = (
            self.total_duration_ms / self.total_calls 
            if self.total_calls > 0 else 0
        )
        
        success_rate = (
            self.successful_calls / self.total_calls * 100
            if self.total_calls > 0 else 0
        )
        
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": round(success_rate, 2),
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_duration_ms": self.total_duration_ms,
            "avg_duration_ms": round(avg_duration, 2),
            "recent_calls": self.call_history[-10:]  # 最近10条
        }
    
    def reset(self):
        """重置所有统计"""
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.total_cost_usd = 0.0
        self.total_duration_ms = 0
        self.call_history = []


# 全局追踪器实例
llm_tracker = LLMCallTracker()


def retry_on_failure(max_retries: int = 3, delay_seconds: float = 1.0):
    """
    失败重试装饰器
    
    自动重试失败的异步函数调用。
    
    Args:
        max_retries: 最大重试次数
        delay_seconds: 重试间隔(秒)
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(
                            f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_retries + 1}): {str(e)}"
                        )
                        await asyncio.sleep(delay_seconds)
                    else:
                        logger.error(
                            f"{func.__name__} 在 {max_retries + 1} 次尝试后仍然失败: {str(e)}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


def measure_time(func: Callable) -> Callable:
    """
    时间测量装饰器
    
    测量异步函数的执行时间并记录日志。
    
    Args:
        func: 要测量的函数
    
    Returns:
        装饰后的函数
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.debug(
                f"{func.__name__} 执行完成, 耗时: {duration_ms}ms"
            )
            
            return result
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"{func.__name__} 执行失败, 耗时: {duration_ms}ms, 错误: {str(e)}"
            )
            raise
    
    return wrapper


def format_duration(duration_ms: int) -> str:
    """
    格式化持续时间
    
    将毫秒数格式化为人类可读的字符串。
    
    Args:
        duration_ms: 持续时间(毫秒)
    
    Returns:
        str: 格式化的字符串
    """
    if duration_ms < 1000:
        return f"{duration_ms}ms"
    elif duration_ms < 60000:
        return f"{duration_ms / 1000:.2f}s"
    else:
        minutes = duration_ms // 60000
        seconds = (duration_ms % 60000) / 1000
        return f"{minutes}m {seconds:.1f}s"


def format_cost(cost_usd: float) -> str:
    """
    格式化成本
    
    将美元金额格式化为可读字符串。
    
    Args:
        cost_usd: 成本(美元)
    
    Returns:
        str: 格式化的字符串
    """
    if cost_usd < 0.01:
        return f"${cost_usd * 1000:.2f}¢"
    else:
        return f"${cost_usd:.4f}"
