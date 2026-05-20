"""统一日志配置模块。

Usage:
    from logging_config import setup_logging
    setup_logging()  # 在应用启动时调用一次
"""

from .config import LogConfig
from .setup import setup_logging

__all__ = ["setup_logging", "LogConfig"]
