"""Scheduler/Orchestrator 数据模型。

JobCommand: 任务指令（Scheduler/API → Orchestrator）
JobResult: 任务结果
PipelineStats: Pipeline 统计
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class JobCommand:
    """任务指令，由 Scheduler 或 API 构造，发给 Orchestrator 执行。

    对应设计文档 D0 JobCommand。
    """

    job_type: str  # "collect" | "analyze" | "report"
    topic_id: int  # 0 表示所有主题（仅 analyze 支持）

    trigger: str = "cron"  # "cron" | "manual"

    # ---- collect 参数 ----
    time_range: Optional[Tuple[datetime, datetime]] = None
    max_items: int = 50
    keywords_override: Optional[List[str]] = None

    # ---- analyze 参数 ----
    max_analyze: int = 20

    # ---- report 参数 ----
    report_period_days: int = 7
    min_relevance: float = 0.5

    # ---- 通用 ----
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        valid_types = ("collect", "analyze", "report")
        if self.job_type not in valid_types:
            raise ValueError(f"job_type must be one of {valid_types}")

        valid_triggers = ("cron", "manual")
        if self.trigger not in valid_triggers:
            raise ValueError(f"trigger must be one of {valid_triggers}")

        if self.job_type == "collect" and self.topic_id <= 0:
            raise ValueError("collect job requires a positive topic_id")


@dataclass
class PipelineStats:
    """Pipeline 执行统计。"""

    # collect pipeline
    collected: int = 0

    # process pipeline（collect 中包含）
    passed: int = 0
    duplicated: int = 0
    filtered: int = 0

    # analyze pipeline
    analyzed: int = 0
    analysis_failed: int = 0

    # report pipeline
    report_generated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "collected": self.collected,
            "passed": self.passed,
            "duplicated": self.duplicated,
            "filtered": self.filtered,
            "analyzed": self.analyzed,
            "analysis_failed": self.analysis_failed,
            "report_generated": self.report_generated,
        }


@dataclass
class JobResult:
    """任务执行结果。"""

    job_type: str
    topic_id: int
    success: bool
    started_at: datetime
    finished_at: datetime
    stats: PipelineStats = field(default_factory=PipelineStats)
    error: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_type": self.job_type,
            "topic_id": self.topic_id,
            "success": self.success,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "stats": self.stats.to_dict(),
            "error": self.error,
        }
