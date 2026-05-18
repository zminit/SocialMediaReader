"""Storage 模块测试。"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone

from storage.config import StorageConfig
from storage.database import Database
from storage.topic_repository import SQLiteTopicRepository, TopicNotFoundError
from storage.dedup_repository import SQLiteDedupRepository
from storage.source_repository import SQLiteSourceRepository
from storage.duplicate_repository import SQLiteDuplicateRecordRepository
from storage.filtered_repository import SQLiteFilteredRecordRepository
from storage.analysis_repository import SQLiteAnalysisResultRepository


class StorageTestBase(unittest.TestCase):
    """Storage 测试基类：每个测试用临时数据库。"""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.config = StorageConfig(db_path=self.tmp.name)
        self.db = Database(self.config)
        self.db.initialize()

    def tearDown(self):
        self.db.close()
        os.unlink(self.tmp.name)
        # WAL 和 SHM 文件
        for suffix in ("-wal", "-shm"):
            path = self.tmp.name + suffix
            if os.path.exists(path):
                os.unlink(path)


class TestDatabase(StorageTestBase):
    """数据库初始化测试。"""

    def test_tables_created(self):
        conn = self.db.get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row["name"] for row in cursor.fetchall()}
        expected = {
            "topics",
            "sources",
            "duplicate_records",
            "filtered_records",
            "analysis_results",
            "schema_version",
        }
        self.assertTrue(expected.issubset(tables), f"Missing tables: {expected - tables}")

    def test_schema_version(self):
        conn = self.db.get_connection()
        cursor = conn.execute("SELECT MAX(version) as v FROM schema_version")
        self.assertEqual(cursor.fetchone()["v"], 1)

    def test_reinitialize_is_idempotent(self):
        """重复 initialize 不报错。"""
        self.db.initialize()
        self.db.initialize()

    def test_context_manager(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        try:
            config = StorageConfig(db_path=path)
            with Database(config) as db:
                conn = db.get_connection()
                cursor = conn.execute("SELECT 1 as x")
                self.assertEqual(cursor.fetchone()["x"], 1)
        finally:
            os.unlink(path)
            for suffix in ("-wal", "-shm"):
                p = path + suffix
                if os.path.exists(p):
                    os.unlink(p)


class TestTopicRepository(StorageTestBase):
    """TopicRepository 测试。"""

    def setUp(self):
        super().setUp()
        self.repo = SQLiteTopicRepository(self.db)

    def test_create_and_get_name(self):
        topic_id = self.repo.create_topic("AI 工作流搭建", keywords=["AI", "workflow"])
        self.assertIsInstance(topic_id, int)
        self.assertEqual(self.repo.get_name(topic_id), "AI 工作流搭建")

    def test_get_name_not_found(self):
        with self.assertRaises(TopicNotFoundError):
            self.repo.get_name(9999)

    def test_get_topic(self):
        topic_id = self.repo.create_topic("测试主题", keywords=["test"])
        topic = self.repo.get_topic(topic_id)
        self.assertIsNotNone(topic)
        self.assertEqual(topic["name"], "测试主题")
        self.assertEqual(topic["keywords"], ["test"])

    def test_list_topics(self):
        self.repo.create_topic("主题A")
        self.repo.create_topic("主题B")
        topics = self.repo.list_topics()
        self.assertEqual(len(topics), 2)
        names = [t["name"] for t in topics]
        self.assertIn("主题A", names)
        self.assertIn("主题B", names)

    def test_update_topic(self):
        topic_id = self.repo.create_topic("原名")
        self.repo.update_topic(topic_id, name="新名")
        self.assertEqual(self.repo.get_name(topic_id), "新名")

    def test_unique_name_constraint(self):
        self.repo.create_topic("唯一名")
        with self.assertRaises(Exception):  # sqlite3.IntegrityError
            self.repo.create_topic("唯一名")


class TestDedupRepository(StorageTestBase):
    """DedupRepository 测试。"""

    def setUp(self):
        super().setUp()
        self.topic_repo = SQLiteTopicRepository(self.db)
        self.source_repo = SQLiteSourceRepository(self.db)
        self.dedup_repo = SQLiteDedupRepository(self.db)

        # 创建测试主题和 source
        self.topic_id = self.topic_repo.create_topic("测试主题")
        now = datetime.now(timezone.utc)
        self.source_id = self.source_repo.create_source(
            topic_id=self.topic_id,
            source_type="github",
            source_subtype="github_repo",
            external_id="github:test/repo",
            url="https://github.com/test/repo",
            canonical_url="https://github.com/test/repo",
            title="Test Repo",
            collected_at=now,
            processed_at=now,
            content_fingerprint="abc123fingerprint",
            metadata={"stars": 100},
        )

    def test_find_by_url(self):
        result = self.dedup_repo.find_by_url("https://github.com/test/repo")
        self.assertEqual(result, self.source_id)

    def test_find_by_url_not_found(self):
        result = self.dedup_repo.find_by_url("https://github.com/other/repo")
        self.assertIsNone(result)

    def test_find_by_external_id(self):
        result = self.dedup_repo.find_by_external_id("github:test/repo")
        self.assertEqual(result, self.source_id)

    def test_find_by_external_id_not_found(self):
        result = self.dedup_repo.find_by_external_id("github:other/repo")
        self.assertIsNone(result)

    def test_find_by_fingerprint(self):
        result = self.dedup_repo.find_by_fingerprint("abc123fingerprint")
        self.assertEqual(result, self.source_id)

    def test_find_by_fingerprint_not_found(self):
        result = self.dedup_repo.find_by_fingerprint("nonexistent")
        self.assertIsNone(result)


class TestSourceRepository(StorageTestBase):
    """SourceRepository 测试。"""

    def setUp(self):
        super().setUp()
        self.topic_repo = SQLiteTopicRepository(self.db)
        self.source_repo = SQLiteSourceRepository(self.db)
        self.topic_id = self.topic_repo.create_topic("测试主题")

    def _create_test_source(self, external_id="github:test/repo", **kwargs):
        now = datetime.now(timezone.utc)
        defaults = dict(
            topic_id=self.topic_id,
            source_type="github",
            source_subtype="github_repo",
            external_id=external_id,
            url=f"https://github.com/{external_id.split(':')[1]}",
            canonical_url=f"https://github.com/{external_id.split(':')[1]}",
            title=f"Test {external_id}",
            collected_at=now,
            processed_at=now,
            content_fingerprint=f"fp_{external_id}",
            metadata={"stars": 50},
        )
        defaults.update(kwargs)
        return self.source_repo.create_source(**defaults)

    def test_create_and_get(self):
        source_id = self._create_test_source()
        source = self.source_repo.get_source(source_id)
        self.assertIsNotNone(source)
        self.assertEqual(source["source_type"], "github")
        self.assertEqual(source["metadata"]["stars"], 50)

    def test_get_nonexistent(self):
        self.assertIsNone(self.source_repo.get_source(9999))

    def test_update_status(self):
        source_id = self._create_test_source()
        self.source_repo.update_status(source_id, "analyzed")
        source = self.source_repo.get_source(source_id)
        self.assertEqual(source["status"], "analyzed")

    def test_get_by_status(self):
        self._create_test_source("github:a/1")
        self._create_test_source("github:a/2")
        sources = self.source_repo.get_sources_by_status("pending_analysis")
        self.assertEqual(len(sources), 2)

    def test_count_by_status(self):
        self._create_test_source("github:b/1")
        s2 = self._create_test_source("github:b/2")
        self.source_repo.update_status(s2, "analyzed")
        counts = self.source_repo.count_by_status()
        self.assertEqual(counts.get("pending_analysis"), 1)
        self.assertEqual(counts.get("analyzed"), 1)

    def test_unique_external_id_constraint(self):
        self._create_test_source("github:unique/repo")
        with self.assertRaises(Exception):
            self._create_test_source("github:unique/repo")

    def test_raw_text_truncated_is_bool(self):
        source_id = self._create_test_source(
            external_id="github:c/1",
            raw_text="some text",
            raw_text_truncated=True,
            raw_text_length=1000,
        )
        source = self.source_repo.get_source(source_id)
        self.assertIs(source["raw_text_truncated"], True)


class TestDuplicateRecordRepository(StorageTestBase):
    """DuplicateRecordRepository 测试。"""

    def setUp(self):
        super().setUp()
        self.topic_repo = SQLiteTopicRepository(self.db)
        self.source_repo = SQLiteSourceRepository(self.db)
        self.dup_repo = SQLiteDuplicateRecordRepository(self.db)

        self.topic_id = self.topic_repo.create_topic("测试")
        now = datetime.now(timezone.utc)
        self.source_id = self.source_repo.create_source(
            topic_id=self.topic_id,
            source_type="github",
            source_subtype="github_repo",
            external_id="github:orig/repo",
            url="https://github.com/orig/repo",
            canonical_url="https://github.com/orig/repo",
            title="Original",
            collected_at=now,
            processed_at=now,
            content_fingerprint="orig_fp",
        )

    def test_create_and_count(self):
        now = datetime.now(timezone.utc)
        self.dup_repo.create_duplicate_record(
            topic_id=self.topic_id,
            duplicate_type="url",
            duplicate_source_id=self.source_id,
            external_id="github:dup/repo",
            url="https://github.com/dup/repo",
            canonical_url="https://github.com/orig/repo",
            title="Duplicate",
            content_fingerprint="dup_fp",
            collected_at=now,
        )
        counts = self.dup_repo.count_by_type()
        self.assertEqual(counts.get("url"), 1)

    def test_list_recent(self):
        now = datetime.now(timezone.utc)
        self.dup_repo.create_duplicate_record(
            topic_id=self.topic_id,
            duplicate_type="content",
            duplicate_source_id=self.source_id,
            external_id="github:dup2/repo",
            url="https://github.com/dup2/repo",
            canonical_url="https://github.com/dup2/repo",
            title="Dup2",
            content_fingerprint="dup2_fp",
            collected_at=now,
        )
        records = self.dup_repo.list_recent(10)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["duplicate_type"], "content")


class TestFilteredRecordRepository(StorageTestBase):
    """FilteredRecordRepository 测试。"""

    def setUp(self):
        super().setUp()
        self.topic_repo = SQLiteTopicRepository(self.db)
        self.filtered_repo = SQLiteFilteredRecordRepository(self.db)
        self.topic_id = self.topic_repo.create_topic("测试")

    def test_create_and_count(self):
        now = datetime.now(timezone.utc)
        self.filtered_repo.create_filtered_record(
            topic_id=self.topic_id,
            filter_reason="no_readme",
            quality_score=0.0,
            checks={"has_content": False, "has_title": True},
            external_id="github:bad/repo",
            url="https://github.com/bad/repo",
            canonical_url="https://github.com/bad/repo",
            title="Bad Repo",
            content_fingerprint="bad_fp",
            collected_at=now,
        )
        counts = self.filtered_repo.count_by_reason()
        self.assertEqual(counts.get("no_readme"), 1)

    def test_checks_stored_as_dict(self):
        now = datetime.now(timezone.utc)
        self.filtered_repo.create_filtered_record(
            topic_id=self.topic_id,
            filter_reason="archived_repo",
            quality_score=0.0,
            checks={"not_archived": False},
            external_id="github:old/repo",
            url="https://github.com/old/repo",
            canonical_url="https://github.com/old/repo",
            title="Old Repo",
            content_fingerprint="old_fp",
            collected_at=now,
        )
        records = self.filtered_repo.list_recent(10)
        self.assertIsInstance(records[0]["checks"], dict)
        self.assertFalse(records[0]["checks"]["not_archived"])


class TestAnalysisResultRepository(StorageTestBase):
    """AnalysisResultRepository 测试。"""

    def setUp(self):
        super().setUp()
        self.topic_repo = SQLiteTopicRepository(self.db)
        self.source_repo = SQLiteSourceRepository(self.db)
        self.analysis_repo = SQLiteAnalysisResultRepository(self.db)

        self.topic_id = self.topic_repo.create_topic("AI 工作流")
        now = datetime.now(timezone.utc)
        self.source_id = self.source_repo.create_source(
            topic_id=self.topic_id,
            source_type="github",
            source_subtype="github_repo",
            external_id="github:good/repo",
            url="https://github.com/good/repo",
            canonical_url="https://github.com/good/repo",
            title="Good Repo",
            collected_at=now,
            processed_at=now,
            content_fingerprint="good_fp",
            initial_quality_score=0.75,
        )

    def test_save_and_get(self):
        now = datetime.now(timezone.utc)
        result_id = self.analysis_repo.save_analysis_result(
            source_id=self.source_id,
            workflow_run_id="wf_123",
            summary="这是一个优秀的 AI 工作流项目",
            relevance_score=0.85,
            quality_score=0.90,
            tags=["AI", "workflow", "automation"],
            raw_response={"data": {"status": "succeeded"}},
            analyzed_at=now,
        )
        self.assertIsInstance(result_id, int)

        result = self.analysis_repo.get_by_source_id(self.source_id)
        self.assertIsNotNone(result)
        self.assertEqual(result["summary"], "这是一个优秀的 AI 工作流项目")
        self.assertAlmostEqual(result["relevance_score"], 0.85)
        self.assertEqual(result["tags"], ["AI", "workflow", "automation"])

    def test_get_nonexistent(self):
        self.assertIsNone(self.analysis_repo.get_by_source_id(9999))

    def test_list_by_topic(self):
        now = datetime.now(timezone.utc)
        self.analysis_repo.save_analysis_result(
            source_id=self.source_id,
            summary="Summary",
            relevance_score=0.8,
            quality_score=0.7,
            tags=["AI"],
            analyzed_at=now,
        )
        # 更新 source 状态
        self.source_repo.update_status(self.source_id, "analyzed")

        results = self.analysis_repo.list_by_topic(self.topic_id, min_relevance=0.5)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Good Repo")

    def test_unique_source_constraint(self):
        """每个 source 只能有一个分析结果。"""
        now = datetime.now(timezone.utc)
        self.analysis_repo.save_analysis_result(
            source_id=self.source_id,
            summary="First",
            analyzed_at=now,
        )
        with self.assertRaises(Exception):
            self.analysis_repo.save_analysis_result(
                source_id=self.source_id,
                summary="Second",
                analyzed_at=now,
            )


if __name__ == "__main__":
    unittest.main()
