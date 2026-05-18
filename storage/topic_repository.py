"""Topic 存储实现。"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from processor.interfaces import TopicRepository

from .database import Database

logger = logging.getLogger(__name__)


class TopicNotFoundError(Exception):
    """主题不存在。"""

    def __init__(self, topic_id: int):
        self.topic_id = topic_id
        super().__init__(f"Topic not found: id={topic_id}")


class SQLiteTopicRepository(TopicRepository):
    """SQLite 实现的主题仓库。"""

    def __init__(self, db: Database):
        self.db = db

    def get_name(self, topic_id: int) -> str:
        """获取真实主题名。

        Raises:
            TopicNotFoundError: 主题不存在时抛出，避免 Dify 收到错误主题。
        """
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT name FROM topics WHERE id = ?", (topic_id,)
        )
        row = cursor.fetchone()
        if row is None:
            raise TopicNotFoundError(topic_id)
        return row["name"]

    def create_topic(
        self,
        name: str,
        keywords: Optional[List[str]] = None,
    ) -> int:
        """创建主题并返回 topic_id。"""
        conn = self.db.get_connection()
        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            "INSERT INTO topics (name, keywords, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (name, json.dumps(keywords or [], ensure_ascii=False), now, now),
        )
        conn.commit()
        topic_id = cursor.lastrowid
        logger.info("Created topic: id=%d, name=%s", topic_id, name)
        return topic_id

    def get_topic(self, topic_id: int) -> Optional[Dict[str, Any]]:
        """获取主题详情。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT id, name, keywords, created_at, updated_at FROM topics WHERE id = ?",
            (topic_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "keywords": json.loads(row["keywords"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def list_topics(self) -> List[Dict[str, Any]]:
        """列出所有主题。"""
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT id, name, keywords, created_at, updated_at FROM topics ORDER BY id"
        )
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "keywords": json.loads(row["keywords"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
            for row in cursor.fetchall()
        ]

    def update_topic(
        self,
        topic_id: int,
        *,
        name: Optional[str] = None,
        keywords: Optional[List[str]] = None,
    ) -> bool:
        """更新主题，返回是否成功。"""
        conn = self.db.get_connection()
        now = datetime.now(timezone.utc).isoformat()

        updates = []
        params: List[Any] = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if keywords is not None:
            updates.append("keywords = ?")
            params.append(json.dumps(keywords, ensure_ascii=False))

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(now)
        params.append(topic_id)

        sql = f"UPDATE topics SET {', '.join(updates)} WHERE id = ?"
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.rowcount > 0
