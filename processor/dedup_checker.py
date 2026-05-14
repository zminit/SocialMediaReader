"""去重检查。"""

from typing import Any, Dict, Optional

from .interfaces import DedupRepository


class DedupChecker:
    """只做去重查询，不写入状态。"""

    def __init__(self, dedup_repository: DedupRepository):
        self.repo = dedup_repository

    def check(
        self,
        canonical_url: str,
        external_id: str,
        fingerprint: str,
    ) -> Optional[Dict[str, Any]]:
        dup_id = self.repo.find_by_url(canonical_url)
        if dup_id:
            return {"type": "url", "source_id": dup_id}

        dup_id = self.repo.find_by_external_id(external_id)
        if dup_id:
            return {"type": "external_id", "source_id": dup_id}

        dup_id = self.repo.find_by_fingerprint(fingerprint)
        if dup_id:
            return {"type": "content", "source_id": dup_id}

        return None