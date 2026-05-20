"""日志配置。"""

import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class LogConfig:
    """日志系统配置。"""

    # 全局默认级别
    level: str = "INFO"

    # 日志文件目录
    log_dir: str = "logs"

    # 文件轮转：保留天数
    max_days: int = 30

    # 单个日志文件最大大小 (MB)
    max_size_mb: int = 10

    # 是否启用 SQLite 日志存储（用于 API 查询）
    db_enabled: bool = True

    # SQLite 日志数据库路径
    db_path: str = "data/logs.db"

    # DB 中保留的最大记录数
    db_max_records: int = 50000

    # DB 最低存储级别（只有 >= 此级别的日志才写入 DB）
    db_min_level: str = "INFO"

    # 控制台是否启用彩色输出
    colorize: bool = True

    # 各模块独立级别覆盖
    module_levels: Dict[str, str] = field(default_factory=dict)

    # 日志格式
    console_format: str = "%(asctime)s │ %(levelname)-8s │ %(name)-20s │ %(message)s"
    file_format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"

    @classmethod
    def from_env(cls) -> "LogConfig":
        """从环境变量加载配置。"""
        module_levels = {}
        # 支持 LOG_LEVEL_COLLECTOR=DEBUG 等环境变量
        for key, value in os.environ.items():
            if key.startswith("LOG_LEVEL_"):
                module_name = key[len("LOG_LEVEL_"):].lower()
                module_levels[module_name] = value.upper()

        return cls(
            level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            log_dir=os.environ.get("LOG_DIR", "logs"),
            max_days=int(os.environ.get("LOG_MAX_DAYS", "30")),
            max_size_mb=int(os.environ.get("LOG_MAX_SIZE_MB", "10")),
            db_enabled=os.environ.get("LOG_DB_ENABLED", "true").lower()
            in ("true", "1", "yes"),
            db_path=os.environ.get("LOG_DB_PATH", "data/logs.db"),
            db_max_records=int(os.environ.get("LOG_DB_MAX_RECORDS", "50000")),
            db_min_level=os.environ.get("LOG_DB_MIN_LEVEL", "INFO").upper(),
            colorize=os.environ.get("LOG_COLORIZE", "true").lower()
            in ("true", "1", "yes"),
            module_levels=module_levels,
        )
