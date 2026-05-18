"""Source 存储实现。"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .database import Database

logger = logging.getLogger(__name__)


class SQLiteSourceRepository:
    """SQLite 实现的内容源仓库。

    负责 sources 表的 CRUD 操作。
    """

    def __init__(self, db: Database):
        self.db = db

    def create_source(
        self,
        *,
        topic_id: int,
        source_type: str,
        source_subtype: str,
        external_id: str,
        url: str,
        canonical_url: str,
        title: str,
        author: Optional[str] = None,
        description: Optional[str] = None,
        published_at: Optional[datetime] = None,
        collected_at: datetime,
        processed_at: datetime,
        raw_text: Optional[str] = None,
        raw_text_truncated: bool = False,
        raw_text_length: int = 0,
        cleaned_content_excerpt: Optional[str] = None,
        content_fingerprint: str,
        metadata: Optional[Dict[str, Any]] = None,
        initial_quality_score: float = 0.0,
        status: str = "pending_analysis",
    ) -> int:
        """创建 source 记录并返回 source_id。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            """
            INSERT INTO sources (
                topic_id, source_type, source_subtype, external_id,
                url, canonical_url, title, author, description,
                published_at, collected_at, processed_at,
                raw_text, raw_text_truncated, raw_text_length,
                cleaned_content_excerpt, content_fingerprint,
                metadata, initial_quality_score, status
            ) VALUES (
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?, ?
            )
            """,
            (
                topic_id,
                source_type,
                source_subtype,
                external_id,
                url,
                canonical_url,
                title,
                author,
                description,
                published_at.isoformat() if published_at else None,
                collected_at.isoformat(),
                processed_at.isoformat(),
                raw_text,
                1 if raw_text_truncated else 0,
                raw_text_length,
                cleaned_content_excerpt,
                content_fingerprint,
                json.dumps(metadata or {}, ensure_ascii=False, default=str),
                initial_quality_score,
                status,
            ),
        )
        conn.commit()
        source_id = cursor.lastrowid
        logger.info(
            "Created source: id=%d, type=%s, title=%s",
            source_id,
            source_type,
            title[:50],
        )
        return source_id

    def get_source(self, source_id: int) -> Optional[Dict[str, Any]]:
        """获取单个 source 详情。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT * FROM sources WHERE id = ?", (source_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def get_sources_by_status(
        self,
        status: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """按状态查询 sources。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT * FROM sources WHERE status = ? ORDER BY id LIMIT ?",
            (status, limit),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_sources_by_topic(
        self,
        topic_id: int,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """按主题查询 sources。"""
        conn = self.db.get_connection()
        if status:
            cursor = conn.execute(
                "SELECT * FROM sources WHERE topic_id = ? AND status = ? ORDER BY id DESC LIMIT ?",
                (topic_id, status, limit),
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM sources WHERE topic_id = ? ORDER BY id DESC LIMIT ?",
                (topic_id, limit),
            )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def update_status(self, source_id: int, status: str) -> bool:
        """更新 source 状态。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            "UPDATE sources SET status = ? WHERE id = ?",
            (status, source_id),
        )
        conn.commit()
        return cursor.rowcount > 0

    def count_by_status(self) -> Dict[str, int]:
        """按状态统计 source 数量。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM sources GROUP BY status"
        )
        return {row["status"]: row["cnt"] for row in cursor.fetchall()}

    def _row_to_dict(self, row: Any) -> Dict[str, Any]:
        """将 sqlite3.Row 转为 dict，解析 JSON 字段。"""
        d = dict(row)
        d["raw_text_truncated"] = bool(d.get("raw_text_truncated", 0))
        if "metadata" in d and isinstance(d["metadata"], str):
            d["metadata"] = json.loads(d["metadata"])
        return d
