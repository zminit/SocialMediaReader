"""Processor 依赖的抽象查询接口。"""

from abc import ABC, abstractmethod
from typing import Optional


class DedupRepository(ABC):
    """去重查询接口，由 storage 模块实现。"""

    @abstractmethod
    def find_by_url(self, canonical_url: str) -> Optional[int]:
        """通过规范 URL 查找已存在 source id。"""

    @abstractmethod
    def find_by_external_id(self, external_id: str) -> Optional[int]:
        """通过外部 ID 查找已存在 source id。"""

    @abstractmethod
    def find_by_fingerprint(self, fingerprint: str) -> Optional[int]:
        """通过内容指纹查找已存在 source id。"""


class TopicRepository(ABC):
    """主题查询接口，由 storage 或调度上下文适配器实现。"""

    @abstractmethod
    def get_name(self, topic_id: int) -> str:
        """获取真实主题名。"""