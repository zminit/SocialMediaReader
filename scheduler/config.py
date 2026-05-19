"""Scheduler/Orchestrator 配置。"""

import os
from dataclasses import dataclass


@dataclass
class OrchestratorConfig:
    """Orchestrator 配置。"""

    # Dify 分析请求间隔（秒），避免触发限流
    analyze_delay: float = 1.0

    # 单次采集上限
    max_collect_per_run: int = 50

    # 单次分析上限
    max_analyze_per_run: int = 20

    # 周报最低相关性分数
    report_min_relevance: float = 0.5

    # 报告周期（天）
    report_period_days: int = 7

    @classmethod
    def from_env(cls) -> "OrchestratorConfig":
        return cls(
            analyze_delay=float(
                os.environ.get("ORCHESTRATOR_ANALYZE_DELAY", "1.0")
            ),
            max_collect_per_run=int(
                os.environ.get("ORCHESTRATOR_MAX_COLLECT", "50")
            ),
            max_analyze_per_run=int(
                os.environ.get("ORCHESTRATOR_MAX_ANALYZE", "20")
            ),
            report_min_relevance=float(
                os.environ.get("ORCHESTRATOR_REPORT_MIN_RELEVANCE", "0.5")
            ),
            report_period_days=int(
                os.environ.get("ORCHESTRATOR_REPORT_PERIOD_DAYS", "7")
            ),
        )


@dataclass
class SchedulerConfig:
    """Scheduler 配置。"""

    # 每日采集时间（UTC 小时）
    collect_hour: int = 2

    # 每日分析时间（UTC 小时）
    analyze_hour: int = 4

    # 周报生成日（sun, mon, ...）
    report_day: str = "sun"

    # 周报生成时间（UTC 小时）
    report_hour: int = 6

    # 是否启用定时任务
    enabled: bool = True

    @classmethod
    def from_env(cls) -> "SchedulerConfig":
        return cls(
            collect_hour=int(
                os.environ.get("SCHEDULER_COLLECT_HOUR", "2")
            ),
            analyze_hour=int(
                os.environ.get("SCHEDULER_ANALYZE_HOUR", "4")
            ),
            report_day=os.environ.get("SCHEDULER_REPORT_DAY", "sun"),
            report_hour=int(
                os.environ.get("SCHEDULER_REPORT_HOUR", "6")
            ),
            enabled=os.environ.get("SCHEDULER_ENABLED", "true").lower()
            in ("true", "1", "yes"),
        )
