"""
数据模型定义

SourceQuery: 采集任务输入
RawItem: 采集结果输出
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple


@dataclass
class SourceQuery:
    """采集任务查询参数"""
    
    topic_id: int
    keywords: List[str]
    source_type: str  # "github", "rss", "csdn", "juejin"
    
    # 时间和数量
    time_range: Optional[Tuple[datetime, datetime]] = None
    max_items: int = 50
    page_size: int = 30
    
    # 排序和过滤
    sort_by: str = "best_match"  # "best_match", "stars", "forks", "updated"
    programming_language: Optional[str] = None  # Python, TypeScript, Go
    content_language: Optional[str] = None  # zh, en（预留给文章采集）
    min_stars: int = 0
    topics: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """验证参数"""
        if not self.keywords:
            raise ValueError("keywords cannot be empty")
        
        valid_source_types = ["github", "rss", "csdn", "juejin"]
        if self.source_type not in valid_source_types:
            raise ValueError(f"source_type must be one of {valid_source_types}")
        
        valid_sort_by = ["best_match", "stars", "forks", "updated", "help-wanted-issues"]
        if self.sort_by not in valid_sort_by:
            raise ValueError(f"sort_by must be one of {valid_sort_by}")
        
        if self.max_items <= 0:
            raise ValueError("max_items must be positive")
        
        if self.page_size <= 0 or self.page_size > 100:
            raise ValueError("page_size must be between 1 and 100")


@dataclass
class RawItem:
    """采集的原始数据项"""
    
    # 基础标识
    topic_id: int
    source_type: str  # "github", "rss", "csdn"
    source_subtype: str  # "github_repo", "github_release", "article"
    external_id: str  # "github:owner/repo", "rss:article_id"
    
    # URL 和标题
    url: str  # 原始 URL
    canonical_url: str  # 规范化 URL
    title: str
    author: str
    description: Optional[str]
    
    # 时间戳
    published_at: Optional[datetime]
    collected_at: datetime
    
    # 内容
    raw_text: Optional[str]  # README 或正文
    raw_text_truncated: bool  # 是否被截断
    raw_text_length: int  # 原始长度
    
    # 元数据（source_type 特定的数据）
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 采集上下文
    query_keyword: Optional[str] = None  # 命中的关键词
    rank: Optional[int] = None  # 在搜索结果中的排名
    collected_by: str = "unknown_collector"
    
    # 调试用（可选，开发期保留）
    raw_payload: Optional[Dict] = None
    
    def __post_init__(self):
        """验证必填字段"""
        if not self.external_id:
            raise ValueError("external_id is required")
        if not self.url:
            raise ValueError("url is required")
        if not self.title:
            raise ValueError("title is required")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "topic_id": self.topic_id,
            "source_type": self.source_type,
            "source_subtype": self.source_subtype,
            "external_id": self.external_id,
            "url": self.url,
            "canonical_url": self.canonical_url,
            "title": self.title,
            "author": self.author,
            "description": self.description,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "collected_at": self.collected_at.isoformat(),
            "raw_text": self.raw_text,
            "raw_text_truncated": self.raw_text_truncated,
            "raw_text_length": self.raw_text_length,
            "metadata": self.metadata,
            "query_keyword": self.query_keyword,
            "rank": self.rank,
            "collected_by": self.collected_by,
            "raw_payload": self.raw_payload,
        }
