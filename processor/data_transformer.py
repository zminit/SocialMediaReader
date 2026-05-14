"""RawItem 到 AnalysisInput 的转换。"""

from datetime import datetime, timezone
from typing import Optional

from collector.models import RawItem

from .config import ProcessorConfig
from .content_cleaner import ContentCleaner
from .models import AnalysisInput


class DataTransformer:
    """将标准化后的 RawItem 转为 Dify 输入。"""

    def __init__(self, cleaner: ContentCleaner, config: ProcessorConfig):
        self.cleaner = cleaner
        self.config = config

    def transform(
        self,
        item: RawItem,
        cleaned_content: str,
        content_fingerprint: str,
        quality_score: float,
        topic_name: str,
    ) -> AnalysisInput:
        metadata = item.metadata
        return AnalysisInput(
            topic=topic_name,
            title=item.title,
            url=item.url,
            description=item.description,
            cleaned_content_excerpt=self.cleaner.extract_excerpt(
                cleaned_content,
                max_length=self.config.max_excerpt_length,
            ),
            content_length=len(cleaned_content),
            stars=metadata.get("stars"),
            forks=metadata.get("forks"),
            programming_language=metadata.get("programming_language"),
            license=metadata.get("license"),
            topics=metadata.get("topics", []),
            last_commit_at=self._parse_datetime(metadata.get("last_commit_at")),
            activity_score=metadata.get("activity_score"),
            initial_quality_score=quality_score,
            external_id=item.external_id,
            content_fingerprint=content_fingerprint,
            processed_at=datetime.now(timezone.utc),
        )

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None