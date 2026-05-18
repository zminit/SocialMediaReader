"""分析结果存储实现。"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .database import Database

logger = logging.getLogger(__name__)


class SQLiteAnalysisResultRepository:
    """SQLite 实现的分析结果仓库。

    保存 Dify 内容分析工作流返回的结果。
    """

    def __init__(self, db: Database):
        self.db = db

    def save_analysis_result(
        self,
        *,
        source_id: int,
        workflow_run_id: Optional[str] = None,
        summary: str = "",
        relevance_score: float = 0.0,
        quality_score: float = 0.0,
        tags: Optional[List[str]] = None,
        raw_response: Optional[Dict[str, Any]] = None,
        analyzed_at: datetime,
    ) -> int:
        """保存 Dify 分析结果。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            """
            INSERT INTO analysis_results (
                source_id, workflow_run_id, summary,
                relevance_score, quality_score, tags,
                raw_response, analyzed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_id,
                workflow_run_id,
                summary,
                relevance_score,
                quality_score,
                json.dumps(tags or [], ensure_ascii=False),
                json.dumps(raw_response or {}, ensure_ascii=False, default=str),
                analyzed_at.isoformat(),
            ),
        )
        conn.commit()
        result_id = cursor.lastrowid
        logger.info(
            "Saved analysis result: id=%d, source_id=%d, relevance=%.2f",
            result_id,
            source_id,
            relevance_score,
        )
        return result_id

    def get_by_source_id(self, source_id: int) -> Optional[Dict[str, Any]]:
        """获取指定 source 的分析结果。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT * FROM analysis_results WHERE source_id = ?",
            (source_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def list_by_topic(
        self,
        topic_id: int,
        min_relevance: float = 0.0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """查询指定主题的分析结果（关联 sources 表）。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            """
            SELECT ar.*, s.title, s.url, s.source_type, s.initial_quality_score
            FROM analysis_results ar
            JOIN sources s ON ar.source_id = s.id
            WHERE s.topic_id = ? AND ar.relevance_score >= ?
            ORDER BY ar.relevance_score DESC
            LIMIT ?
            """,
            (topic_id, min_relevance, limit),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def _row_to_dict(self, row: Any) -> Dict[str, Any]:
        d = dict(row)
        if "tags" in d and isinstance(d["tags"], str):
            d["tags"] = json.loads(d["tags"])
        if "raw_response" in d and isinstance(d["raw_response"], str):
            d["raw_response"] = json.loads(d["raw_response"])
        return d
