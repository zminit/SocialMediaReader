# Collector 模块

负责从外部信息源采集数据的模块。

## 功能特性

- ✅ GitHub Repos 搜索和详情采集
- ✅ 自动处理分页
- ✅ 智能速率限制管理（header-driven）
- ✅ 指数退避重试机制
- ✅ 单次采集内去重
- ✅ 流式处理（Iterable）
- ✅ 活跃度评分计算
- ✅ 完整的元数据记录

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入你的 GitHub Token：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
GITHUB_TOKEN=your_github_token_here
```

### 3. 基础使用

```python
from collector import GitHubCollector, SourceQuery, CollectorConfig

# 加载配置
config = CollectorConfig.from_env()

# 创建 collector
collector = GitHubCollector(config)

# 创建查询
query = SourceQuery(
    topic_id=1,
    keywords=["machine learning"],
    source_type="github",
    max_items=10,
    sort_by="stars",
    programming_language="Python"
)

# 执行采集（流式处理）
for item in collector.collect(query):
    print(f"{item.title} - {item.metadata['stars']} stars")
```

## 核心概念

### SourceQuery

采集任务的输入参数：

```python
query = SourceQuery(
    topic_id=1,                          # 主题 ID
    keywords=["rust", "web framework"],  # 搜索关键词
    source_type="github",                # 数据源类型
    max_items=50,                        # 最大采集数量
    page_size=30,                        # 每页数量
    sort_by="best_match",                # 排序方式
    programming_language="Rust",         # 编程语言过滤
    min_stars=100,                       # 最小 Star 数
    topics=["web", "framework"]          # GitHub Topics 过滤
)
```

**sort_by 参数说明：**

- `"best_match"`: 相关性排序（默认，不传 sort 参数给 GitHub API）
- `"stars"`: 按 Star 数排序
- `"forks"`: 按 Fork 数排序
- `"updated"`: 按更新时间排序
- `"help-wanted-issues"`: 按 help-wanted issues 数排序

### RawItem

采集结果的标准输出格式：

```python
@dataclass
class RawItem:
    # 基础标识
    topic_id: int
    source_type: str              # "github"
    source_subtype: str           # "github_repo"
    external_id: str              # "github:owner/repo"
    
    # URL 和标题
    url: str
    canonical_url: str
    title: str
    author: str
    description: str
    
    # 时间戳
    published_at: datetime
    collected_at: datetime
    
    # 内容
    raw_text: str                 # README 内容
    raw_text_truncated: bool
    raw_text_length: int
    
    # 元数据
    metadata: Dict[str, Any]      # stars, forks, activity_score 等
    
    # 采集上下文
    query_keyword: str            # 命中的关键词
    rank: int                     # 搜索结果排名
    collected_by: str             # "GitHubCollector"
```

### CollectorConfig

配置管理（从环境变量加载）：

```python
config = CollectorConfig.from_env()

# 或手动创建
config = CollectorConfig(
    github_token="your_token",
    github_api_timeout=30,
    github_max_retries=3,
    github_rate_limit_buffer=100,  # 保留配额
    save_raw_payload=True,         # 开发期保留原始响应
    log_level="INFO"
)
```

## 速率限制管理

GitHubCollector 自动处理速率限制：

1. **初始化时获取真实状态**：启动时调用 `/rate_limit` 获取当前配额
2. **Header-driven 更新**：每次请求后从响应头更新状态
3. **主动等待**：配额低于 buffer 时自动等待到重置时间
4. **403 响应处理**：捕获 rate limit exceeded 响应并等待

```python
# 查看 rate limit 状态
status = collector.get_rate_limit_status()
print(f"Remaining: {status['remaining']}/{status['limit']}")
print(f"Reset at: {status['reset_at_datetime']}")
```

## 活跃度评分

V0 版本使用简化的活跃度评分算法（不依赖历史数据）：

```python
score = (
    push_freshness * 0.5 +      # 推送新鲜度（距离最后推送的天数）
    stars_weight * 0.3 +         # Stars 权重（对数归一化）
    recent_activity * 0.2        # 近期活动（90 天内是否有推送）
)
```

评分范围：0-1，越高表示越活跃。

## 错误处理

```python
from collector.base import (
    CollectorError,
    RateLimitExceeded,
    AuthenticationError,
    ResourceNotFound
)

try:
    for item in collector.collect(query):
        # 处理数据
        pass
except AuthenticationError:
    print("GitHub Token 无效")
except RateLimitExceeded:
    print("速率限制超出")
except CollectorError as e:
    print(f"采集失败: {e}")
```

## 示例代码

查看 `examples/basic_usage.py` 获取完整示例：

```bash
python examples/basic_usage.py
```

## 测试

```bash
# 运行单元测试
pytest tests/test_collector.py -v

# 运行集成测试（需要真实 GitHub Token）
pytest tests/test_integration.py -v
```

## 职责边界

**Collector 负责：**
- 构造外部查询
- 调用外部 API
- 处理分页、限流、重试
- 单次采集内的基础去重
- 转换成标准 RawItem
- 记录采集上下文和外部元数据

**Collector 不负责：**
- 跨批次去重（由 processor 负责）
- 内容质量判断
- LLM 摘要和分析
- 数据持久化

## 扩展

未来可以扩展其他数据源：

```python
class RSSCollector(BaseCollector):
    def collect(self, query: SourceQuery) -> Iterable[RawItem]:
        # 实现 RSS 采集逻辑
        pass

class CSDNCollector(BaseCollector):
    def collect(self, query: SourceQuery) -> Iterable[RawItem]:
        # 实现 CSDN 采集逻辑
        pass
```

## 注意事项

1. **GitHub Token 权限**：需要 `public_repo` 权限
2. **Rate Limit**：未认证 60 次/小时，认证后 5000 次/小时
3. **README 获取**：开发期默认获取 README，生产期可关闭以节省配额
4. **分页限制**：GitHub Search API 最多返回 1000 条结果
5. **文本截断**：README 超过 5000 字符会被截断

## 配置参数

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `GITHUB_TOKEN` | 必填 | GitHub Personal Access Token |
| `GITHUB_API_TIMEOUT` | 30 | API 请求超时（秒）|
| `GITHUB_MAX_RETRIES` | 3 | 最大重试次数 |
| `GITHUB_RATE_LIMIT_BUFFER` | 100 | 速率限制保留配额 |
| `SAVE_RAW_PAYLOAD` | true | 是否保存原始响应 |
| `COLLECTOR_LOG_LEVEL` | INFO | 日志级别 |

## 修订历史

### V0.1 (2026-05-13)

- ✅ 修正 `sort_by="best_match"` 映射（不传 sort 参数）
- ✅ 修正 rate_limit 初始化逻辑
- ✅ 添加 403 rate limit 响应处理
- ✅ 去掉 `activity_score` 中的假值（release_freshness）
- ✅ 实现完整的 GitHubCollector
- ✅ 添加示例代码和文档
