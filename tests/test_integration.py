"""
Collector 模块集成测试

使用真实 GitHub API 进行小规模测试
需要设置 GITHUB_TOKEN 环境变量
"""

import pytest
import os
from dotenv import load_dotenv

from collector import GitHubCollector, SourceQuery, CollectorConfig
from collector.base import CollectorError

# 加载环境变量
load_dotenv()

# 如果没有 GITHUB_TOKEN，跳过集成测试
pytestmark = pytest.mark.skipif(
    not os.getenv("GITHUB_TOKEN"),
    reason="GITHUB_TOKEN not set, skipping integration tests"
)


@pytest.fixture
def real_config():
    """真实配置"""
    return CollectorConfig.from_env()


@pytest.fixture
def collector(real_config):
    """真实 collector"""
    return GitHubCollector(real_config)


def test_real_rate_limit_status(collector):
    """测试真实 rate limit 状态获取"""
    status = collector.get_rate_limit_status()
    
    assert "remaining" in status
    assert "limit" in status
    assert "reset_at" in status
    assert status["remaining"] >= 0
    assert status["limit"] > 0
    
    print(f"\nRate limit status: {status['remaining']}/{status['limit']}")


def test_real_basic_search(collector):
    """测试真实基础搜索"""
    query = SourceQuery(
        topic_id=1,
        keywords=["python web framework"],
        source_type="github",
        max_items=3,
        page_size=3,
        sort_by="stars",
        programming_language="Python"
    )
    
    results = list(collector.collect(query))
    
    assert len(results) > 0
    assert len(results) <= 3
    
    for item in results:
        assert item.source_type == "github"
        assert item.source_subtype == "github_repo"
        assert item.external_id.startswith("github:")
        assert item.url.startswith("https://github.com/")
        assert item.metadata["stars"] > 0
        assert item.metadata["language"] == "Python"
        
        print(f"\n找到: {item.title} ({item.author})")
        print(f"  Stars: {item.metadata['stars']}")
        print(f"  Activity Score: {item.metadata['activity_score']}")


def test_real_best_match_search(collector):
    """测试真实 best_match 搜索"""
    query = SourceQuery(
        topic_id=2,
        keywords=["rust async"],
        source_type="github",
        max_items=2,
        page_size=2,
        sort_by="best_match",  # 测试 best_match 映射
        programming_language="Rust"
    )
    
    results = list(collector.collect(query))
    
    assert len(results) > 0
    
    for item in results:
        assert item.metadata["language"] == "Rust"
        print(f"\n{item.rank}. {item.title} - {item.metadata['stars']} stars")


def test_real_multiple_keywords(collector):
    """测试多关键词搜索和去重"""
    query = SourceQuery(
        topic_id=3,
        keywords=["typescript", "typescript framework"],  # 可能有重复结果
        source_type="github",
        max_items=5,
        page_size=3,
        sort_by="stars",
        programming_language="TypeScript"
    )
    
    results = list(collector.collect(query))
    
    # 检查去重
    external_ids = [item.external_id for item in results]
    assert len(external_ids) == len(set(external_ids)), "应该没有重复的 repo"
    
    print(f"\n采集到 {len(results)} 个不重复的 repos")


def test_real_with_min_stars(collector):
    """测试 min_stars 过滤"""
    query = SourceQuery(
        topic_id=4,
        keywords=["machine learning"],
        source_type="github",
        max_items=3,
        sort_by="stars",
        programming_language="Python",
        min_stars=1000  # 至少 1000 stars
    )
    
    results = list(collector.collect(query))
    
    for item in results:
        assert item.metadata["stars"] >= 1000
        print(f"\n{item.title}: {item.metadata['stars']} stars")


def test_real_rate_limit_tracking(collector):
    """测试 rate limit 跟踪"""
    status_before = collector.get_rate_limit_status()
    remaining_before = status_before["remaining"]
    
    # 执行一次小规模采集
    query = SourceQuery(
        topic_id=5,
        keywords=["python"],
        source_type="github",
        max_items=2,
        page_size=2
    )
    
    list(collector.collect(query))
    
    status_after = collector.get_rate_limit_status()
    remaining_after = status_after["remaining"]
    
    # 应该消耗了一些配额
    assert remaining_after < remaining_before
    
    print(f"\n配额变化: {remaining_before} -> {remaining_after}")
    print(f"消耗: {remaining_before - remaining_after}")


def test_real_error_handling(collector):
    """测试错误处理"""
    # 测试无效的编程语言（应该返回空结果，不应该崩溃）
    query = SourceQuery(
        topic_id=6,
        keywords=["nonexistent_keyword_12345"],
        source_type="github",
        max_items=5,
        programming_language="InvalidLanguage"
    )
    
    results = list(collector.collect(query))
    
    # 可能返回空结果，但不应该抛出异常
    print(f"\n无效语言搜索结果: {len(results)} 个")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
