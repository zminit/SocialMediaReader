# Collector 模块开发方案

## 📋 项目概述

Collector 模块是 SocialMediaReader 项目的数据采集层，负责从外部信息源（GitHub、RSS、CSDN 等）采集原始数据。

**当前状态**: ✅ V0.1 完成（GitHub Repos 采集）

## 🎯 核心目标

1. **职责清晰**: 只负责采集和基础转换，不做质量判断和 LLM 分析
2. **可扩展**: 支持多种数据源，统一接口
3. **健壮性**: 完善的错误处理、重试、限流机制
4. **可测试**: 单元测试 + 集成测试覆盖

## 📁 目录结构

```
collector/
├── __init__.py              # 模块入口
├── README.md                # 模块文档
├── base.py                  # BaseCollector 抽象基类
├── models.py                # 数据模型（SourceQuery, RawItem）
├── config.py                # 配置管理
├── utils.py                 # 工具函数（重试、日志）
├── github_collector.py      # GitHub 采集器实现
└── (future) rss_collector.py, csdn_collector.py...

examples/
└── basic_usage.py           # 使用示例

tests/
├── __init__.py
├── test_collector.py        # 单元测试（Mock）
└── test_integration.py      # 集成测试（真实 API）
```

## 🔧 核心组件

### 1. 数据模型

#### SourceQuery（输入）
```python
@dataclass
class SourceQuery:
    topic_id: int
    keywords: List[str]
    source_type: str              # "github", "rss", "csdn"
    max_items: int = 50
    page_size: int = 30
    sort_by: str = "best_match"
    programming_language: Optional[str] = None
    min_stars: int = 0
    topics: List[str] = []
```

#### RawItem（输出）
```python
@dataclass
class RawItem:
    # 标识
    topic_id: int
    source_type: str
    source_subtype: str
    external_id: str              # "github:owner/repo"
    
    # 内容
    url: str
    title: str
    author: str
    description: str
    raw_text: Optional[str]       # README 或正文
    
    # 元数据
    metadata: Dict[str, Any]      # stars, forks, activity_score 等
    
    # 上下文
    query_keyword: str
    rank: int
    collected_at: datetime
```

### 2. GitHubCollector 实现

**核心特性**:
- ✅ httpx 客户端（同步）
- ✅ Header-driven rate limit 管理
- ✅ 指数退避重试
- ✅ 分页处理
- ✅ 单次采集内去重
- ✅ 流式处理（Iterable）
- ✅ 活跃度评分计算

**关键修正**:
1. `sort_by="best_match"` 不传 sort 参数（使用 GitHub 默认相关性排序）
2. 初始化时调用 `/rate_limit` 获取真实状态
3. 403 响应时捕获 rate limit exceeded 并等待
4. 活跃度评分去掉假值（release_freshness）

### 3. 速率限制管理

```python
# 1. 初始化时获取真实状态
self._fetch_rate_limit_status()

# 2. 每次请求后从响应头更新
self._update_rate_limit(response.headers)

# 3. 请求前检查，必要时等待
self._check_rate_lim