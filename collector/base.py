"""
BaseCollector 抽象基类

定义所有 collector 的通用接口
"""

from abc import ABC, abstractmethod
from typing import Iterable, Dict, Any

from collector.models import SourceQuery, RawItem
from collector.config import CollectorConfig


class BaseCollector(ABC):
    """采集器抽象基类"""
    
    def __init__(self, config: CollectorConfig):
        self.config = config
    
    @abstractmethod
    def collect(self, query: SourceQuery) -> Iterable[RawItem]:
        """
        执行采集任务
        
        Args:
            query: 采集查询参数
        
        Returns:
            RawItem 迭代器，支持流式处理
        
        Raises:
            CollectorError: 采集失败
            RateLimitExceeded: 速率限制超出
        """
        pass
    
    def validate_config(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            配置是否有效
        """
        return self.config.validate()
    
    @abstractmethod
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        获取速率限制状态
        
        Returns:
            包含 remaining, limit, reset_at 等信息的字典
        """
        pass
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(config={self.config})"


class CollectorError(Exception):
    """采集器通用错误"""
    pass


class RateLimitExceeded(CollectorError):
    """速率限制超出"""
    pass


class AuthenticationError(CollectorError):
    """认证失败"""
    pass


class ResourceNotFound(CollectorError):
    """资源不存在"""
    pass
