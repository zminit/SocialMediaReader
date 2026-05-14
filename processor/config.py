"""Processor 配置。"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessorConfig:
    """Processor 运行配置。

    V0 仅保留必要配置，避免暗示已有复杂相似度能力。
    """

    min_content_length: int = 50
    max_excerpt_length: int = 2000

    @classmethod
    def from_env(cls) -> "ProcessorConfig":
        """从环境变量加载配置。"""
        return cls(
            min_content_length=int(os.getenv("PROCESSOR_MIN_CONTENT_LENGTH", "50")),
            max_excerpt_length=int(os.getenv("PROCESSOR_MAX_EXCERPT_LENGTH", "2000")),
        )