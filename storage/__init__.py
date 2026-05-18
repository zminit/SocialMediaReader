"""Storage 模块

SQLite 持久化层，实现 Processor 依赖的查询接口和 Orchestrator 需要的写入接口。

职责：
- 数据库初始化和迁移
- topics 管理
- sources CRUD + 去重查询
- duplicate_records / filtered_records 日志
- analysis_results 存储
"""

from .config import StorageConfig
from .database import Database
from .topic_repository import SQLiteTopicRepository
from .dedup_repository import SQLiteDedupRepository
from .source_repository import SQLiteSourceRepository
from .duplicate_repository import SQLiteDuplicateRecordRepository
from .filtered_repository import SQLiteFilteredRecordRepository
from .analysis_repository import SQLiteAnalysisResultRepository

__all__ = [
    "StorageConfig",
    "Database",
    "SQLiteTopicRepository",
    "SQLiteDedupRepository",
    "SQLiteSourceRepository",
    "SQLiteDuplicateRecordRepository",
    "SQLiteFilteredRecordRepository",
    "SQLiteAnalysisResultRepository",
]
