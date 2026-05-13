"""
Collector 模块单元测试

使用 Mock 测试核心逻辑，不依赖真实 GitHub API
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
import httpx

from collector import GitHubCollector, SourceQuery, CollectorConfig
from collector.base import RateLimitExceeded, AuthenticationError
from collector.models import RawItem


@pytest.fixture
def mock_config():
    """Mock 配置"""
    return CollectorConfig(
        github_token="test_token_12345678",
        github_api_timeout=30,
        github_max_retries=3,
        github_rate_limit_buffer=100,
        save_raw_payload=False,
        log_level="INFO"
    )


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.Client"""
    with patch('collector.github_collector.httpx.Client') as mock_client:
        yield mock_client


def test_source_query_validation():
    """测试 SourceQuery 参数验证"""
    # 正常创建
    query = SourceQuery(
        topic_id=1,
        keywords=["test"],
        source_type="github"
    )
    assert query.topic_id == 1
    assert query.keywords == ["test"]
    
    # 空关键词
    with pytest.raises(ValueError, match="keywords cannot be empty"):
        SourceQuery(
            topic_id=1,
            keywords=[],
            source_type="github"
        )
    
    # 无效的 source_type
    with pytest.raises(ValueError, match="source_type must be one of"):
        SourceQuery(
            topic_id=1,
            keywords=["test"],
            source_type="invalid"
        )
    
    # 无效的 sort_by
    with pytest.raises(ValueError, match="sort_by must be one of"):
        SourceQuery(
            topic_id=1,
            keywords=["test"],
            source_type="github",
            sort_by="invalid"
        )


def test_collector_config_validation(mock_config):
    """测试配置验证"""
    assert mock_config.validate() is True
    
    # 无效配置
    invalid_config = CollectorConfig(
        github_token="",
        github_api_timeout=-1
    )
    assert invalid_config.validate() is False


def test_sort_mapping():
    """测试 sort 参数映射"""
    assert GitHubCollector.SORT_MAPPING["best_match"] is None
    assert GitHubCollector.SORT_MAPPING["stars"] == "stars"
    assert GitHubCollector.SORT_MAPPING["forks"] == "forks"
    assert GitHubCollector.SORT_MAPPING["updated"] == "updated"


def test_github_collector_init(mock_config, mock_httpx_client):
    """测试 GitHubCollector 初始化"""
    # Mock rate_limit 响应
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "resources": {
            "core": {
                "remaining": 4500,
                "reset": 1234567890,
                "limit": 5000
            }
        }
    }
    
    mock_client_instance = Mock()
    mock_client_instance.get.return_value = mock_response
    mock_httpx_client.return_value = mock_client_instance
    
    collector = GitHubCollector(mock_config)
    
    assert collector.remaining == 4500
    assert collector.limit == 5000
    assert collector.reset_at == 1234567890


def test_rate_limit_status(mock_config, mock_httpx_client):
    """测试 rate limit 状态获取"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "resources": {
            "core": {
                "remaining": 4500,
                "reset": 1234567890,
                "limit": 5000
            }
        }
    }
    
    mock_client_instance = Mock()
    mock_client_instance.get.return_value = mock_response
    mock_httpx_client.return_value = mock_client_instance
    
    collector = GitHubCollector(mock_config)
    status = collector.get_rate_limit_status()
    
    assert status["remaining"] == 4500
    assert status["limit"] == 5000
    assert status["reset_at"] == 1234567890
    assert "reset_at_datetime" in status


def test_handle_response_401(mock_config, mock_httpx_client):
    """测试 401 认证失败处理"""
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.headers = {}
    
    mock_client_instance = Mock()
    mock_client_instance.get.return_value = mock_response
    mock_httpx_client.return_value = mock_client_instance
    
    collector = GitHubCollector(mock_config)
    
    with pytest.raises(AuthenticationError):
        collector._handle_response(mock_response)


def test_handle_response_403_rate_limit(mock_config, mock_httpx_client):
    """测试 403 rate limit 处理"""
    mock_response = Mock()
    mock_response.status_code = 403
    mock_response.text = "rate limit exceeded"
    mock_response.headers = {
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "1234567890"
    }
    
    mock_client_instance = Mock()
    mock_client_instance.get.return_value = mock_response
    mock_httpx_client.return_value = mock_client_instance
    
    collector = GitHubCollector(mock_config)
    
    with patch('time.sleep'):  # Mock sleep 避免真实等待
        with pytest.raises(RateLimitExceeded):
            collector._handle_response(mock_response)


def test_parse_repo(mock_config, mock_httpx_client):
    """测试 repo 数据解析"""
    mock_client_instance = Mock()
    mock_httpx_client.return_value = mock_client_instance
    
    collector = GitHubCollector(mock_config)
    
    # Mock repo 数据
    repo_data = {
        "full_name": "test/repo",
        "name": "repo",
        "owner": {"login": "test"},
        "html_url": "https://github.com/test/repo",
        "description": "Test repository",
        "stargazers_count": 100,
        "forks_count": 20,
        "watchers_count": 50,
        "open_issues_count": 5,
        "language": "Python",
        "topics": ["test", "demo"],
        "license": {"spdx_id": "MIT"},
        "fork": False,
        "archived": False,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-12-01T00:00:00Z",
        "pushed_at": "2024-12-15T00:00:00Z",
        "homepage": "https://example.com"
    }
    
    query = SourceQuery(
        topic_id=1,
        keywords=["test"],
        source_type="github"
    )
    
    raw_item = collector._parse_repo(repo_data, query)
    
    assert raw_item.topic_id == 1
    assert raw_item.source_type == "github"
    assert raw_item.source_subtype == "github_repo"
    assert raw_item.external_id == "github:test/repo"
    assert raw_item.title == "repo"
    assert raw_item.author == "test"
    assert raw_item.metadata["stars"] == 100
    assert raw_item.metadata["language"] == "Python"
    assert raw_item.metadata["activity_score"] > 0


def test_calculate_activity_score(mock_config, mock_httpx_client):
    """测试活跃度评分计算"""
    mock_client_instance = Mock()
    mock_httpx_client.return_value = mock_client_instance
    
    collector = GitHubCollector(mock_config)
    
    # 高活跃度 repo（最近推送，高 stars）
    repo_data_active = {
        "stargazers_count": 10000,
        "pushed_at": datetime.now(timezone.utc).isoformat()
    }
    score_active = collector._calculate_activity_score(repo_data_active)
    assert score_active > 0.5
    
    # 低活跃度 repo（很久没推送，低 stars）
    repo_data_inactive = {
        "stargazers_count": 10,
        "pushed_at": "2020-01-01T00:00:00Z"
    }
    score_inactive = collector._calculate_activity_score(repo_data_inactive)
    assert score_inactive < 0.5


def test_raw_item_validation():
    """测试 RawItem 验证"""
    # 正常创建
    item = RawItem(
        topic_id=1,
        source_type="github",
        source_subtype="github_repo",
        external_id="github:test/repo",
        url="https://github.com/test/repo",
        canonical_url="https://github.com/test/repo",
        title="Test Repo",
        author="test",
        description="Test",
        published_at=datetime.now(timezone.utc),
        collected_at=datetime.now(timezone.utc),
        raw_text=None,
        raw_text_truncated=False,
        raw_text_length=0
    )
    assert item.external_id == "github:test/repo"
    
    # 缺少必填字段
    with pytest.raises(ValueError, match="external_id is required"):
        RawItem(
            topic_id=1,
            source_type="github",
            source_subtype="github_repo",
            external_id="",
            url="https://github.com/test/repo",
            canonical_url="https://github.com/test/repo",
            title="Test",
            author="test",
            description="Test",
            published_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc),
            raw_text=None,
            raw_text_truncated=False,
            raw_text_length=0
        )


def test_raw_item_to_dict():
    """测试 RawItem 序列化"""
    now = datetime.now(timezone.utc)
    item = RawItem(
        topic_id=1,
        source_type="github",
        source_subtype="github_repo",
        external_id="github:test/repo",
        url="https://github.com/test/repo",
        canonical_url="https://github.com/test/repo",
        title="Test",
        author="test",
        description="Test",
        published_at=now,
        collected_at=now,
        raw_text="README content",
        raw_text_truncated=False,
        raw_text_length=14,
        metadata={"stars": 100}
    )
    
    data = item.to_dict()
    
    assert data["topic_id"] == 1
    assert data["external_id"] == "github:test/repo"
    assert data["title"] == "Test"
    assert data["metadata"]["stars"] == 100
    assert isinstance(data["published_at"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
