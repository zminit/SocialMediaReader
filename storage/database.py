"""数据库初始化与连接管理。"""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

from .config import StorageConfig

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

SCHEMA_SQL = """
-- 主题表
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    keywords TEXT DEFAULT '[]',  -- JSON array
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- 内容源表
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    source_type TEXT NOT NULL,          -- github / rss / csdn / juejin
    source_subtype TEXT NOT NULL,       -- github_repo / article 等
    external_id TEXT NOT NULL,          -- github:owner/repo
    url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    title TEXT NOT NULL,
    author TEXT,
    description TEXT,
    published_at TEXT,
    collected_at TEXT NOT NULL,
    processed_at TEXT NOT NULL,
    raw_text TEXT,
    raw_text_truncated INTEGER NOT NULL DEFAULT 0,
    raw_text_length INTEGER NOT NULL DEFAULT 0,
    cleaned_content_excerpt TEXT,
    content_fingerprint TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',         -- JSON object
    initial_quality_score REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'pending_analysis'  -- pending_analysis / analyzed / analysis_failed
);

-- 重复记录表
CREATE TABLE IF NOT EXISTS duplicate_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    duplicate_type TEXT NOT NULL,        -- url / external_id / content
    duplicate_source_id INTEGER NOT NULL REFERENCES sources(id),
    external_id TEXT NOT NULL,
    url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    title TEXT NOT NULL,
    content_fingerprint TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- 过滤记录表
CREATE TABLE IF NOT EXISTS filtered_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    filter_reason TEXT NOT NULL,
    quality_score REAL NOT NULL DEFAULT 0.0,
    checks TEXT DEFAULT '{}',           -- JSON object
    external_id TEXT NOT NULL,
    url TEXT NOT NULL,
    canonical_url TEXT NOT NULL,
    title TEXT NOT NULL,
    content_fingerprint TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- 分析结果表
CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    workflow_run_id TEXT,
    summary TEXT NOT NULL DEFAULT '',
    relevance_score REAL NOT NULL DEFAULT 0.0,
    quality_score REAL NOT NULL DEFAULT 0.0,
    tags TEXT DEFAULT '[]',             -- JSON array
    raw_response TEXT DEFAULT '{}',     -- JSON object
    analyzed_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Schema 版本跟踪
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- 索引：去重查询
CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_canonical_url ON sources(canonical_url);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sources_external_id ON sources(external_id);
CREATE INDEX IF NOT EXISTS idx_sources_content_fingerprint ON sources(content_fingerprint);

-- 索引：按状态查询
CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(status);
CREATE INDEX IF NOT EXISTS idx_sources_topic_id ON sources(topic_id);

-- 索引：分析结果
CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_results_source_id ON analysis_results(source_id);

-- 索引：主题名唯一
-- (已在 CREATE TABLE 中通过 UNIQUE 约束创建)
"""


class Database:
    """SQLite 数据库管理器。

    Usage:
        config = StorageConfig.from_env()
        db = Database(config)
        db.initialize()

        conn = db.get_connection()
        # ... 使用 conn
    """

    def __init__(self, config: StorageConfig):
        self.config = config
        self._connection: Optional[sqlite3.Connection] = None

    def initialize(self) -> None:
        """初始化数据库：创建目录、建表、建索引。"""
        db_path = Path(self.config.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = self.get_connection()
        cursor = conn.cursor()

        # 检查是否已初始化
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        if cursor.fetchone() is None:
            # 首次初始化
            logger.info("Initializing database at %s", self.config.db_path)
            conn.executescript(SCHEMA_SQL)
            cursor.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
            conn.commit()
            logger.info("Database initialized with schema version %d", SCHEMA_VERSION)
        else:
            # 已存在，检查版本
            cursor.execute(
                "SELECT MAX(version) FROM schema_version"
            )
            row = cursor.fetchone()
            current_version = row[0] if row else 0
            if current_version < SCHEMA_VERSION:
                logger.info(
                    "Database schema upgrade needed: %d -> %d",
                    current_version,
                    SCHEMA_VERSION,
                )
                self._migrate(conn, current_version, SCHEMA_VERSION)
            else:
                logger.debug(
                    "Database schema is up to date (version %d)", current_version
                )

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接（单连接复用）。"""
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.config.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            self._connection.row_factory = sqlite3.Row
            # 开启 WAL 模式，提升并发读性能
            self._connection.execute("PRAGMA journal_mode=WAL")
            # 开启外键约束
            self._connection.execute("PRAGMA foreign_keys=ON")

            if self.config.echo_sql:
                self._connection.set_trace_callback(
                    lambda sql: logger.debug("SQL: %s", sql)
                )

        return self._connection

    def close(self) -> None:
        """关闭数据库连接。"""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            logger.debug("Database connection closed")

    def _migrate(self, conn: sqlite3.Connection, from_version: int, to_version: int) -> None:
        """执行数据库迁移。

        V0 只有一个版本，预留迁移框架。
        """
        # 未来在这里添加迁移逻辑：
        # if from_version < 2:
        #     conn.executescript("ALTER TABLE ...")
        #     ...
        logger.info(
            "Migration from version %d to %d: no migration needed",
            from_version,
            to_version,
        )

    def __enter__(self) -> "Database":
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
