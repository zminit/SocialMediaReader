"""RawItem 标准化。"""

from dataclasses import replace
from typing import Any, Dict

from collector.models import RawItem


class Normalizer:
    """标准化 RawItem，不修改原对象。"""

    def normalize(self, item: RawItem) -> RawItem:
        metadata = self._normalize_metadata(item.metadata)
        canonical_url = (item.canonical_url or item.url).strip()

        return replace(
            item,
            url=item.url.strip(),
            canonical_url=canonical_url,
            title=item.title.strip(),
            author=item.author.strip() if item.author else item.author,
            description=item.description.strip() if item.description else item.description,
            metadata=metadata,
        )

    def _normalize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(metadata or {})

        # 兼容当前 Collector 的 language/pushed_at 字段，Processor 对外统一使用
        # programming_language/last_commit_at。
        if "programming_language" not in normalized and "language" in normalized:
            normalized["programming_language"] = normalized.get("language")

        if "last_commit_at" not in normalized:
            normalized["last_commit_at"] = normalized.get("pushed_at")

        if normalized.get("topics") is None:
            normalized["topics"] = []

        return normalized