"""去重查询存储实现。"""

import logging
from typing import Optional

from processor.interfaces import DedupRepository

from .database import Database

logger = logging.getLogger(__name__)


class SQLiteDedupRepository(DedupRepository):
    """SQLite 实现的去重查询仓库。

    查询 sources 表中已有记录，用于 Processor 跨批次去重。
    """

    def __init__(self, db: Database):
        self.db = db

    def find_by_url(self, canonical_url: str) -> Optional[int]:
        """通过规范 URL 查找已存在 source id。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT id FROM sources WHERE canonical_url = ?",
            (canonical_url,),
        )
        row = cursor.fetchone()
        return row["id"] if row else None

    def find_by_external_id(self, external_id: str) -> Optional[int]:
        """通过外部 ID 查找已存在 source id。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT id FROM sources WHERE external_id = ?",
            (external_id,),
        )
        row = cursor.fetchone()
        return row["id"] if row else None

    def find_by_fingerprint(self, fingerprint: str) -> Optional[int]:
        """通过内容指纹查找已存在 source id。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT id FROM sources WHERE content_fingerprint = ?",
            (fingerprint,),
        )
        row = cursor.fetchone()
        return row["id"] if row else None
