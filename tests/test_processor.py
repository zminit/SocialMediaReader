"""Processor 模块测试。"""

from datetime import datetime, timezone
from typing import Dict, Optional

from collector.models import RawItem
from processor import (
    ContentCleaner,
    DataTransformer,
    DedupChecker,
    DedupRepository,
    FingerprintCalculator,
    Normalizer,
    Processor,
    ProcessorConfig,
    QualityFilter,
    TopicRepository,
)


class InMemoryDedupRepository(DedupRepository):
    def __init__(self):
        self.urls: Dict[str, int] = {}
        self.external_ids: Dict[str, int] = {}
        self.fingerprints: Dict[str, int] = {}

    def find_by_url(self, canonical_url: str) -> Optional[int]:
        return self.urls.get(canonical_url)

    def find_by_external_id(self, external_id: str) -> Optional[int]:
        return self.external_ids.get(external_id)

    def find_by_fingerprint(self, fingerprint: str) -> Optional[int]:
        return self.fingerprints.get(fingerprint)


class InMemoryTopicRepository(TopicRepository):
    def __init__(self):
        self.topics = {1: "AI 工作流搭建"}

    def get_name(self, topic_id: int) -> str:
        return self.topics[topic_id]


def build_processor(dedup_repo: Optional[InMemoryDedupRepository] = None) -> Processor:
    config = ProcessorConfig(min_content_length=50, max_excerpt_length=500)
    cleaner = ContentCleaner()
    return Processor(
        normalizer=Normalizer(),
        cleaner=cleaner,
        fingerprint_calculator=FingerprintCalculator(),
        dedup_checker=DedupChecker(dedup_repo or InMemoryDedupRepository()),
        quality_filter=QualityFilter(config),
        transformer=DataTransformer(cleaner, config),
        topic_repository=InMemoryTopicRepository(),
        config=config,
    )


def make_raw_item(**overrides) -> RawItem:
    raw_text = """
<!-- comment should be removed -->
# Example Workflow Project

[![Build](https://img.shields.io/badge/build-passing.svg)](https://example.com)

## Overview

This project helps developers build AI workflow applications with orchestration,
tool calling, RAG pipelines, and deployment examples.

## Install

```bash
pip install example-workflow
```
""".strip()

    data = dict(
        topic_id=1,
        source_type="github",
        source_subtype="github_repo",
        external_id="github:example/workflow",
        url="https://github.com/example/workflow",
        canonical_url="https://github.com/example/workflow",
        title=" example-workflow ",
        author="example",
        description=" AI workflow orchestration toolkit ",
        published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        collected_at=datetime.now(timezone.utc),
        raw_text=raw_text,
        raw_text_truncated=False,
        raw_text_length=len(raw_text),
        metadata={
            "stars": 3,
            "forks": 1,
            "language": "Python",
            "license": "MIT",
            "topics": ["workflow", "llm"],
            "pushed_at": "2026-05-10T12:00:00+00:00",
            "activity_score": 0.8,
            "is_archived": False,
        },
    )
    data.update(overrides)
    return RawItem(**data)


def test_processor_converts_raw_item_to_analysis_input():
    processor = build_processor()
    result = processor.process(make_raw_item())

    assert result.status == "passed"
    assert result.analysis_input is not None
    assert result.analysis_input.topic == "AI 工作流搭建"
    assert result.analysis_input.title == "example-workflow"
    assert result.analysis_input.programming_language == "Python"
    assert result.analysis_input.last_commit_at is not None
    assert result.analysis_input.initial_quality_score > 0
    assert result.content_fingerprint
    assert "comment should be removed" not in result.analysis_input.cleaned_content_excerpt
    assert "shields.io" not in result.analysis_input.cleaned_content_excerpt

    payload = result.analysis_input.to_dify_payload()
    assert payload["topic"] == "AI 工作流搭建"
    assert payload["metadata"]["programming_language"] == "Python"


def test_processor_detects_duplicate_before_quality_filter():
    repo = InMemoryDedupRepository()
    repo.urls["https://github.com/example/workflow"] = 42
    processor = build_processor(repo)

    result = processor.process(make_raw_item(raw_text="short"))

    assert result.status == "duplicate"
    assert result.duplicate_info == {"type": "url", "duplicate_source_id": 42}


def test_processor_hard_filters_archived_repo():
    item = make_raw_item(metadata={"is_archived": True, "language": "Python"})
    processor = build_processor()

    result = processor.process(item)

    assert result.status == "filtered"
    assert result.filter_info is not None
    assert result.filter_info["reason"] == "archived_repo"


def test_low_stars_are_soft_scored_not_filtered():
    item = make_raw_item(metadata={"stars": 0, "language": "Python", "is_archived": False, "activity_score": 0.1})
    processor = build_processor()

    result = processor.process(item)

    assert result.status == "passed"
    assert result.analysis_input is not None
    assert result.analysis_input.initial_quality_score > 0