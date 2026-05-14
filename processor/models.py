"""Processor 数据模型。"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from collector.models import RawItem


@dataclass
class AnalysisInput:
    """发送给 Dify 内容分析工作流的输入。"""

    topic: str
    title: str
    url: str
    description: Optional[str]

    cleaned_content_excerpt: str
    content_length: int

    stars: Optional[int] = None
    forks: Optional[int] = None
    programming_language: Optional[str] = None
    license: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    last_commit_at: Optional[datetime] = None

    activity_score: Optional[float] = None
    initial_quality_score: float = 0.0

    external_id: str = ""
    content_fingerprint: str = ""
    processed_at: Optional[datetime] = None

    def to_dify_payload(self) -> Dict[str, Any]:
        """转换为 Dify 内容分析工作流 payload。"""
        return {
            "topic": self.topic,
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "readme": self.cleaned_content_excerpt,
            "metadata": {
                "stars": self.stars,
                "forks": self.forks,
                "programming_language": self.programming_language,
                "license": self.license,
                "topics": self.topics,
                "last_commit_at": self.last_commit_at.isoformat() if self.last_commit_at else None,
                "activity_score": self.activity_score,
                "initial_quality_score": self.initial_quality_score,
            },
        }


@dataclass
class QualityEvaluation:
    """质量评估结果。"""

    score: float
    hard_filtered: bool
    filter_reason: Optional[str]
    checks: Dict[str, bool]
    score_breakdown: Dict[str, float] = field(default_factory=dict)


@dataclass
class ProcessingResult:
    """单条 RawItem 的处理结果。"""

    status: str  # passed, duplicate, filtered
    analysis_input: Optional[AnalysisInput] = None
    duplicate_info: Optional[Dict[str, Any]] = None
    filter_info: Optional[Dict[str, Any]] = None
    normalized_item: Optional[RawItem] = None
    content_fingerprint: Optional[str] = None

    @classmethod
    def passed(
        cls,
        analysis_input: AnalysisInput,
        fingerprint: str,
        normalized_item: RawItem,
    ) -> "ProcessingResult":
        return cls(
            status="passed",
            analysis_input=analysis_input,
            normalized_item=normalized_item,
            content_fingerprint=fingerprint,
        )

    @classmethod
    def duplicate(
        cls,
        dup_type: str,
        dup_id: int,
        fingerprint: str,
        normalized_item: RawItem,
    ) -> "ProcessingResult":
        return cls(
            status="duplicate",
            duplicate_info={"type": dup_type, "duplicate_source_id": dup_id},
            normalized_item=normalized_item,
            content_fingerprint=fingerprint,
        )

    @classmethod
    def filtered(
        cls,
        reason: str,
        quality_score: float,
        checks: Dict[str, bool],
        normalized_item: RawItem,
        fingerprint: str,
    ) -> "ProcessingResult":
        return cls(
            status="filtered",
            filter_info={
                "reason": reason,
                "quality_score": quality_score,
                "checks": checks,
            },
            normalized_item=normalized_item,
            content_fingerprint=fingerprint,
        )