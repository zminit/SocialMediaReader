"""Scheduler — APScheduler 封装。

管理定时任务（每日采集、每日分析、每周报告），
也支持 API 手动触发。
"""

import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import SchedulerConfig
from .models import JobCommand, JobResult
from .orchestrator import Orchestrator

logger = logging.getLogger(__name__)


class Scheduler:
    """定时调度器，基于 APScheduler BackgroundScheduler。

    Usage:
        scheduler = Scheduler(orchestrator, config)
        scheduler.start()        # 注册定时任务并启动
        scheduler.shutdown()     # 关闭

        # API 手动触发
        result = scheduler.trigger_manual(JobCommand(...))
    """

    def __init__(
        self,
        orchestrator: Orchestrator,
        config: SchedulerConfig,
    ):
        self.orchestrator = orchestrator
        self.config = config
        self._scheduler: Optional[BackgroundScheduler] = None

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """启动调度器并注册默认定时任务。"""
        if not self.config.enabled:
            logger.info("Scheduler is disabled by config")
            return

        self._scheduler = BackgroundScheduler()
        self._setup_default_jobs()
        self._scheduler.start()
        logger.info("Scheduler started")

    def shutdown(self, wait: bool = True) -> None:
        """关闭调度器。"""
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=wait)
            logger.info("Scheduler shut down")

    @property
    def running(self) -> bool:
        return self._scheduler is not None and self._scheduler.running

    # ------------------------------------------------------------------ #
    #  手动触发
    # ------------------------------------------------------------------ #

    def trigger_manual(self, command: JobCommand) -> JobResult:
        """API 手动触发任务，同步执行并返回结果。"""
        command.trigger = "manual"
        logger.info(
            "Manual trigger: type=%s, topic_id=%d",
            command.job_type,
            command.topic_id,
        )
        return self.orchestrator.execute(command)

    # ------------------------------------------------------------------ #
    #  定时任务注册
    # ------------------------------------------------------------------ #

    def _setup_default_jobs(self) -> None:
        """注册默认的定时任务。"""
        if self._scheduler is None:
            return

        # 每日采集
        self._scheduler.add_job(
            self._daily_collect,
            CronTrigger(hour=self.config.collect_hour, minute=0),
            id="daily_collect",
            name="Daily Collect",
            replace_existing=True,
        )
        logger.info(
            "Registered daily_collect at UTC %02d:00", self.config.collect_hour
        )

        # 每日分析
        self._scheduler.add_job(
            self._daily_analyze,
            CronTrigger(hour=self.config.analyze_hour, minute=0),
            id="daily_analyze",
            name="Daily Analyze",
            replace_existing=True,
        )
        logger.info(
            "Registered daily_analyze at UTC %02d:00", self.config.analyze_hour
        )

        # 每周报告
        self._scheduler.add_job(
            self._weekly_report,
            CronTrigger(
                day_of_week=self.config.report_day,
                hour=self.config.report_hour,
                minute=0,
            ),
            id="weekly_report",
            name="Weekly Report",
            replace_existing=True,
        )
        logger.info(
            "Registered weekly_report on %s at UTC %02d:00",
            self.config.report_day,
            self.config.report_hour,
        )

    # ------------------------------------------------------------------ #
    #  定时任务实现
    # ------------------------------------------------------------------ #

    def _daily_collect(self) -> None:
        """每日采集所有活跃主题。"""
        logger.info("Starting daily collect")
        topics = self.orchestrator.topic_repo.list_topics()

        if not topics:
            logger.info("No topics configured, skipping daily collect")
            return

        for topic in topics:
            command = JobCommand(
                job_type="collect",
                topic_id=topic["id"],
                trigger="cron",
            )
            try:
                result = self.orchestrator.execute(command)
                logger.info(
                    "Daily collect for topic %d (%s): success=%s, stats=%s",
                    topic["id"],
                    topic["name"],
                    result.success,
                    result.stats.to_dict(),
                )
            except Exception as e:
                logger.error(
                    "Daily collect failed for topic %d (%s): %s",
                    topic["id"],
                    topic["name"],
                    e,
                )

    def _daily_analyze(self) -> None:
        """每日分析所有 pending 内容。"""
        logger.info("Starting daily analyze")
        command = JobCommand(
            job_type="analyze",
            topic_id=0,  # 0 表示所有主题
            trigger="cron",
        )
        try:
            result = self.orchestrator.execute(command)
            logger.info(
                "Daily analyze: success=%s, stats=%s",
                result.success,
                result.stats.to_dict(),
            )
        except Exception as e:
            logger.error("Daily analyze failed: %s", e)

    def _weekly_report(self) -> None:
        """每周生成报告。"""
        logger.info("Starting weekly report generation")
        topics = self.orchestrator.topic_repo.list_topics()

        if not topics:
            logger.info("No topics configured, skipping weekly report")
            return

        for topic in topics:
            command = JobCommand(
                job_type="report",
                topic_id=topic["id"],
                trigger="cron",
            )
            try:
                result = self.orchestrator.execute(command)
                logger.info(
                    "Weekly report for topic %d (%s): success=%s",
                    topic["id"],
                    topic["name"],
                    result.success,
                )
            except Exception as e:
                logger.error(
                    "Weekly report failed for topic %d (%s): %s",
                    topic["id"],
                    topic["name"],
                    e,
                )
