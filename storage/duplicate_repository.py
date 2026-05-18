"""重复记录存储实现。"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .database import Database

logger = logging.getLogger(__name__)


class SQLiteDuplicateRecordRepository:
    """SQLite 实现的重复记录仓库。

    记录被 Processor 判定为 duplicate 的 RawItem，
    便于排查 Collector 搜索质量和来源覆盖。
    """

    def __init__(self, db: Database):
        self.db = db

    def create_duplicate_record(
        self,
        *,
        topic_id: int,
        duplicate_type: str,
        duplicate_source_id: int,
        external_id: str,
        url: str,
        canonical_url: str,
        title: str,
        content_fingerprint: str,
        collected_at: datetime,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """记录被 Processor 判定为 duplicate 的 RawItem。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            """
            INSERT INTO duplicate_records (
                topic_id, duplicate_type, duplicate_source_id,
                external_id, url, canonical_url, title,
                content_fingerprint, collected_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic_id,
                duplicate_type,
                duplicate_source_id,
                external_id,
                url,
                canonical_url,
                title,
                content_fingerprint,
                collected_at.isoformat(),
                json.dumps(metadata or {}, ensure_ascii=False, default=str),
            ),
        )
        conn.commit()
        record_id = cursor.lastrowid
        logger.debug(
            "Created duplicate record: id=%d, type=%s, title=%s",
            record_id,
            duplicate_type,
            title[:50],
        )
        return record_id

    def count_by_type(self) -> Dict[str, int]:
        """按重复类型统计数量。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT duplicate_type, COUNT(*) as cnt FROM duplicate_records GROUP BY duplicate_type"
        )
        return {row["duplicate_type"]: row["cnt"] for row in cursor.fetchall()}

    def list_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出最近的重复记录。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT * FROM duplicate_records ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def _row_to_dict(self, row: Any) -> Dict[str, Any]:
        d = dict(row)
        if "metadata" in d and isinstance(d["metadata"], str):
            d["metadata"] = json.loads(d["metadata"])
        return d
