"""Orchestrator — 流程编排核心。

串联 Collector → Processor → DifyClient → Storage，驱动三条 Pipeline：
1. Collect: 采集 + 处理 + 入库
2. Analyze: Dify 内容分析
3. Report: 周报生成（预留）
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import List

from collector.base import BaseCollector, CollectorError
from collector.models import RawItem, SourceQuery
from dify_client.client import DifyClient
from dify_client.models import AnalysisResult
from processor.models import ProcessingResult
from processor.processor import Processor
from storage.analysis_repository import SQLiteAnalysisResultRepository
from storage.duplicate_repository import SQLiteDuplicateRecordRepository
from storage.filtered_repository import SQLiteFilteredRecordRepository
from storage.source_repository import SQLiteSourceRepository
from storage.topic_repository import SQLiteTopicRepository

from .config import OrchestratorConfig
from .models import JobCommand, JobResult, PipelineStats

logger = logging.getLogger(__name__)


class Orchestrator:
    """流程编排器，驱动采集 → 处理 → 分析 → 报告全流程。

    所有 Storage 写操作只在 Orchestrator 中发生，
    Processor 只做只读查询（DedupRepository / TopicRepository）。
    """

    def __init__(
        self,
        collector: BaseCollector,
        processor: Processor,
        dify_client: DifyClient,
        source_repo: SQLiteSourceRepository,
        topic_repo: SQLiteTopicRepository,
        duplicate_repo: SQLiteDuplicateRecordRepository,
        filtered_repo: SQLiteFilteredRecordRepository,
        analysis_repo: SQLiteAnalysisResultRepository,
        config: OrchestratorConfig,
    ):
        self.collector = collector
        self.processor = processor
        self.dify_client = dify_client
        self.source_repo = source_repo
        self.topic_repo = topic_repo
        self.duplicate_repo = duplicate_repo
        self.filtered_repo = filtered_repo
        self.analysis_repo = analysis_repo
        self.config = config

    # ------------------------------------------------------------------ #
    #  统一入口
    # ------------------------------------------------------------------ #

    def execute(self, command: JobCommand) -> JobResult:
        """根据 job_type 路由到对应 Pipeline。"""
        logger.info(
            "Executing job: type=%s, topic_id=%d, trigger=%s",
            command.job_type,
            command.topic_id,
            command.trigger,
        )

        if command.job_type == "collect":
            return self.run_collect(command)
        elif command.job_type == "analyze":
            return self.run_analyze(command)
        elif command.job_type == "report":
            return self.run_report(command)
        else:
            raise ValueError(f"Unknown job type: {command.job_type}")

    # ------------------------------------------------------------------ #
    #  Pipeline 1: Collect（采集 + 处理 + 入库）
    # ------------------------------------------------------------------ #

    def run_collect(self, command: JobCommand) -> JobResult:
        """采集 Pipeline。

        流程：
        1. 从 TopicRepository 获取 topic（name + keywords）
        2. 构造 SourceQuery → Collector.collect() → [RawItem]
        3. Processor.process_batch() → [ProcessingResult]
        4. 按 status 分别写入 sources / duplicate_records / filtered_records
        """
        started_at = datetime.now(timezone.utc)
        stats = PipelineStats()

        try:
            # 1. 获取 topic 信息
            topic = self.topic_repo.get_topic(command.topic_id)
            if topic is None:
                return self._fail(command, started_at, f"Topic not found: {command.topic_id}")

            keywords = command.keywords_override or topic.get("keywords", [])
            if not keywords:
                return self._fail(command, started_at, f"No keywords for topic {command.topic_id}")

            # 2. 构造 SourceQuery 并采集
            query = SourceQuery(
                topic_id=command.topic_id,
                keywords=keywords,
                source_type="github",
                time_range=command.time_range,
                max_items=min(command.max_items, self.config.max_collect_per_run),
            )

            logger.info(
                "Collecting for topic '%s' with keywords %s",
                topic["name"],
                keywords,
            )

            raw_items: List[RawItem] = list(self.collector.collect(query))
            stats.collected = len(raw_items)
            logger.info("Collected %d items", stats.collected)

            if not raw_items:
                return self._succeed(command, started_at, stats)

            # 3. Processor 处理
            results: List[ProcessingResult] = self.processor.process_batch(raw_items)

            # 4. 按 status 写入 Storage
            now = datetime.now(timezone.utc)
            for result in results:
                try:
                    self._persist_processing_result(result, now)
                    if result.status == "passed":
                        stats.passed += 1
                    elif result.status == "duplicate":
                        stats.duplicated += 1
                    elif result.status == "filtered":
                        stats.filtered += 1
                except Exception as e:
                    logger.error(
                        "Failed to persist result (status=%s): %s",
                        result.status,
                        e,
                    )

            return self._succeed(command, started_at, stats)

        except CollectorError as e:
            logger.error("Collector error: %s", e)
            return self._fail(command, started_at, f"Collector error: {e}")
        except Exception as e:
            logger.exception("Unexpected error in collect pipeline")
            return self._fail(command, started_at, f"Unexpected error: {e}")

    def _persist_processing_result(
        self,
        result: ProcessingResult,
        processed_at: datetime,
    ) -> None:
        """将单条 ProcessingResult 写入对应的 Storage 表。"""
        item = result.normalized_item
        if item is None:
            return

        if result.status == "passed" and result.analysis_input is not None:
            self.source_repo.create_source(
                topic_id=item.topic_id,
                source_type=item.source_type,
                source_subtype=item.source_subtype,
                external_id=item.external_id,
                url=item.url,
                canonical_url=item.canonical_url,
                title=item.title,
                author=item.author,
                description=item.description,
                published_at=item.published_at,
                collected_at=item.collected_at,
                processed_at=processed_at,
                raw_text=item.raw_text,
                raw_text_truncated=item.raw_text_truncated,
                raw_text_length=item.raw_text_length,
                cleaned_content_excerpt=result.analysis_input.cleaned_content_excerpt,
                content_fingerprint=result.content_fingerprint or "",
                metadata=item.metadata,
                initial_quality_score=result.analysis_input.initial_quality_score,
                status="pending_analysis",
            )

        elif result.status == "duplicate" and result.duplicate_info:
            self.duplicate_repo.create_duplicate_record(
                topic_id=item.topic_id,
                duplicate_type=result.duplicate_info.get("type", "unknown"),
                duplicate_source_id=result.duplicate_info.get("duplicate_source_id", 0),
                external_id=item.external_id,
                url=item.url,
                canonical_url=item.canonical_url,
                title=item.title,
                content_fingerprint=result.content_fingerprint or "",
                collected_at=item.collected_at,
                metadata=item.metadata,
            )

        elif result.status == "filtered" and result.filter_info:
            self.filtered_repo.create_filtered_record(
                topic_id=item.topic_id,
                filter_reason=result.filter_info.get("reason", "unknown"),
                quality_score=result.filter_info.get("quality_score", 0.0),
                checks=result.filter_info.get("checks"),
                external_id=item.external_id,
                url=item.url,
                canonical_url=item.canonical_url,
                title=item.title,
                content_fingerprint=result.content_fingerprint or "",
                collected_at=item.collected_at,
                metadata=item.metadata,
            )

    # ------------------------------------------------------------------ #
    #  Pipeline 2: Analyze（Dify 内容分析）
    # ------------------------------------------------------------------ #

    def run_analyze(self, command: JobCommand) -> JobResult:
        """分析 Pipeline。

        流程：
        1. 查询 status="pending_analysis" 的 sources
        2. 逐条调用 DifyClient.analyze()
        3. 成功 → save_analysis_result + update_status("analyzed")
           失败 → update_status("analysis_failed")
        """
        started_at = datetime.now(timezone.utc)
        stats = PipelineStats()

        try:
            # 1. 获取待分析内容
            max_analyze = min(command.max_analyze, self.config.max_analyze_per_run)

            if command.topic_id > 0:
                pending = self.source_repo.get_sources_by_topic(
                    topic_id=command.topic_id,
                    status="pending_analysis",
                    limit=max_analyze,
                )
            else:
                # topic_id=0 表示处理所有主题
                pending = self.source_repo.get_sources_by_status(
                    status="pending_analysis",
                    limit=max_analyze,
                )

            if not pending:
                logger.info("No pending items to analyze")
                return self._succeed(command, started_at, stats)

            logger.info("Found %d items to analyze", len(pending))

            # 2. 逐条分析
            for i, source in enumerate(pending):
                source_id = source["id"]
                title = source.get("title", "")[:50]

                try:
                    logger.info(
                        "Analyzing %d/%d: [%d] %s",
                        i + 1,
                        len(pending),
                        source_id,
                        title,
                    )

                    # 构造 AnalysisInput（从 source 记录重建）
                    analysis_input = self._build_analysis_input_from_source(source)
                    result: AnalysisResult = self.dify_client.analyze(analysis_input)

                    if result.succeeded:
                        # 保存分析结果
                        self.analysis_repo.save_analysis_result(
                            source_id=source_id,
                            workflow_run_id=result.workflow_run_id,
                            summary=result.summary,
                            relevance_score=result.relevance_score,
                            quality_score=result.quality_score,
                            tags=result.tags,
                            raw_response=result.raw_response,
                            analyzed_at=result.analyzed_at or datetime.now(timezone.utc),
                        )
                        self.source_repo.update_status(source_id, "analyzed")
                        stats.analyzed += 1
                    else:
                        logger.warning(
                            "Dify analysis failed for source %d: %s",
                            source_id,
                            result.error,
                        )
                        self.source_repo.update_status(source_id, "analysis_failed")
                        stats.analysis_failed += 1

                    # 请求间隔
                    if i < len(pending) - 1 and self.config.analyze_delay > 0:
                        time.sleep(self.config.analyze_delay)

                except Exception as e:
                    logger.error(
                        "Error analyzing source %d: %s", source_id, e
                    )
                    self.source_repo.update_status(source_id, "analysis_failed")
                    stats.analysis_failed += 1

            return self._succeed(command, started_at, stats)

        except Exception as e:
            logger.exception("Unexpected error in analyze pipeline")
            return self._fail(command, started_at, f"Unexpected error: {e}")

    def _build_analysis_input_from_source(self, source: dict):
        """从 source 记录重建 AnalysisInput。

        这是因为 Processor 产生的 AnalysisInput 在 collect 阶段没有保存为独立对象，
        而是把关键字段存在了 sources 表中。分析阶段需要从 source 记录中重建。
        """
        from processor.models import AnalysisInput

        metadata = source.get("metadata", {})
        topic_name = self.topic_repo.get_name(source["topic_id"])

        return AnalysisInput(
            topic=topic_name,
            title=source.get("title", ""),
            url=source.get("url", ""),
            description=source.get("description"),
            cleaned_content_excerpt=source.get("cleaned_content_excerpt", ""),
            content_length=source.get("raw_text_length", 0),
            stars=metadata.get("stars"),
            forks=metadata.get("forks"),
            programming_language=metadata.get("primary_language")
            or metadata.get("programming_language"),
            license=metadata.get("license"),
            topics=metadata.get("topics", []),
            last_commit_at=None,  # TODO: 从 metadata 中解析
            activity_score=metadata.get("activity_score"),
            initial_quality_score=source.get("initial_quality_score", 0.0),
            external_id=source.get("external_id", ""),
            content_fingerprint=source.get("content_fingerprint", ""),
        )

    # ------------------------------------------------------------------ #
    #  Pipeline 3: Report（周报生成 — 预留）
    # ------------------------------------------------------------------ #

    def run_report(self, command: JobCommand) -> JobResult:
        """周报生成 Pipeline（预留）。

        流程：
        1. 计算报告周期 period_start / period_end
        2. 从 AnalysisResultRepository 获取高分分析结果
        3. 构造 ReportInput 发送给 Dify 周报工作流
        4. 保存报告

        注意：需要 reports 表和 Dify 周报工作流，当前返回 not implemented。
        """
        started_at = datetime.now(timezone.utc)

        # 计算周期（用于日志和未来实现）
        period_end = datetime.now(timezone.utc)
        period_start = period_end - timedelta(days=command.report_period_days)

        logger.info(
            "Report pipeline: topic=%d, period=%s ~ %s (not implemented yet)",
            command.topic_id,
            period_start.strftime("%Y-%m-%d"),
            period_end.strftime("%Y-%m-%d"),
        )

        # TODO: 实现周报生成
        # 1. self.analysis_repo.list_by_topic(topic_id, min_relevance)
        # 2. 构造 Dify 周报工作流输入
        # 3. 调用 Dify 周报工作流
        # 4. 保存到 reports 表

        return self._fail(
            command,
            started_at,
            "Report pipeline not implemented yet",
        )

    # ------------------------------------------------------------------ #
    #  辅助方法
    # ------------------------------------------------------------------ #

    def _succeed(
        self,
        command: JobCommand,
        started_at: datetime,
        stats: PipelineStats,
    ) -> JobResult:
        finished_at = datetime.now(timezone.utc)
        result = JobResult(
            job_type=command.job_type,
            topic_id=command.topic_id,
            success=True,
            started_at=started_at,
            finished_at=finished_at,
            stats=stats,
        )
        logger.info(
            "Job succeeded: type=%s, topic=%d, duration=%.1fs, stats=%s",
            result.job_type,
            result.topic_id,
            result.duration_seconds,
            stats.to_dict(),
        )
        return result

    def _fail(
        self,
        command: JobCommand,
        started_at: datetime,
        error: str,
    ) -> JobResult:
        finished_at = datetime.now(timezone.utc)
        result = JobResult(
            job_type=command.job_type,
            topic_id=command.topic_id,
            success=False,
            started_at=started_at,
            finished_at=finished_at,
            error=error,
        )
        logger.error(
            "Job failed: type=%s, topic=%d, error=%s",
            result.job_type,
            result.topic_id,
            error,
        )
        return result
