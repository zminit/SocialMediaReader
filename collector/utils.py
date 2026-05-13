"""
工具函数

包括重试、限流、日志等通用功能
"""

import time
import logging
from typing import Callable, Tuple, Type, Any
from functools import wraps

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("collector")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    指数退避重试装饰器
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exceptions: 需要重试的异常类型
    
    Example:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def fetch_data():
            # 可能失败的操作
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries - 1:
                        # 最后一次尝试失败，抛出异常
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts: {e}"
                        )
                        raise
                    
                    # 计算延迟时间（指数退避）
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(
                        f"{func.__name__} attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
            
            # 理论上不会到这里，但为了类型检查
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def parse_github_datetime(dt_str: str) -> Any:
    """
    解析 GitHub API 返回的时间字符串
    
    Args:
        dt_str: ISO 8601 格式的时间字符串
    
    Returns:
        datetime 对象
    """
    from datetime import datetime
    
    if not dt_str:
        return None
    
    try:
        # GitHub 返回的格式：2026-05-13T12:34:56Z
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse datetime '{dt_str}': {e}")
        return None


def truncate_text(text: str, max_length: int = 5000) -> Tuple[str, bool, int]:
    """
    截断文本并返回元数据
    
    Args:
        text: 原始文本
        max_length: 最大长度
    
    Returns:
        (截断后的文本, 是否被截断, 原始长度)
    """
    if not text:
        return "", False, 0
    
    original_length = len(text)
    truncated = original_length > max_length
    
    if truncated:
        return text[:max_length], True, original_length
    else:
        return text, False, original_length


def sanitize_url(url: str) -> str:
    """
    规范化 URL
    
    Args:
        url: 原始 URL
    
    Returns:
        规范化后的 URL
    """
    if not url:
        return ""
    
    # 移除尾部斜杠
    url = url.rstrip('/')
    
    # 统一使用 https
    if url.startswith('http://'):
        url = url.replace('http://', 'https://', 1)
    
    return url


def calculate_activity_score(
    pushed_at_days: int,
    stars: int,
    has_recent_activity: bool
) -> float:
    """
    计算活跃度评分（V0 简化版）
    
    Args:
        pushed_at_days: 距离最后推送的天数
        stars: Star 数量
        has_recent_activity: 是否有近期活动（90 天内）
    
    Returns:
        活跃度评分（0-1）
    """
    import math
    
    # 1. 推送新鲜度（0-1）
    push_freshness = max(0, 1 - pushed_at_days / 365)
    
    # 2. Stars 权重（对数归一化，0-1）
    stars_weight = min(1.0, math.log10(stars + 1) / 5)
    
    # 3. 近期活动（0 或 1）
    recent_activity = 1.0 if has_recent_activity else 0.0
    
    # V0 简化权重
    score = (
        push_freshness * 0.5 +      # 推送新鲜度 50%
        stars_weight * 0.3 +         # Stars 权重 30%
        recent_activity * 0.2        # 近期活动 20%
    )
    
    return round(score, 3)


def set_log_level(level: str):
    """
    设置日志级别
    
    Args:
        level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    logger.setLevel(numeric_level)
