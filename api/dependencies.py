"""FastAPI 依赖注入。

集中管理所有模块实例的创建与生命周期，
各 router 通过 Depends() 获取所需依赖。
"""

import logging
from typing import Optional

from storage.config import StorageConfig
from storage.database import Database
from storage.topic_repository import SQLiteTopicRepository
from storage.dedup_repository import SQLiteDedupRepository
from storage.source_repository import SQLiteSourceRepository
from storage.duplicate_repository import SQLiteDuplicateRecordRepository
from storage.filtered_repository import SQLiteFilteredRecordRepository
from storage.analysis_repository import SQLiteAnalysisResultRepository

from scheduler.models import JobCommand
from scheduler.orchestrator import Orchestrator
from scheduler.config import OrchestratorConfig, SchedulerConfig
from scheduler.scheduler import Scheduler

logger = logging.getLogger(__name__)


class AppState:
    """应用级单例状态，在 app lifespan 中初始化和关闭。

    持有所有 Storage / Orchestrator / Scheduler 实例，
    router 通过 get_xxx() 函数获取。
    """

    def __init__(self):
        self.db: Optional[Database] = None
        self.topic_repo: Optional[SQLiteTopicRepository] = None
        self.dedup_repo: Optional[SQLiteDedupRepository] = None
        self.source_repo: Optional[SQLiteSourceRepository] = None
        self.duplicate_repo: Optional[SQLiteDuplicateRecordRepository] = None
        self.filtered_repo: Optional[SQLiteFilteredRecordRepository] = None
        self.analysis_repo: Optional[SQLiteAnalysisResultRepository] = None
        self.orchestrator: Optional[Orchestrator] = None
        self.scheduler: Optional[Scheduler] = None

    def init_storage(self, storage_config: Optional[StorageConfig] = None) -> None:
        """初始化 Storage 层。"""
        config = storage_config or StorageConfig.from_env()
        self.db = Database(config)
        self.db.initialize()

        self.topic_repo = SQLiteTopicRepository(self.db)
        self.dedup_repo = SQLiteDedupRepository(self.db)
        self.source_repo = SQLiteSourceRepository(self.db)
        self.duplicate_repo = SQLiteDuplicateRecordRepository(self.db)
        self.filtered_repo = SQLiteFilteredRecordRepository(self.db)
        self.analysis_repo = SQLiteAnalysisResultRepository(self.db)
        logger.info("Storage layer initialized: %s", config.db_path)

    def init_orchestrator(
        self,
        orchestrator_config: Optional[OrchestratorConfig] = None,
    ) -> None:
        """初始化 Orchestrator（需要先 init_storage）。

        Collector / Processor / DifyClient 在这里按需创建。
        如果外部 API 不可用（如 GITHUB_TOKEN 未配置），仅影响运行时调用。
        """
        if self.source_repo is None:
            raise RuntimeError("Must call init_storage() before init_orchestrator()")

        config = orchestrator_config or OrchestratorConfig.from_env()

        # Collector（可能因 token 缺失而创建失败，此时 orchestrator.collector 为 None）
        collector = self._create_collector()

        # Processor
        processor = self._create_processor()

        # DifyClient
        dify_client = self._create_dify_client()

        self.orchestrator = Orchestrator(
            collector=collector,
            processor=processor,
            dify_client=dify_client,
            source_repo=self.source_repo,
            topic_repo=self.topic_repo,
            duplicate_repo=self.duplicate_repo,
            filtered_repo=self.filtered_repo,
            analysis_repo=self.analysis_repo,
            config=config,
        )
        logger.info("Orchestrator initialized")

    def init_scheduler(
        self,
        scheduler_config: Optional[SchedulerConfig] = None,
    ) -> None:
        """初始化 Scheduler（需要先 init_orchestrator）。"""
        if self.orchestrator is None:
            raise RuntimeError("Must call init_orchestrator() before init_scheduler()")

        config = scheduler_config or SchedulerConfig.from_env()
        self.scheduler = Scheduler(self.orchestrator, config)
        logger.info("Scheduler initialized (enabled=%s)", config.enabled)

    def start_scheduler(self) -> None:
        """启动定时任务。"""
        if self.scheduler is not None:
            self.scheduler.start()

    def shutdown(self) -> None:
        """关闭所有资源。"""
        if self.scheduler is not None:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler shut down")
        if self.db is not None:
            self.db.close()
            logger.info("Database closed")

    # ------------------------------------------------------------------ #
    #  内部工厂方法
    # ------------------------------------------------------------------ #

    def _create_collector(self):
        """尝试创建 Collector，失败时返回 None。"""
        try:
            from collector.config import CollectorConfig
            from collector.github_collector import GitHubCollector

            config = CollectorConfig.from_env()
            if not config.github_token:
                logger.warning("GITHUB_TOKEN not set, Collector unavailable")
                return None
            return GitHubCollector(config)
        except Exception as e:
            logger.warning("Failed to create Collector: %s", e)
            return None

    def _create_processor(self):
        """创建 Processor。"""
        try:
            from processor.config import ProcessorConfig
            from processor.normalizer import Normalizer
            from processor.content_cleaner import ContentCleaner
            from processor.fingerprint import FingerprintCalculator
            from processor.dedup_checker import DedupChecker
            from processor.quality_filter import QualityFilter
            from processor.data_transformer import DataTransformer
            from processor.processor import Processor

            config = ProcessorConfig.from_env()
            return Processor(
                normalizer=Normalizer(),
                cleaner=ContentCleaner(),
                fingerprint_calculator=FingerprintCalculator(),
                dedup_checker=DedupChecker(self.dedup_repo),
                quality_filter=QualityFilter(config),
                transformer=DataTransformer(config),
                topic_repository=self.topic_repo,
                config=config,
            )
        except Exception as e:
            logger.warning("Failed to create Processor: %s", e)
            return None

    def _create_dify_client(self):
        """尝试创建 DifyClient，失败时返回 None。"""
        try:
            from dify_client.config import DifyConfig
            from dify_client.client import DifyClient

            config = DifyConfig.from_env()
            if not config.api_key:
                logger.warning("DIFY_API_KEY not set, DifyClient unavailable")
                return None
            return DifyClient(config)
        except Exception as e:
            logger.warning("Failed to create DifyClient: %s", e)
            return None


# 全局单例
_app_state = AppState()


def get_app_state() -> AppState:
    """获取全局 AppState。"""
    return _app_state


def get_topic_repo() -> SQLiteTopicRepository:
    state = get_app_state()
    if state.topic_repo is None:
        raise RuntimeError("Storage not initialized")
    return state.topic_repo


def get_source_repo() -> SQLiteSourceRepository:
    state = get_app_state()
    if state.source_repo is None:
        raise RuntimeError("Storage not initialized")
    return state.source_repo


def get_analysis_repo() -> SQLiteAnalysisResultRepository:
    state = get_app_state()
    if state.analysis_repo is None:
        raise RuntimeError("Storage not initialized")
    return state.analysis_repo


def get_duplicate_repo() -> SQLiteDuplicateRecordRepository:
    state = get_app_state()
    if state.duplicate_repo is None:
        raise RuntimeError("Storage not initialized")
    return state.duplicate_repo


def get_filtered_repo() -> SQLiteFilteredRecordRepository:
    state = get_app_state()
    if state.filtered_repo is None:
        raise RuntimeError("Storage not initialized")
    return state.filtered_repo


def get_orchestrator() -> Orchestrator:
    state = get_app_state()
    if state.orchestrator is None:
        raise RuntimeError("Orchestrator not initialized")
    return state.orchestrator


def get_scheduler() -> Scheduler:
    state = get_app_state()
    if state.scheduler is None:
        raise RuntimeError("Scheduler not initialized")
    return state.scheduler
