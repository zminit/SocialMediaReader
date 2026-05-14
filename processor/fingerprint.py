"""内容指纹计算。"""

import hashlib
import re


class FingerprintCalculator:
    """V0 使用 SHA256 精确指纹，不提供相似度阈值能力。"""

    def calculate(self, content: str) -> str:
        normalized = self._normalize_for_fingerprint(content)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _normalize_for_fingerprint(self, content: str) -> str:
        content = re.sub(r"\s+", " ", content or "")
        return content.lower().strip()