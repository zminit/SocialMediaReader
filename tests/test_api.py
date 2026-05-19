"""API 模块单元测试。

使用 FastAPI TestClient + 内存 SQLite 测试所有端点。
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch

# 设置测试环境变量（在导入 api 前）
os.environ.setdefault("STORAGE_DB_PATH", ":memory:")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

from fastapi.testclient import TestClient

from api.config import APIConfig
from api.dependencies import AppState, _app_state, get_app_state
from storage.config import StorageConfig
from scheduler.config import SchedulerConfig, OrchestratorConfig


# ------------------------------------------------------------------ #
#  Fixtures
# ------------------------------------------------------------------ #


@pytest.fixture(scope="module")
def app_state():
    """模块级 AppState，使用内存 SQLite。"""
    state = AppState()
    state.init_storage(StorageConfig(db_path=":memory:"))
    return state


@pytest.fixture(scope="module")
def client(app_state):
    """模块级 TestClient。

    用 dependency_overrides 替换全局 AppState，
    避免 lifespan 真正初始化外部依赖。
    """
    from api.app import create_app
    from api import dependencies

    # 创建 app 但跳过 lifespan（用 None）
    config = APIConfig(title="Test API", version="test")
    app = create_app.__wrapped__(config) if hasattr(create_app, '__wrapped__') else _create_test_app(config, app_state)

    # Override 依赖
    app.dependency_overrides[get_app_state] = lambda: app_state
    app.dependency_overrides[dependencies.get_topic_repo] = lambda: app_state.topic_repo
    app.dependency_overrides[dependencies.get_source_repo] = lambda: app_state.source_repo
    app.dependency_overrides[dependencies.get_analysis_repo] = lambda: app_state.analysis_repo
    app.dependency_overrides[dependencies.get_duplicate_repo] = lambda: app_state.duplicate_repo
    app.dependency_overrides[dependencies.get_filtered_repo] = lambda: app_state.filtered_repo

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def _create_test_app(config, state):
    """创建不含 lifespan 的测试 app。"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from api.routers import health, topics, sources, analysis, jobs, stats

    app = FastAPI(title=config.title, version=config.version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(topics.router)
    app.include_router(sources.router)
    app.include_router(analysis.router)
    # jobs 和 stats 需要 scheduler/orchestrator，单独测
    app.include_router(stats.router)
    return app


# ================================================================== #
#  APIConfig Tests
# ================================================================== #


class TestAPIConfig:
    def test_defaults(self):
        config = APIConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.debug is False
        assert config.cors_origins == ["*"]

    def test_from_env(self):
        with patch.dict(os.environ, {
            "API_HOST": "127.0.0.1",
            "API_PORT": "9000",
            "API_DEBUG": "true",
            "API_CORS_ORIGINS": "http://a.com, http://b.com",
        }):
            config = APIConfig.from_env()
            assert config.host == "127.0.0.1"
            assert config.port == 9000
            assert config.debug is True
            assert config.cors_origins == ["http://a.com", "http://b.com"]


# ================================================================== #
#  Health Tests
# ================================================================== #


class TestHealth:
    def test_health_check(self, client, app_state):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("healthy", "degraded")
        assert "checks" in data
        assert data["checks"]["storage"] is True


# ================================================================== #
#  Topics Tests
# ================================================================== #


class TestTopics:
    def test_list_topics_empty(self, client):
        resp = client.get("/api/topics")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_topic(self, client):
        resp = client.post("/api/topics", json={
            "name": "AI Workflow",
            "keywords": ["langchain", "dify", "agent"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "AI Workflow"
        assert data["keywords"] == ["langchain", "dify", "agent"]
        assert "id" in data

    def test_create_topic_minimal(self, client):
        resp = client.post("/api/topics", json={"name": "Python Tools"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Python Tools"
        assert data["keywords"] == []

    def test_create_topic_empty_name(self, client):
        resp = client.post("/api/topics", json={"name": ""})
        assert resp.status_code == 422  # validation error

    def test_get_topic(self, client):
        # 先创建
        create_resp = client.post("/api/topics", json={"name": "Test Get"})
        topic_id = create_resp.json()["id"]

        resp = client.get(f"/api/topics/{topic_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Get"

    def test_get_topic_not_found(self, client):
        resp = client.get("/api/topics/9999")
        assert resp.status_code == 404

    def test_update_topic(self, client):
        create_resp = client.post("/api/topics", json={
            "name": "Before Update",
            "keywords": ["old"],
        })
        topic_id = create_resp.json()["id"]

        resp = client.put(f"/api/topics/{topic_id}", json={
            "name": "After Update",
            "keywords": ["new1", "new2"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "After Update"
        assert data["keywords"] == ["new1", "new2"]

    def test_update_topic_not_found(self, client):
        resp = client.put("/api/topics/9999", json={"name": "X"})
        assert resp.status_code == 404

    def test_list_topics_after_create(self, client):
        resp = client.get("/api/topics")
        assert resp.status_code == 200
        topics = resp.json()
        assert len(topics) >= 1
        assert any(t["name"] == "AI Workflow" for t in topics)


# ================================================================== #
#  Sources Tests
# ================================================================== #


class TestSources:
    def test_list_sources_empty(self, client):
        resp = client.get("/api/sources")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_sources_with_status(self, client):
        resp = client.get("/api/sources?status=pending_analysis")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_source_not_found(self, client):
        resp = client.get("/api/sources/9999")
        assert resp.status_code == 404

    def test_list_sources_with_topic(self, client):
        resp = client.get("/api/sources?topic_id=1")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_and_get_source(self, client, app_state):
        """通过 repo 直接写入 source，然后通过 API 查询。"""
        from datetime import datetime, timezone

        # 先确保有 topic
        topic_id = app_state.topic_repo.create_topic("Source Test Topic")

        source_id = app_state.source_repo.create_source(
            topic_id=topic_id,
            source_type="github",
            source_subtype="github_repo",
            external_id="github:test/repo",
            url="https://github.com/test/repo",
            canonical_url="https://github.com/test/repo",
            title="Test Repo",
            collected_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
            content_fingerprint="abc123",
            status="analyzed",
        )

        resp = client.get(f"/api/sources/{source_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Repo"
        assert data["external_id"] == "github:test/repo"


# ================================================================== #
#  Analysis Tests
# ================================================================== #


class TestAnalysis:
    def test_list_analysis_empty(self, client):
        resp = client.get("/api/analysis?topic_id=1")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_analysis_missing_topic_id(self, client):
        resp = client.get("/api/analysis")
        assert resp.status_code == 422  # topic_id is required

    def test_get_analysis_not_found(self, client):
        resp = client.get("/api/analysis/source/9999")
        assert resp.status_code == 404

    def test_create_and_get_analysis(self, client, app_state):
        """通过 repo 写入分析结果，通过 API 查询。"""
        from datetime import datetime, timezone

        topic_id = app_state.topic_repo.create_topic("Analysis Test Topic")

        source_id = app_state.source_repo.create_source(
            topic_id=topic_id,
            source_type="github",
            source_subtype="github_repo",
            external_id="github:analysis/test",
            url="https://github.com/analysis/test",
            canonical_url="https://github.com/analysis/test",
            title="Analysis Test Repo",
            collected_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
            content_fingerprint="def456",
            status="analyzed",
        )

        app_state.analysis_repo.save_analysis_result(
            source_id=source_id,
            summary="A great AI tool",
            relevance_score=0.85,
            quality_score=0.7,
            tags=["ai", "workflow"],
            analyzed_at=datetime.now(timezone.utc),
        )

        # 查询 by source
        resp = client.get(f"/api/analysis/source/{source_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"] == "A great AI tool"
        assert data["relevance_score"] == 0.85
        assert data["tags"] == ["ai", "workflow"]

        # 查询 by topic
        resp = client.get(f"/api/analysis?topic_id={topic_id}")
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1
        assert results[0]["relevance_score"] >= 0.85

        # 过滤 min_relevance
        resp = client.get(f"/api/analysis?topic_id={topic_id}&min_relevance=0.9")
        assert resp.status_code == 200
        # 0.85 < 0.9, so filtered out
        assert len(resp.json()) == 0


# ================================================================== #
#  Stats Tests
# ================================================================== #


class TestStats:
    def test_get_stats(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data
        assert "duplicates" in data
        assert "filtered" in data
        assert "pipeline_total" in data
        assert isinstance(data["sources"]["total"], int)


# ================================================================== #
#  Jobs Tests (with mocks)
# ================================================================== #


class TestJobs:
    def test_scheduler_status(self):
        """测试 scheduler status 端点（需要 mock scheduler）。"""
        from api.routers import jobs
        from api import dependencies

        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        mock_scheduler.config = SchedulerConfig(enabled=False)
        mock_scheduler._scheduler = None

        app = _create_jobs_test_app(mock_scheduler)
        with TestClient(app) as c:
            resp = c.get("/api/jobs/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["running"] is False
            assert data["enabled"] is False

    def test_list_jobs_empty(self):
        mock_scheduler = MagicMock()
        mock_scheduler._scheduler = None

        app = _create_jobs_test_app(mock_scheduler)
        with TestClient(app) as c:
            resp = c.get("/api/jobs")
            assert resp.status_code == 200
            assert resp.json() == []

    def test_trigger_collect(self):
        from scheduler.models import JobResult, PipelineStats
        from datetime import datetime, timezone

        mock_scheduler = MagicMock()
        mock_result = JobResult(
            job_type="collect",
            topic_id=1,
            success=True,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            stats=PipelineStats(collected=10, passed=8, duplicated=1, filtered=1),
        )
        mock_scheduler.trigger_manual.return_value = mock_result

        app = _create_jobs_test_app(mock_scheduler)
        with TestClient(app) as c:
            resp = c.post("/api/jobs/trigger", json={
                "job_type": "collect",
                "topic_id": 1,
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["stats"]["collected"] == 10
            assert data["stats"]["passed"] == 8

    def test_trigger_analyze(self):
        from scheduler.models import JobResult, PipelineStats
        from datetime import datetime, timezone

        mock_scheduler = MagicMock()
        mock_result = JobResult(
            job_type="analyze",
            topic_id=0,
            success=True,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            stats=PipelineStats(analyzed=5),
        )
        mock_scheduler.trigger_manual.return_value = mock_result

        app = _create_jobs_test_app(mock_scheduler)
        with TestClient(app) as c:
            resp = c.post("/api/jobs/trigger", json={
                "job_type": "analyze",
                "topic_id": 0,
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["success"] is True
            assert data["stats"]["analyzed"] == 5

    def test_trigger_invalid_type(self):
        mock_scheduler = MagicMock()

        app = _create_jobs_test_app(mock_scheduler)
        with TestClient(app) as c:
            resp = c.post("/api/jobs/trigger", json={
                "job_type": "invalid",
                "topic_id": 1,
            })
            assert resp.status_code == 400


# ------------------------------------------------------------------ #
#  Helper
# ------------------------------------------------------------------ #


def _create_jobs_test_app(mock_scheduler):
    """创建只含 jobs router 的测试 app。"""
    from fastapi import FastAPI
    from api.routers import jobs
    from api import dependencies

    app = FastAPI()
    app.include_router(jobs.router)
    app.dependency_overrides[dependencies.get_scheduler] = lambda: mock_scheduler
    return app


# ================================================================== #
#  AppState Tests
# ================================================================== #


class TestAppState:
    def test_init_storage(self):
        state = AppState()
        state.init_storage(StorageConfig(db_path=":memory:"))
        assert state.db is not None
        assert state.topic_repo is not None
        assert state.source_repo is not None

    def test_init_orchestrator_without_storage(self):
        state = AppState()
        with pytest.raises(RuntimeError, match="init_storage"):
            state.init_orchestrator()

    def test_init_scheduler_without_orchestrator(self):
        state = AppState()
        state.init_storage(StorageConfig(db_path=":memory:"))
        with pytest.raises(RuntimeError, match="init_orchestrator"):
            state.init_scheduler()

    def test_init_orchestrator(self):
        state = AppState()
        state.init_storage(StorageConfig(db_path=":memory:"))
        # Collector 和 DifyClient 因缺少 token 会为 None，但不应报错
        state.init_orchestrator()
        assert state.orchestrator is not None

    def test_full_lifecycle(self):
        state = AppState()
        state.init_storage(StorageConfig(db_path=":memory:"))
        state.init_orchestrator()
        state.init_scheduler(SchedulerConfig(enabled=False))
        state.start_scheduler()  # disabled, should not fail
        state.shutdown()

    def test_shutdown_idempotent(self):
        state = AppState()
        state.shutdown()  # should not raise
