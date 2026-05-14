"""基础质量过滤与软评分。"""

from typing import Dict, Tuple

from collector.models import RawItem

from .config import ProcessorConfig
from .models import QualityEvaluation


class QualityFilter:
    """硬过滤只丢明显不可用内容；stars 等信号只做软评分。"""

    def __init__(self, config: ProcessorConfig):
        self.config = config

    def evaluate(self, item: RawItem, cleaned_content: str) -> QualityEvaluation:
        hard_filtered, reason = self._check_hard_filters(item, cleaned_content)
        checks = self._get_checks(item, cleaned_content)
        if hard_filtered:
            return QualityEvaluation(
                score=0.0,
                hard_filtered=True,
                filter_reason=reason,
                checks=checks,
            )

        score, breakdown = self._calculate_score(item, cleaned_content)
        return QualityEvaluation(
            score=score,
            hard_filtered=False,
            filter_reason=None,
            checks=checks,
            score_breakdown=breakdown,
        )

    def _check_hard_filters(self, item: RawItem, content: str) -> Tuple[bool, str]:
        if not item.title or not item.url or not item.external_id:
            return True, "missing_required_fields"

        if item.source_type == "github":
            if item.metadata.get("is_archived"):
                return True, "archived_repo"
            if not item.raw_text or len(item.raw_text.strip()) < self.config.min_content_length:
                return True, "no_readme"
            if len(content.strip()) < self.config.min_content_length:
                return True, f"insufficient_content_{len(content.strip())}"

        return False, ""

    def _calculate_score(self, item: RawItem, content: str) -> Tuple[float, Dict[str, float]]:
        if item.source_type != "github":
            return 0.5, {"default": 0.5}

        metadata = item.metadata
        score = 0.0
        breakdown: Dict[str, float] = {}

        stars = metadata.get("stars", 0) or 0
        if stars >= 10000:
            stars_score = 0.30
        elif stars >= 1000:
            stars_score = 0.25
        elif stars >= 100:
            stars_score = 0.20
        elif stars >= 10:
            stars_score = 0.15
        else:
            stars_score = 0.05
        score += stars_score
        breakdown["stars"] = stars_score

        activity = float(metadata.get("activity_score", 0) or 0)
        activity_score = max(0.0, min(activity, 1.0)) * 0.30
        score += activity_score
        breakdown["activity"] = activity_score

        content_len = len(content)
        if content_len >= 2000:
            readme_score = 0.25
        elif content_len >= 1000:
            readme_score = 0.20
        elif content_len >= 500:
            readme_score = 0.15
        else:
            readme_score = 0.10
        score += readme_score
        breakdown["readme"] = readme_score

        metadata_score = 0.0
        if metadata.get("license"):
            metadata_score += 0.05
        if metadata.get("topics"):
            metadata_score += 0.05
        if metadata.get("programming_language"):
            metadata_score += 0.05
        score += metadata_score
        breakdown["metadata"] = metadata_score

        return min(score, 1.0), breakdown

    def _get_checks(self, item: RawItem, content: str) -> Dict[str, bool]:
        return {
            "has_title": bool(item.title),
            "has_url": bool(item.url),
            "has_external_id": bool(item.external_id),
            "has_content": len((content or "").strip()) >= self.config.min_content_length,
            "has_description": bool(item.description),
            "not_archived": not item.metadata.get("is_archived", False),
        }