"""Storage 配置。"""

import os
from dataclasses import dataclass


@dataclass
class StorageConfig:
    """Storage 模块配置。

    Attributes:
        db_path: SQLite 数据库文件路径
        echo_sql: 是否打印 SQL（调试用）
    """

    db_path: str = "data/social_media_reader.db"
    echo_sql: bool = False

    @classmethod
    def from_env(cls) -> "StorageConfig":
        return cls(
            db_path=os.getenv("STORAGE_DB_PATH", "data/social_media_reader.db"),
            echo_sql=os.getenv("STORAGE_ECHO_SQL", "").lower() in ("1", "true"),
        )
