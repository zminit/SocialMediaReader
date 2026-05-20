"""端到端测试：采集 → 处理 → Dify 分析。

用法: python -m examples.end_to_end
"""

import logging
import sys
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    # ---- 1. 初始化所有组件 ----
    from collector.config import CollectorConfig
    from collector.github_collector import GitHubCollector
    from dify_client.client import DifyClient
    from dify_client.config import DifyConfig
    from processor.processor import Processor
    from scheduler.config import OrchestratorConfig
    from scheduler.models import JobCommand
    from scheduler.orchestrator import Orchestrator
    from storage.database import Database
    from storage.analysis_repository import SQLiteAnalysisResultRepository
    from storage.dedup_repository import SQLiteDedupRepository
    from storage.duplicate_repository import SQLiteDuplicateRecordRepository
    from storage.filtered_repository import SQLiteFilteredRecordRepository
    from storage.source_repository import SQLiteSourceRepository
    from storage.topic_repository import SQLiteTopicRepository

    logger.info("=== 初始化组件 ===")

    from storage.config import StorageConfig
    storage_config = StorageConfig(db_path="e2e_test.db")
    db = Database(storage_config)
    db.initialize()

    topic_repo = SQLiteTopicRepository(db)
    source_repo = SQLiteSourceRepository(db)
    dedup_repo = SQLiteDedupRepository(db)
    duplicate_repo = SQLiteDuplicateRecordRepository(db)
    filtered_repo = SQLiteFilteredRecordRepository(db)
    analysis_repo = SQLiteAnalysisResultRepository(db)

    collector_config = CollectorConfig.from_env()
    collector = GitHubCollector(collector_config)

    from processor.config import ProcessorConfig
    from processor.normalizer import Normalizer
    from processor.content_cleaner import ContentCleaner
    from processor.fingerprint import FingerprintCalculator
    from processor.dedup_checker import DedupChecker
    from processor.quality_filter import QualityFilter
    from processor.data_transformer import DataTransformer

    proc_config = ProcessorConfig()
    cleaner = ContentCleaner()
    processor = Processor(
        normalizer=Normalizer(),
        cleaner=cleaner,
        fingerprint_calculator=FingerprintCalculator(),
        dedup_checker=DedupChecker(dedup_repo),
        quality_filter=QualityFilter(proc_config),
        transformer=DataTransformer(cleaner=cleaner, config=proc_config),
        topic_repository=topic_repo,
        config=proc_config,
    )

    dify_config = DifyConfig.from_env()
    dify_client = DifyClient(dify_config)

    orchestrator_config = OrchestratorConfig()
    orchestrator = Orchestrator(
        collector=collector,
        processor=processor,
        dify_client=dify_client,
        source_repo=source_repo,
        topic_repo=topic_repo,
        duplicate_repo=duplicate_repo,
        filtered_repo=filtered_repo,
        analysis_repo=analysis_repo,
        config=orchestrator_config,
    )

    # ---- 2. 创建主题 ----
    logger.info("=== 创建主题 ===")
    topic_id = topic_repo.create_topic(
        name="AI Agent",
        keywords=["AI agent framework"],
    )
    logger.info("Created topic: id=%d", topic_id)

    # ---- 3. 采集 Pipeline ----
    logger.info("=== 运行采集 Pipeline ===")
    collect_cmd = JobCommand(
        job_type="collect",
        topic_id=topic_id,
        max_items=3,  # 少量测试
    )
    collect_result = orchestrator.run_collect(collect_cmd)
    logger.info(
        "Collect result: success=%s, stats=%s",
        collect_result.success,
        collect_result.stats.to_dict() if collect_result.stats else "N/A",
    )

    if not collect_result.success:
        logger.error("Collect failed: %s", collect_result.error)
        sys.exit(1)

    # ---- 4. 检查采集结果 ----
    pending = source_repo.get_sources_by_status("pending_analysis", limit=100)
    logger.info("Pending analysis: %d items", len(pending))
    for s in pending:
        logger.info("  [%d] %s - %s", s["id"], s["title"][:60], s["url"])

    if not pending:
        logger.warning("No items collected, nothing to analyze")
        sys.exit(0)

    # ---- 5. 分析 Pipeline ----
    logger.info("=== 运行 Dify 分析 Pipeline ===")
    analyze_cmd = JobCommand(
        job_type="analyze",
        topic_id=topic_id,
        max_analyze=3,
    )
    analyze_result = orchestrator.run_analyze(analyze_cmd)
    logger.info(
        "Analyze result: success=%s, stats=%s",
        analyze_result.success,
        analyze_result.stats.to_dict() if analyze_result.stats else "N/A",
    )

    # ---- 6. 查看分析结果 ----
    logger.info("=== 分析结果 ===")
    analyzed = source_repo.get_sources_by_topic(topic_id, status="analyzed", limit=100)
    for s in analyzed:
        sid = s["id"]
        ar = analysis_repo.get_by_source_id(sid)
        if ar:
            logger.info(
                "  [%d] %s\n"
                "       summary: %s\n"
                "       relevance: %.2f, quality: %.2f\n"
                "       tags: %s",
                sid,
                s["title"][:60],
                ar.get("summary", "")[:100],
                ar.get("relevance_score", 0),
                ar.get("quality_score", 0),
                ar.get("tags", []),
            )

    logger.info("=== 端到端测试完成 ===")


if __name__ == "__main__":
    main()
