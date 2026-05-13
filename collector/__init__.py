"""
Collector 模块

负责从外部信息源采集数据，包括：
- GitHub repos 搜索和详情
- 未来扩展：RSS、CSDN、掘金等

职责边界：
- 构造外部查询
- 调用外部 API
- 处理分页、限流、重试
- 单次采集内的基础去重
- 转换成标准 RawItem
- 记录采集上下文和外部元数据

不负责：
- 跨批次去重（由 processor 负责）
- 内容质量判断
- LLM 摘要和分析
"""

from collector.base import BaseCollector
from collector.github_collector import GitHubCollector
from collector.models import SourceQuery, RawItem
from collector.config import CollectorConfig

__all__ = [
    "BaseCollector",
    "GitHubCollector",
    "SourceQuery",
    "RawItem",
    "CollectorConfig",
]
