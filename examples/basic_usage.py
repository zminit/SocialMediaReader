"""
Collector 模块基础使用示例

演示如何使用 GitHubCollector 采集数据
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

from collector import GitHubCollector, SourceQuery, CollectorConfig
from collector.utils import set_log_level

# 加载环境变量
load_dotenv()

# 设置日志级别
set_log_level("INFO")


def example_basic_search():
    """基础搜索示例"""
    print("=" * 60)
    print("示例 1: 基础搜索")
    print("=" * 60)
    
    # 创建配置
    config = CollectorConfig.from_env()
    
    # 创建 collector
    collector = GitHubCollector(config)
    
    # 查看 rate limit 状态
    print(f"Rate limit status: {collector.get_rate_limit_status()}")
    
    # 创建查询
    query = SourceQuery(
        topic_id=1,
        keywords=["machine learning", "deep learning"],
        source_type="github",
        max_items=10,
        page_size=5,
        sort_by="stars",
        programming_language="Python",
        min_stars=100
    )
    
    # 执行采集
    print(f"\n开始采集...")
    results = []
    
    for item in collector.collect(query):
        print(f"\n找到: {item.title} ({item.author})")
        print(f"  URL: {item.url}")
        print(f"  Stars: {item.metadata['stars']}")
        print(f"  Activity Score: {item.metadata['activity_score']}")
        print(f"  Language: {item.metadata['language']}")
        
        results.append(item.to_dict())
    
    print(f"\n采集完成，共 {len(results)} 条结果")
    
    # 保存结果
    with open("results_basic.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"结果已保存到 results_basic.json")


def example_best_match_search():
    """Best Match 搜索示例（测试 sort 参数映射）"""
    print("\n" + "=" * 60)
    print("示例 2: Best Match 搜索（相关性排序）")
    print("=" * 60)
    
    config = CollectorConfig.from_env()
    collector = GitHubCollector(config)
    
    query = SourceQuery(
        topic_id=2,
        keywords=["rust web framework"],
        source_type="github",
        max_items=5,
        page_size=5,
        sort_by="best_match",  # 不传 sort 参数，使用默认相关性排序
        programming_language="Rust"
    )
    
    print(f"\n开始采集（best_match 模式）...")
    
    for item in collector.collect(query):
        print(f"\n{item.rank}. {item.title} ({item.author})")
        print(f"   Stars: {item.metadata['stars']}, Keyword: {item.query_keyword}")


def example_with_topics():
    """带 topics 过滤的搜索"""
    print("\n" + "=" * 60)
    print("示例 3: 带 Topics 过滤")
    print("=" * 60)
    
    config = CollectorConfig.from_env()
    collector = GitHubCollector(config)
    
    query = SourceQuery(
        topic_id=3,
        keywords=["web framework"],
        source_type="github",
        max_items=5,
        sort_by="updated",
        programming_language="TypeScript",
        topics=["react", "nextjs"]
    )
    
    print(f"\n开始采集（带 topics 过滤）...")
    
    for item in collector.collect(query):
        print(f"\n{item.title}")
        print(f"  Topics: {', '.join(item.metadata['topics'][:5])}")
        print(f"  Updated: {item.metadata['updated_at']}")


def example_rate_limit_handling():
    """Rate Limit 处理示例"""
    print("\n" + "=" * 60)
    print("示例 4: Rate Limit 状态监控")
    print("=" * 60)
    
    config = CollectorConfig.from_env()
    collector = GitHubCollector(config)
    
    # 查看初始状态
    status = collector.get_rate_limit_status()
    print(f"\n初始 Rate Limit 状态:")
    print(f"  Remaining: {status['remaining']}/{status['limit']}")
    print(f"  Reset at: {status['reset_at_datetime']}")
    print(f"  Buffer: {status['buffer']}")
    
    # 执行一次小规模采集
    query = SourceQuery(
        topic_id=4,
        keywords=["python"],
        source_type="github",
        max_items=3,
        page_size=3
    )
    
    list(collector.collect(query))
    
    # 查看采集后状态
    status = collector.get_rate_limit_status()
    print(f"\n采集后 Rate Limit 状态:")
    print(f"  Remaining: {status['remaining']}/{status['limit']}")


if __name__ == "__main__":
    # 检查环境变量
    if not os.getenv("GITHUB_TOKEN"):
        print("错误: 请设置 GITHUB_TOKEN 环境变量")
        print("可以在 .env 文件中设置:")
        print("  GITHUB_TOKEN=your_token_here")
        exit(1)
    
    try:
        # 运行示例
        example_basic_search()
        example_best_match_search()
        example_with_topics()
        example_rate_limit_handling()
        
        print("\n" + "=" * 60)
        print("所有示例运行完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
