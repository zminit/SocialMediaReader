"""Scheduler + Orchestrator 模块测试。

使用 unittest.mock 隔离所有外部依赖，
只测试 Orchestrator 的编排逻辑和 Scheduler 的注册/触发逻辑。
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from scheduler.config import OrchestratorConfig, SchedulerConfig
from scheduler.models import JobCommand, JobResult, PipelineStats
from scheduler.orchestrator import Orchestrator
from scheduler.scheduler import Scheduler


# ------------------------------------------------------------------ #
#  辅助：构造 mock 依赖
# ------------------------------------------------------------------ #


def _make_mock_orchestrator() -> Orchestrator:
    """构造一个带 mock 依赖的 Orchestrator。"""
    collector = MagicMock()
    processor = MagicMock()
    dify_client = MagicMock()
    source_repo = MagicMock()
    topic_repo = MagicMock()
    duplicate_repo = MagicMock()
    filtered_repo = MagicMock()
    analysis_repo = MagicMock()
    config = OrchestratorConfig()

    orch = Orchestrator(
        collector=collector,
        processor=processor,
        dify_client=dify_client,
        source_repo=source_repo,
        topic_repo=topic_repo,
        duplicate_repo=duplicate_repo,
        filtered_repo=filtered_repo,
        analysis_repo=analysis_repo,
        config=config,
    )
    return orch


def _make_raw_item(**overrides):
    """构造一个简单的 mock RawItem。"""
    item = MagicMock()
    item.topic_id = overrides.get("topic_id", 1)
    item.source_type = overrides.get("source_type", "github")
    item.source_subtype = overrides.get("source_subtype", "github_repo")
    item.external_id = overrides.get("external_id", "github:test/repo")
    item.url = overrides.get("url", "https://github.com/test/repo")
    item.canonical_url = overrides.get("canonical_url", "https://github.com/test/repo")
    item.title = overrides.get("title", "Test Repo")
    item.author = overrides.get("author", "test")
    item.description = overrides.get("description", "A test repo")
    item.published_at = overrides.get("published_at", None)
    item.collected_at = overrides.get("collected_at", datetime.now(timezone.utc))
    item.raw_text = overrides.get("raw_text", "README content")
    item.raw_text_truncated = overrides.get("raw_text_truncated", False)
    item.raw_text_length = overrides.get("raw_text_length", 14)
    item.metadata = overrides.get("metadata", {"stars": 100})
    return item


def _make_analysis_input():
    """构造一个简单的 mock AnalysisInput。"""
    ai = MagicMock()
    ai.cleaned_content_excerpt = "cleaned content"
    ai.initial_quality_score = 0.8
    return ai


# ------------------------------------------------------------------ #
#  JobCommand 测试
# ------------------------------------------------------------------ #


class TestJobCommand(unittest.TestCase):
    """测试 JobCommand 数据模型。"""

    def test_valid_collect_command(self):
        cmd = JobCommand(job_type="collect", topic_id=1)
        self.assertEqual(cmd.job_type, "collect")
        self.assertEqual(cmd.topic_id, 1)
        self.assertEqual(cmd.trigger, "cron")

    def test_valid_analyze_command_topic_zero(self):
        """analyze 允许 topic_id=0 表示所有主题。"""
        cmd = JobCommand(job_type="analyze", topic_id=0)
        self.assertEqual(cmd.topic_id, 0)

    def test_invalid_job_type(self):
        with self.assertRaises(ValueError):
            JobCommand(job_type="invalid", topic_id=1)

    def test_invalid_trigger(self):
        with self.assertRaises(ValueError):
            JobCommand(job_type="collect", topic_id=1, trigger="invalid")

    def test_collect_requires_positive_topic_id(self):
        with self.assertRaises(ValueError):
            JobCommand(job_type="collect", topic_id=0)

    def test_manual_trigger(self):
        cmd = JobCommand(job_type="analyze", topic_id=1, trigger="manual")
        self.assertEqual(cmd.trigger, "manual")


# ------------------------------------------------------------------ #
#  PipelineStats 测试
# ------------------------------------------------------------------ #


class TestPipelineStats(unittest.TestCase):
    def test_to_dict(self):
        stats = PipelineStats(collected=10, passed=7, duplicated=2, filtered=1)
        d = stats.to_dict()
        self.assertEqual(d["collected"], 10)
        self.assertEqual(d["passed"], 7)
        self.assertEqual(d["duplicated"], 2)
        self.assertEqual(d["filtered"], 1)


# ------------------------------------------------------------------ #
#  JobResult 测试
# ------------------------------------------------------------------ #


class TestJobResult(unittest.TestCase):
    def test_duration_seconds(self):
        t1 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 1, 1, 0, 1, 30, tzinfo=timezone.utc)
        result = JobResult(
            job_type="collect",
            topic_id=1,
            success=True,
            started_at=t1,
            finished_at=t2,
        )
        self.assertEqual(result.duration_seconds, 90.0)

    def test_to_dict(self):
        result = JobResult(
            job_type="analyze",
            topic_id=2,
            success=False,
            started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            finished_at=datetime(2026, 1, 1, 0, 0, 5, tzinfo=timezone.utc),
            error="test error",
        )
        d = result.to_dict()
        self.assertEqual(d["job_type"], "analyze")
        self.assertFalse(d["success"])
        self.assertEqual(d["error"], "test error")
        self.assertEqual(d["duration_seconds"], 5.0)


# ------------------------------------------------------------------ #
#  OrchestratorConfig 测试
# ------------------------------------------------------------------ #


class TestOrchestratorConfig(unittest.TestCase):
    def test_defaults(self):
        config = OrchestratorConfig()
        self.assertEqual(config.analyze_delay, 1.0)
        self.assertEqual(config.max_collect_per_run, 50)
        self.assertEqual(config.max_analyze_per_run, 20)

    @patch.dict("os.environ", {
        "ORCHESTRATOR_ANALYZE_DELAY": "2.5",
        "ORCHESTRATOR_MAX_COLLECT": "100",
    })
    def test_from_env(self):
        config = OrchestratorConfig.from_env()
        self.assertEqual(config.analyze_delay, 2.5)
        self.assertEqual(config.max_collect_per_run, 100)


# ------------------------------------------------------------------ #
#  SchedulerConfig 测试
# ------------------------------------------------------------------ #


class TestSchedulerConfig(unittest.TestCase):
    def test_defaults(self):
        config = SchedulerConfig()
        self.assertEqual(config.collect_hour, 2)
        self.assertTrue(config.enabled)

    @patch.dict("os.environ", {"SCHEDULER_ENABLED": "false"})
    def test_disabled(self):
        config = SchedulerConfig.from_env()
        self.assertFalse(config.enabled)


# ------------------------------------------------------------------ #
#  Orchestrator: Collect Pipeline 测试
# ------------------------------------------------------------------ #


class TestOrchestratorCollect(unittest.TestCase):
    """测试 Orchestrator.run_collect 编排逻辑。"""

    def test_collect_topic_not_found(self):
        orch = _make_mock_orchestrator()
        orch.topic_repo.get_topic.return_value = None

        cmd = JobCommand(job_type="collect", topic_id=999)
        result = orch.run_collect(cmd)

        self.assertFalse(result.success)
        self.assertIn("Topic not found", result.error)

    def test_collect_no_keywords(self):
        orch = _make_mock_orchestrator()
        orch.topic_repo.get_topic.return_value = {
            "id": 1, "name": "Test", "keywords": [],
        }

        cmd = JobCommand(job_type="collect", topic_id=1)
        result = orch.run_collect(cmd)

        self.assertFalse(result.success)
        self.assertIn("No keywords", result.error)

    def test_collect_empty_results(self):
        orch = _make_mock_orchestrator()
        orch.topic_repo.get_topic.return_value = {
            "id": 1, "name": "AI Workflow", "keywords": ["ai", "workflow"],
        }
        orch.collector.collect.return_value = []

        cmd = JobCommand(job_type="collect", topic_id=1)
        result = orch.run_collect(cmd)

        self.assertTrue(result.success)
        self.assertEqual(result.stats.collected, 0)

    def test_collect_with_passed_items(self):
        orch = _make_mock_orchestrator()
        orch.topic_repo.get_topic.return_value = {
            "id": 1, "name": "AI Workflow", "keywords": ["ai"],
        }

        raw_item = _make_raw_item()
        orch.collector.collect.return_value = [raw_item]

        # Processor 返回 passed
        from processor.models import ProcessingResult
        mock_result = MagicMock(spec=ProcessingResult)
        mock_result.status = "passed"
        mock_result.normalized_item = raw_item
        mock_result.analysis_input = _make_analysis_input()
        mock_result.content_fingerprint = "abc123"
        mock_result.duplicate_info = None
        mock_result.filter_info = None

        orch.processor.process_batch.return_value = [mock_result]
        orch.source_repo.create_source.return_value = 1

        cmd = JobCommand(job_type="collect", topic_id=1)
        result = orch.run_collect(cmd)

        self.assertTrue(result.success)
        self.assertEqual(result.stats.collected, 1)
        self.assertEqual(result.stats.passed, 1)
        orch.source_repo.create_source.assert_called_once()

    def test_collect_with_duplicate_items(self):
        orch = _make_mock_orchestrator()
        orch.topic_repo.get_topic.return_value = {
            "id": 1, "name": "Test", "keywords": ["test"],
        }

        raw_item = _make_raw_item()
        orch.collector.collect.return_value = [raw_item]

        mock_result = MagicMock()
        mock_result.status = "duplicate"
        mock_result.normalized_item = raw_item
        mock_result.analysis_input = None
        mock_result.duplicate_info = {"type": "url", "duplicate_source_id": 42}
        mock_result.filter_info = None
        mock_result.content_fingerprint = "abc123"

        orch.processor.process_batch.return_value = [mock_result]

        cmd = JobCommand(job_type="collect", topic_id=1)
        result = orch.run_collect(cmd)

        self.assertTrue(result.success)
        self.assertEqual(result.stats.duplicated, 1)
        orch.duplicate_repo.create_duplicate_record.assert_called_once()

    def test_collect_with_filtered_items(self):
        orch = _make_mock_orchestrator()
        orch.topic_repo.get_topic.return_value = {
            "id": 1, "name": "Test", "keywords": ["test"],
        }

        raw_item = _make_raw_item()
        orch.collector.collect.return_value = [raw_item]

        mock_result = MagicMock()
        mock_result.status = "filtered"
        mock_result.normalized_item = raw_item
        mock_result.analysis_input = None
        mock_result.duplicate_info = None
        mock_result.filter_info = {
            "reason": "low_quality",
            "quality_score": 0.1,
            "checks": {"has_description": False},
        }
        mock_result.content_fingerprint = "abc123"

        orch.processor.process_batch.return_value = [mock_result]

        cmd = JobCommand(job_type="collect", topic_id=1)
        result = orch.run_collect(cmd)

        self.assertTrue(result.success)
        self.assertEqual(result.stats.filtered, 1)
        orch.filtered_repo.create_filtered_record.assert_called_once()

    def test_collect_keywords_override(self):
        orch = _make_mock_orchestrator()
        orch.topic_repo.get_topic.return_value = {
            "id": 1, "name": "Test", "keywords": ["default"],
        }
        orch.collector.collect.return_value = []

        cmd = JobCommand(
            job_type="collect",
            topic_id=1,
            keywords_override=["override_kw"],
        )
        result = orch.run_collect(cmd)

        # 验证使用了 override keywords
        call_args = orch.collector.collect.call_args
        query = call_args[0][0]
        self.assertEqual(query.keywords, ["override_kw"])


# ------------------------------------------------------------------ #
#  Orchestrator: Analyze Pipeline 测试
# ------------------------------------------------------------------ #


class TestOrchestratorAnalyze(unittest.TestCase):
    """测试 Orchestrator.run_analyze 编排逻辑。"""

    def test_analyze_no_pending(self):
        orch = _make_mock_orchestrator()
        orch.source_repo.get_sources_by_status.return_value = []

        cmd = JobCommand(job_type="analyze", topic_id=0)
        result = orch.run_analyze(cmd)

        self.assertTrue(result.success)
        self.assertEqual(result.stats.analyzed, 0)

    def test_analyze_success(self):
        orch = _make_mock_orchestrator()
        orch.config.analyze_delay = 0  # 测试不等待

        pending_source = {
            "id": 1,
            "topic_id": 1,
            "title": "Test Repo",
            "url": "https://github.com/test/repo",
            "description": "test",
            "cleaned_content_excerpt": "content",
            "raw_text_length": 100,
            "initial_quality_score": 0.8,
            "external_id": "github:test/repo",
            "content_fingerprint": "fp123",
            "metadata": {"stars": 100},
        }
        orch.source_repo.get_sources_by_status.return_value = [pending_source]
        orch.topic_repo.get_name.return_value = "AI Workflow"

        # Dify 返回成功
        mock_dify_result = MagicMock()
        mock_dify_result.succeeded = True
        mock_dify_result.workflow_run_id = "run_123"
        mock_dify_result.summary = "A test summary"
        mock_dify_result.relevance_score = 0.85
        mock_dify_result.quality_score = 0.9
        mock_dify_result.tags = ["ai", "workflow"]
        mock_dify_result.raw_response = {}
        mock_dify_result.analyzed_at = datetime.now(timezone.utc)
        orch.dify_client.analyze.return_value = mock_dify_result

        cmd = JobCommand(job_type="analyze", topic_id=0)
        result = orch.run_analyze(cmd)

        self.assertTrue(result.success)
        self.assertEqual(result.stats.analyzed, 1)
        orch.analysis_repo.save_analysis_result.assert_called_once()
        orch.source_repo.update_status.assert_called_with(1, "analyzed")

    def test_analyze_failure(self):
        orch = _make_mock_orchestrator()
        orch.config.analyze_delay = 0

        pending_source = {
            "id": 2,
            "topic_id": 1,
            "title": "Failed Repo",
            "url": "https://github.com/fail/repo",
            "description": "test",
            "cleaned_content_excerpt": "content",
            "raw_text_length": 50,
            "initial_quality_score": 0.5,
            "external_id": "github:fail/repo",
            "content_fingerprint": "fp456",
            "metadata": {},
        }
        orch.source_repo.get_sources_by_status.return_value = [pending_source]
        orch.topic_repo.get_name.return_value = "Test"

        # Dify 返回失败
        mock_dify_result = MagicMock()
        mock_dify_result.succeeded = False
        mock_dify_result.error = "Timeout"
        orch.dify_client.analyze.return_value = mock_dify_result

        cmd = JobCommand(job_type="analyze", topic_id=0)
        result = orch.run_analyze(cmd)

        self.assertTrue(result.success)  # Pipeline 本身成功
        self.assertEqual(result.stats.analysis_failed, 1)
        orch.source_repo.update_status.assert_called_with(2, "analysis_failed")

    def test_analyze_by_topic(self):
        orch = _make_mock_orchestrator()
        orch.source_repo.get_sources_by_topic.return_value = []

        cmd = JobCommand(job_type="analyze", topic_id=5)
        result = orch.run_analyze(cmd)

        self.assertTrue(result.success)
        orch.source_repo.get_sources_by_topic.assert_called_once_with(
            topic_id=5, status="pending_analysis", limit=20,
        )


# ------------------------------------------------------------------ #
#  Orchestrator: Report Pipeline 测试
# ------------------------------------------------------------------ #


class TestOrchestratorReport(unittest.TestCase):
    def test_report_not_implemented(self):
        orch = _make_mock_orchestrator()

        cmd = JobCommand(job_type="report", topic_id=1)
        result = orch.run_report(cmd)

        self.assertFalse(result.success)
        self.assertIn("not implemented", result.error)


# ------------------------------------------------------------------ #
#  Orchestrator: execute 路由测试
# ------------------------------------------------------------------ #


class TestOrchestratorExecute(unittest.TestCase):
    def test_execute_routes_collect(self):
        orch = _make_mock_orchestrator()
        orch.topic_repo.get_topic.return_value = {
            "id": 1, "name": "T", "keywords": ["k"],
        }
        orch.collector.collect.return_value = []

        cmd = JobCommand(job_type="collect", topic_id=1)
        result = orch.execute(cmd)
        self.assertTrue(result.success)

    def test_execute_routes_analyze(self):
        orch = _make_mock_orchestrator()
        orch.source_repo.get_sources_by_status.return_value = []

        cmd = JobCommand(job_type="analyze", topic_id=0)
        result = orch.execute(cmd)
        self.assertTrue(result.success)

    def test_execute_routes_report(self):
        orch = _make_mock_orchestrator()

        cmd = JobCommand(job_type="report", topic_id=1)
        result = orch.execute(cmd)
        self.assertFalse(result.success)


# ------------------------------------------------------------------ #
#  Scheduler 测试
# ------------------------------------------------------------------ #


class TestScheduler(unittest.TestCase):
    def test_disabled_scheduler(self):
        orch = _make_mock_orchestrator()
        config = SchedulerConfig(enabled=False)
        sched = Scheduler(orchestrator=orch, config=config)
        sched.start()
        self.assertFalse(sched.running)

    def test_trigger_manual(self):
        orch = _make_mock_orchestrator()
        orch.topic_repo.get_topic.return_value = {
            "id": 1, "name": "T", "keywords": ["k"],
        }
        orch.collector.collect.return_value = []

        config = SchedulerConfig(enabled=False)
        sched = Scheduler(orchestrator=orch, config=config)

        cmd = JobCommand(job_type="collect", topic_id=1)
        result = sched.trigger_manual(cmd)

        self.assertTrue(result.success)
        self.assertEqual(cmd.trigger, "manual")

    def test_daily_collect_no_topics(self):
        orch = _make_mock_orchestrator()
        orch.topic_repo.list_topics.return_value = []

        config = SchedulerConfig(enabled=False)
        sched = Scheduler(orchestrator=orch, config=config)
        sched._daily_collect()

        orch.topic_repo.list_topics.assert_called_once()

    def test_daily_collect_with_topics(self):
        orch = _make_mock_orchestrator()
        orch.topic_repo.list_topics.return_value = [
            {"id": 1, "name": "Topic A"},
            {"id": 2, "name": "Topic B"},
        ]
        orch.topic_repo.get_topic.side_effect = lambda tid: {
            "id": tid, "name": f"Topic {tid}", "keywords": ["kw"],
        }
        orch.collector.collect.return_value = []

        config = SchedulerConfig(enabled=False)
        sched = Scheduler(orchestrator=orch, config=config)
        sched._daily_collect()

        # 应该为每个 topic 调用一次 execute
        self.assertEqual(orch.topic_repo.get_topic.call_count, 2)

    def test_daily_analyze(self):
        orch = _make_mock_orchestrator()
        orch.source_repo.get_sources_by_status.return_value = []

        config = SchedulerConfig(enabled=False)
        sched = Scheduler(orchestrator=orch, config=config)
        sched._daily_analyze()

        orch.source_repo.get_sources_by_status.assert_called_once()


if __name__ == "__main__":
    unittest.main()
