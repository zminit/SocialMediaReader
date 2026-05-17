"""Dify 工作流客户端模块。

负责将 Processor 输出的 AnalysisInput 发送给 Dify 内容分析工作流，
并解析 Dify 返回的分析结果。
"""

from .client import DifyClient
from .config import DifyConfig
from .models import AnalysisResult

__all__ = ["DifyClient", "DifyConfig", "AnalysisResult"]
