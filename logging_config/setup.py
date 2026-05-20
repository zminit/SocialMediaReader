"""统一日志初始化。"""

import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional

from .config import LogConfig
from .db_handler import SQLiteLogHandler
from .formatters import ColorFormatter, JSONFormatter

# 应用涉及的所有模块
APP_MODULES = [
    "collector",
    "processor",
    "scheduler",
    "api",
    "api.request",
    "storage",
    "dify_client",
]


def setup_logging(config: Optional[LogConfig] = None) -> LogConfig:
    """一次性配置全局日志系统。

    Args:
        config: 日志配置，为 None 时从环境变量加载。

    Returns:
        使用的 LogConfig 实例。
    """
    if config is None:
        config = LogConfig.from_env()

    root = logging.getLogger()
    # 清除已有 handler（避免重复配置）
    root.handlers.clear()
    root.setLevel(logging.DEBUG)  # root 设最低，由各 handler 控制

    # ── 1. 控制台 Handler ──
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(getattr(logging, config.level, logging.INFO))
    if config.colorize and hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
        console.setFormatter(ColorFormatter(datefmt="%H:%M:%S"))
    else:
        console.setFormatter(logging.Formatter(
            config.console_format, datefmt="%Y-%m-%d %H:%M:%S"
        ))
    root.addHandler(console)

    # ── 2. 文件 Handler（按天轮转）──
    log_dir = Path(config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    file_handler = TimedRotatingFileHandler(
        filename=str(log_dir / "app.log"),
        when="midnight",
        interval=1,
        backupCount=config.max_days,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        config.file_format, datefmt="%Y-%m-%d %H:%M:%S"
    ))
    root.addHandler(file_handler)

    # 错误日志单独一个文件
    error_handler = TimedRotatingFileHandler(
        filename=str(log_dir / "error.log"),
        when="midnight",
        interval=1,
        backupCount=config.max_days,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(logging.Formatter(
        config.file_format, datefmt="%Y-%m-%d %H:%M:%S"
    ))
    root.addHandler(error_handler)

    # ── 3. SQLite Handler（API 查询用）──
    if config.db_enabled:
        db_handler = SQLiteLogHandler(
            db_path=config.db_path,
            max_records=config.db_max_records,
        )
        db_handler.setLevel(getattr(logging, config.db_min_level, logging.INFO))
        root.addHandler(db_handler)

    # ── 4. 各模块独立级别 ──
    for module in APP_MODULES:
        module_logger = logging.getLogger(module)
        override = config.module_levels.get(module)
        if override:
            module_logger.setLevel(getattr(logging, override, logging.INFO))

    # 降低第三方库噪音
    for noisy in ["urllib3", "httpx", "httpcore", "uvicorn.access"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Logging initialized: level=%s, dir=%s, db=%s",
        config.level, config.log_dir,
        config.db_path if config.db_enabled else "disabled",
    )
    return config
