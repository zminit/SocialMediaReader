"""API 模块

FastAPI HTTP 接口层，提供 REST API 用于：
- 主题 CRUD
- 采集内容查询
- 分析结果查询
- 手动触发任务
- 系统统计与健康检查
"""

from .config import APIConfig

__all__ = [
    "APIConfig",
]
