"""日志格式化器。"""

import json
import logging
from datetime import datetime, timezone


class ColorFormatter(logging.Formatter):
    """控制台彩色格式化器。"""

    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[1;31m",  # 粗体红色
    }
    RESET = "\033[0m"
    DIM = "\033[2m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        # 时间用暗色
        asctime = self.formatTime(record, self.datefmt)
        # 模块名截断到 20 字符
        name = record.name[:20].ljust(20)

        msg = record.getMessage()
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            msg = msg + "\n" + record.exc_text

        return (
            f"{self.DIM}{asctime}{self.RESET} │ "
            f"{color}{record.levelname:<8}{self.RESET} │ "
            f"{name} │ {msg}"
        )


class JSONFormatter(logging.Formatter):
    """JSON 结构化日志格式化器（用于文件存储）。"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data"):
            log_entry["extra"] = record.extra_data

        return json.dumps(log_entry, ensure_ascii=False)
