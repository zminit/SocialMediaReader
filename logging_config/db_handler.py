"""SQLite 日志 Handler — 将日志写入数据库，支持 API 查询。"""

import logging
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

LOG_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS log_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    level TEXT NOT NULL,
    logger TEXT NOT NULL,
    module TEXT,
    function TEXT,
    line INTEGER,
    message TEXT NOT NULL,
    exception TEXT,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_log_timestamp ON log_entries(timestamp);
CREATE INDEX IF NOT EXISTS idx_log_level ON log_entries(level);
CREATE INDEX IF NOT EXISTS idx_log_logger ON log_entries(logger);
"""


class SQLiteLogHandler(logging.Handler):
    """将日志记录写入 SQLite 数据库。

    使用后台线程批量写入，避免阻塞主线程。
    """

    def __init__(
        self,
        db_path: str = "data/logs.db",
        max_records: int = 50000,
        flush_interval: float = 2.0,
        batch_size: int = 100,
    ):
        super().__init__()
        self.db_path = db_path
        self.max_records = max_records
        self.flush_interval = flush_interval
        self.batch_size = batch_size

        self._buffer: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

        # 初始化数据库
        self._init_db()

        # 启动后台写入线程
        self._flush_thread = threading.Thread(
            target=self._flush_loop, daemon=True, name="log-db-flusher"
        )
        self._flush_thread.start()

    def _init_db(self) -> None:
        """初始化日志数据库。"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(LOG_TABLE_SQL)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.commit()
        finally:
            conn.close()

    def emit(self, record: logging.LogRecord) -> None:
        """接收日志记录，放入缓冲区。"""
        try:
            entry = {
                "timestamp": datetime.fromtimestamp(
                    record.created, tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "level": record.levelname,
                "logger": record.name,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "message": record.getMessage(),
                "exception": (
                    self.format_exception(record) if record.exc_info else None
                ),
                "created_at": record.created,
            }
            with self._lock:
                self._buffer.append(entry)

                # 如果缓冲区满了，立即刷新
                if len(self._buffer) >= self.batch_size:
                    self._flush()
        except Exception:
            self.handleError(record)

    def format_exception(self, record: logging.LogRecord) -> Optional[str]:
        """格式化异常信息。"""
        if record.exc_info:
            formatter = logging.Formatter()
            return formatter.formatException(record.exc_info)
        return None

    def _flush_loop(self) -> None:
        """后台定时刷新缓冲区。"""
        while not self._stop_event.is_set():
            time.sleep(self.flush_interval)
            with self._lock:
                if self._buffer:
                    self._flush()

    def _flush(self) -> None:
        """将缓冲区写入数据库（需在锁内调用）。"""
        if not self._buffer:
            return

        entries = self._buffer[:]
        self._buffer.clear()

        try:
            conn = sqlite3.connect(self.db_path, timeout=5)
            try:
                conn.executemany(
                    """INSERT INTO log_entries
                       (timestamp, level, logger, module, function, line, message, exception, created_at)
                       VALUES (:timestamp, :level, :logger, :module, :function, :line, :message, :exception, :created_at)
                    """,
                    entries,
                )
                conn.commit()

                # 清理超出限制的旧记录
                self._cleanup(conn)
            finally:
                conn.close()
        except Exception:
            pass  # 日志系统本身不应抛出异常

    def _cleanup(self, conn: sqlite3.Connection) -> None:
        """清理超出最大记录数的旧日志。"""
        cursor = conn.execute("SELECT COUNT(*) FROM log_entries")
        count = cursor.fetchone()[0]
        if count > self.max_records:
            excess = count - self.max_records
            conn.execute(
                """DELETE FROM log_entries WHERE id IN (
                    SELECT id FROM log_entries ORDER BY id ASC LIMIT ?
                )""",
                (excess,),
            )
            conn.commit()

    def close(self) -> None:
        """关闭 Handler，刷新剩余缓冲区。"""
        self._stop_event.set()
        with self._lock:
            self._flush()
        super().close()


class LogQueryService:
    """日志查询服务 — 提供给 API 路由使用。"""

    def __init__(self, db_path: str = "data/logs.db"):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn

    def query_logs(
        self,
        level: Optional[str] = None,
        logger_name: Optional[str] = None,
        search: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """查询日志记录。"""
        conditions = []
        params = []

        if level:
            conditions.append("level = ?")
            params.append(level.upper())
        if logger_name:
            conditions.append("logger LIKE ?")
            params.append(f"%{logger_name}%")
        if search:
            conditions.append("message LIKE ?")
            params.append(f"%{search}%")
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)

        where = " AND ".join(conditions) if conditions else "1=1"

        conn = self._get_conn()
        try:
            # 总数
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM log_entries WHERE {where}", params
            )
            total = cursor.fetchone()[0]

            # 数据
            cursor = conn.execute(
                f"""SELECT id, timestamp, level, logger, module, function,
                           line, message, exception
                    FROM log_entries
                    WHERE {where}
                    ORDER BY id DESC
                    LIMIT ? OFFSET ?""",
                params + [limit, offset],
            )
            rows = [dict(row) for row in cursor.fetchall()]

            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "items": rows,
            }
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """获取日志统计信息。"""
        conn = self._get_conn()
        try:
            # 各级别数量
            cursor = conn.execute(
                """SELECT level, COUNT(*) as count
                   FROM log_entries
                   GROUP BY level
                   ORDER BY count DESC"""
            )
            level_counts = {row["level"]: row["count"] for row in cursor.fetchall()}

            # 总数
            cursor = conn.execute("SELECT COUNT(*) FROM log_entries")
            total = cursor.fetchone()[0]

            # 最近 24 小时各级别趋势（按小时分组）
            cursor = conn.execute(
                """SELECT
                       strftime('%Y-%m-%dT%H:00:00Z', timestamp) as hour,
                       level,
                       COUNT(*) as count
                   FROM log_entries
                   WHERE timestamp >= datetime('now', '-24 hours')
                   GROUP BY hour, level
                   ORDER BY hour"""
            )
            hourly = {}
            for row in cursor.fetchall():
                hour = row["hour"]
                if hour not in hourly:
                    hourly[hour] = {}
                hourly[hour][row["level"]] = row["count"]

            # 各模块日志量
            cursor = conn.execute(
                """SELECT logger, COUNT(*) as count
                   FROM log_entries
                   GROUP BY logger
                   ORDER BY count DESC
                   LIMIT 20"""
            )
            module_counts = {row["logger"]: row["count"] for row in cursor.fetchall()}

            return {
                "total": total,
                "by_level": level_counts,
                "by_module": module_counts,
                "hourly_trend": hourly,
            }
        finally:
            conn.close()

    def clear_logs(self, before: Optional[str] = None) -> int:
        """清理日志。"""
        conn = self._get_conn()
        try:
            if before:
                cursor = conn.execute(
                    "DELETE FROM log_entries WHERE timestamp < ?", (before,)
                )
            else:
                cursor = conn.execute("DELETE FROM log_entries")
            conn.commit()
            deleted = cursor.rowcount
            conn.execute("VACUUM")
            return deleted
        finally:
            conn.close()
