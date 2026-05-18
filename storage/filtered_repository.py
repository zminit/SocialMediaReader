"""过滤记录存储实现。"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .database import Database

logger = logging.getLogger(__name__)


class SQLiteFilteredRecordRepository:
    """SQLite 实现的过滤记录仓库。

    记录被 Processor 硬过滤的 RawItem，便于后续调整过滤规则。
    """

    def __init__(self, db: Database):
        self.db = db

    def create_filtered_record(
        self,
        *,
        topic_id: int,
        filter_reason: str,
        quality_score: float,
        checks: Optional[Dict[str, bool]] = None,
        external_id: str,
        url: str,
        canonical_url: str,
        title: str,
        content_fingerprint: str,
        collected_at: datetime,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """记录被 Processor 硬过滤的 RawItem。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            """
            INSERT INTO filtered_records (
                topic_id, filter_reason, quality_score, checks,
                external_id, url, canonical_url, title,
                content_fingerprint, collected_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                topic_id,
                filter_reason,
                quality_score,
                json.dumps(checks or {}, ensure_ascii=False),
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
            "Created filtered record: id=%d, reason=%s, title=%s",
            record_id,
            filter_reason,
            title[:50],
        )
        return record_id

    def count_by_reason(self) -> Dict[str, int]:
        """按过滤原因统计数量。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT filter_reason, COUNT(*) as cnt FROM filtered_records GROUP BY filter_reason"
        )
        return {row["filter_reason"]: row["cnt"] for row in cursor.fetchall()}

    def list_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """列出最近的过滤记录。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT * FROM filtered_records ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def _row_to_dict(self, row: Any) -> Dict[str, Any]:
        d = dict(row)
        if "checks" in d and isinstance(d["checks"], str):
            d["checks"] = json.loads(d["checks"])
        if "metadata" in d and isinstance(d["metadata"], str):
            d["metadata"] = json.loads(d["metadata"])
        return d
