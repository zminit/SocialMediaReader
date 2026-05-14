"""Processor 主流程。"""

import logging
from typing import Iterable, List

from collector.models import RawItem

from .config import ProcessorConfig
from .content_cleaner import ContentCleaner
from .data_transformer import DataTransformer
from .dedup_checker import DedupChecker
from .fingerprint import FingerprintCalculator
from .interfaces import TopicRepository
from .models import AnalysisInput, ProcessingResult
from .normalizer import Normalizer
from .quality_filter import QualityFilter


class Processor:
    """轻量 Processor：不负责持久化，不调用 Dify。"""

    def __init__(
        self,
        normalizer: Normalizer,
        cleaner: ContentCleaner,
        fingerprint_calculator: FingerprintCalculator,
        dedup_checker: DedupChecker,
        quality_filter: QualityFilter,
        transformer: DataTransformer,
        topic_repository: TopicRepository,
        config: ProcessorConfig,
    ):
        self.normalizer = normalizer
        self.cleaner = cleaner
        self.fingerprint = fingerprint_calculator
        self.dedup = dedup_checker
        self.quality_filter = quality_filter
        self.transformer = transformer
        self.topics = topic_repository
        self.config = config
        self.logger = logging.getLogger(__name__)

    def process(self, item: RawItem) -> ProcessingResult:
        normalized = self.normalizer.normalize(item)
        cleaned_content = self.cleaner.clean(normalized)
        fingerprint = self.fingerprint.calculate(cleaned_content)

        duplicate = self.dedup.check(
            canonical_url=normalized.canonical_url,
            external_id=normalized.external_id,
            fingerprint=fingerprint,
        )
        if duplicate:
            return ProcessingResult.duplicate(
                dup_type=duplicate["type"],
                dup_id=duplicate["source_id"],
                fingerprint=fingerprint,
                normalized_item=normalized,
            )

        quality = self.quality_filter.evaluate(normalized, cleaned_content)
        if quality.hard_filtered:
            return ProcessingResult.filtered(
                reason=quality.filter_reason or "unknown",
                quality_score=quality.score,
                checks=quality.checks,
                normalized_item=normalized,
                fingerprint=fingerprint,
            )

        topic_name = self.topics.get_name(normalized.topic_id)
        analysis_input = self.transformer.transform(
            item=normalized,
            cleaned_content=cleaned_content,
            content_fingerprint=fingerprint,
            quality_score=quality.score,
            topic_name=topic_name,
        )

        return ProcessingResult.passed(
            analysis_input=analysis_input,
            fingerprint=fingerprint,
            normalized_item=normalized,
        )

    def process_batch(self, items: Iterable[RawItem]) -> List[ProcessingResult]:
        results = [self.process(item) for item in items]
        stats = {"passed": 0, "duplicate": 0, "filtered": 0}
        for result in results:
            stats[result.status] = stats.get(result.status, 0) + 1
        self.logger.info("Processor batch complete: %s", stats)
        return results

    def process_batch_to_analysis_inputs(self, items: Iterable[RawItem]) -> List[AnalysisInput]:
        return [
            result.analysis_input
            for result in self.process_batch(items)
            if result.status == "passed" and result.analysis_input is not None
        ]