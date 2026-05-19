# SocialMediaReader 项目状态

> **最后更新**: 2026-05-19 | **版本**: V0

## 项目概述

SocialMediaReader 是一个面向个人使用的 AI 工作流调研系统：持续收集 GitHub 和专业技术内容，通过 Dify 完成摘要、分类、对比与周报生成，最终在个人网站中展示。

完整设计文档见 `social_media_reader_v0.html`。

---

## 已完成模块

### 1. Collector 模块

**职责**：从外部信息源采集数据，转换为标准 `RawItem`。

**职责边界**：
- ✅ 构造外部查询、调用外部 API
- ✅ 处理分页、限流、重试
- ✅ 单次采集内基础去重（同一批次内 `external_id` 去重）
- ✅ 转换成标准 `RawItem`，记录采集上下文
- ❌ 不负责跨批次去重（由 Processor 负责）
- ❌ 不负责内容质量判断、LLM 摘要和分析

**文件结构**：
```
collector/
├── __init__.py           # 导出 BaseCollector, GitHubCollector, SourceQuery, RawItem, CollectorConfig
├── models.py             # SourceQuery, RawItem 数据模型
├── config.py             # CollectorConfig 配置管理
├── base.py               # BaseCollector 抽象基类 + 异常类
├── utils.py              # retry_with_backoff, parse_github_datetime, truncate_text, sanitize_url
├── github_collector.py   # GitHubCollector 实现
└── README.md
```

#### 核心类与接口

**`SourceQuery`** — 采集任务输入参数
```python
@dataclass
class SourceQuery:
    topic_id: int
    keywords: List[str]
    source_type: str          # "github" | "rss" | "csdn" | "juejin"
    time_range: Optional[Tuple[datetime, datetime]] = None
    max_items: int = 50
    page_size: int = 30
    sort_by: str = "best_match"  # "best_match" | "stars" | "forks" | "updated"
    programming_language: Optional[str] = None
    content_language: Optional[str] = None
    min_stars: int = 0
    topics: List[str] = field(default_factory=list)
```

**`RawItem`** — 采集结果输出
```python
@dataclass
class RawItem:
    topic_id: int
    source_type: str          # "github" | "rss" | "csdn"
    source_subtype: str       # "github_repo" | "github_release" | "article"
    external_id: str          # "github:owner/repo"
    url: str
    canonical_url: str
    title: str
    author: str
    description: Optional[str]
    published_at: Optional[datetime]
    collected_at: datetime
    raw_text: Optional[str]   # README 或正文
    raw_text_truncated: bool
    raw_text_length: int
    metadata: Dict[str, Any]  # source_type 特定元数据
    query_keyword: Optional[str] = None
    rank: Optional[int] = None
    collected_by: str = "unknown_collector"
    raw_payload: Optional[Dict] = None  # 开发期保留原始响应
```

GitHub 类型的 `metadata` 结构：
```python
{
    "stars": int,
    "forks": int,
    "watchers": int,
    "open_issues": int,
    "language": str,           # 编程语言
    "topics": List[str],       # GitHub topics
    "license": Optional[str],  # SPDX ID
    "is_fork": bool,
    "is_archived": bool,
    "created_at": str,         # ISO 8601
    "updated_at": str,
    "pushed_at": str,
    "activity_score": float,   # 0-1，由 Collector 计算
    "homepage": Optional[str],
}
```

**`BaseCollector`** — 抽象基类
```python
class BaseCollector(ABC):
    def __init__(self, config: CollectorConfig): ...
    @abstractmethod
    def collect(self, query: SourceQuery) -> Iterable[RawItem]: ...
    @abstractmethod
    def get_rate_limit_status(self) -> Dict[str, Any]: ...
    def validate_config(self) -> bool: ...
```

**`GitHubCollector`** — GitHub 采集器实现
```python
class GitHubCollector(BaseCollector):
    def collect(self, query: SourceQuery) -> Iterable[RawItem]:
        """按 keywords 搜索 GitHub repos，支持分页、rate limit 管理、单批次去重。"""
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """返回 {remaining, limit, reset_at, reset_at_datetime, buffer}"""
```

**`CollectorConfig`** — 配置
```python
@dataclass
class CollectorConfig:
    github_token: str
    github_api_timeout: int = 30
    github_max_retries: int = 3
    github_rate_limit_buffer: int = 100
    save_raw_payload: bool = True
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "CollectorConfig": ...
```

环境变量：`GITHUB_TOKEN`（必须）、`GITHUB_API_TIMEOUT`、`GITHUB_MAX_RETRIES`、`GITHUB_RATE_LIMIT_BUFFER`、`SAVE_RAW_PAYLOAD`、`COLLECTOR_LOG_LEVEL`

**异常类**：`CollectorError`、`RateLimitExceeded`、`AuthenticationError`、`ResourceNotFound`

**工具函数** (`utils.py`)：
- `retry_with_backoff(max_retries, base_delay, max_delay, exceptions)` — 指数退避重试装饰器
- `parse_github_datetime(dt_str) -> Optional[datetime]`
- `truncate_text(text, max_length) -> Tuple[str, bool, int]`
- `sanitize_url(url) -> str` — 规范化 URL（去尾斜杠、统一 https）

---

### 2. Processor 模块

**职责**：将 Collector 输出的 `RawItem` 标准化、清洗、指纹化、去重检查、质量评估，转换为 Dify 可消费的 `AnalysisInput`。

**职责边界**：
- ✅ RawItem 标准化（URL trim、metadata 字段统一）
- ✅ 内容清洗（去 badge、去 HTML 注释、截断过长代码块）
- ✅ SHA256 内容指纹
- ✅ 跨批次去重查询（通过 `DedupRepository` 接口）
- ✅ 基础质量评估（硬过滤 + 软评分）
- ✅ 转换为 `AnalysisInput`
- ❌ 不负责数据库写入（由 Orchestrator 负责）
- ❌ 不负责调用 Dify（由 DifyClient / Orchestrator 负责）

**文件结构**：
```
processor/
├── __init__.py           # 导出所有公开类
├── config.py             # ProcessorConfig
├── models.py             # AnalysisInput, QualityEvaluation, ProcessingResult
├── interfaces.py         # DedupRepository, TopicRepository（抽象接口，由 Storage 实现）
├── normalizer.py         # Normalizer
├── content_cleaner.py    # ContentCleaner
├── fingerprint.py        # FingerprintCalculator
├── dedup_checker.py      # DedupChecker
├── quality_filter.py     # QualityFilter
├── data_transformer.py   # DataTransformer
├── processor.py          # Processor 主流程
└── README.md
```

#### 核心类与接口

**`Processor`** — 主流程
```python
class Processor:
    def __init__(self,
        normalizer, cleaner, fingerprint_calculator,
        dedup_checker, quality_filter, transformer,
        topic_repository, config): ...

    def process(self, item: RawItem) -> ProcessingResult:
        """处理单条 RawItem，返回 passed/duplicate/filtered 结果。"""

    def process_batch(self, items: Iterable[RawItem]) -> List[ProcessingResult]:
        """批量处理，返回所有结果（含统计日志）。"""

    def process_batch_to_analysis_inputs(self, items: Iterable[RawItem]) -> List[AnalysisInput]:
        """批量处理，仅返回通过的 AnalysisInput 列表。"""
```

处理流程：`RawItem → Normalizer → ContentCleaner → FingerprintCalculator → DedupChecker → QualityFilter → DataTransformer → AnalysisInput`

**`ProcessingResult`** — 处理结果
```python
@dataclass
class ProcessingResult:
    status: str  # "passed" | "duplicate" | "filtered"
    analysis_input: Optional[AnalysisInput] = None      # status=passed 时有值
    duplicate_info: Optional[Dict] = None               # status=duplicate 时有值：{type, duplicate_source_id}
    filter_info: Optional[Dict] = None                  # status=filtered 时有值：{reason, quality_score, checks}
    normalized_item: Optional[RawItem] = None            # 标准化后的 RawItem（所有状态都有）
    content_fingerprint: Optional[str] = None            # SHA256 指纹（所有状态都有）
```

**`AnalysisInput`** — Dify 工作流输入
```python
@dataclass
class AnalysisInput:
    topic: str                        # 主题名（非 id）
    title: str
    url: str
    description: Optional[str]
    cleaned_content_excerpt: str      # 清洗后的内容片段（≤ max_excerpt_length）
    content_length: int               # 清洗后完整内容长度
    stars: Optional[int] = None
    forks: Optional[int] = None
    programming_language: Optional[str] = None
    license: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    last_commit_at: Optional[datetime] = None
    activity_score: Optional[float] = None
    initial_quality_score: float = 0.0
    external_id: str = ""
    content_fingerprint: str = ""
    processed_at: Optional[datetime] = None

    def to_dify_payload(self) -> Dict[str, Any]:
        """转换为 Dify 请求 payload：{topic, title, url, description, readme, metadata}"""
```

**`QualityEvaluation`** — 质量评估结果
```python
@dataclass
class QualityEvaluation:
    score: float               # 0-1 综合评分
    hard_filtered: bool        # 是否被硬过滤
    filter_reason: Optional[str]
    checks: Dict[str, bool]    # {has_title, has_url, has_external_id, has_content, has_description, not_archived}
    score_breakdown: Dict[str, float]  # {stars, activity, readme, metadata}
```

硬过滤条件（GitHub）：
- 缺少 title/url/external_id
- `is_archived = True`
- README 为空或清洗后内容 < `min_content_length`（默认 50 字符）

软评分权重（GitHub）：
- Stars 权重 30%（分档：10k+ → 0.30, 1k+ → 0.25, 100+ → 0.20, 10+ → 0.15, <10 → 0.05）
- Activity 权重 30%（取 Collector 的 `activity_score`）
- README 长度 25%（分档：2000+ → 0.25, 1000+ → 0.20, 500+ → 0.15, <500 → 0.10）
- 元数据完整度 15%（license +0.05, topics +0.05, language +0.05）

#### Processor 依赖的外部接口（Storage 需实现）

定义在 `processor/interfaces.py`：

```python
class DedupRepository(ABC):
    def find_by_url(self, canonical_url: str) -> Optional[int]: ...
    def find_by_external_id(self, external_id: str) -> Optional[int]: ...
    def find_by_fingerprint(self, fingerprint: str) -> Optional[int]: ...

class TopicRepository(ABC):
    def get_name(self, topic_id: int) -> str: ...
```

**`ProcessorConfig`**：
```python
@dataclass(frozen=True)
class ProcessorConfig:
    min_content_length: int = 50      # 硬过滤：最小内容长度
    max_excerpt_length: int = 2000    # Dify 输入 excerpt 最大长度
```

环境变量：`PROCESSOR_MIN_CONTENT_LENGTH`、`PROCESSOR_MAX_EXCERPT_LENGTH`

#### 各组件详情

| 组件 | 功能 |
|---|---|
| `Normalizer` | URL trim、canonical_url fallback、metadata 字段统一（`language→programming_language`、`pushed_at→last_commit_at`） |
| `ContentCleaner` | 去 HTML 注释、去 badge/纯图片行、截断过长代码块、提取优先段落（Description/Overview 等）、excerpt 截断 |
| `FingerprintCalculator` | 空白归一化 + 小写 + SHA256 |
| `DedupChecker` | 按顺序查 canonical_url → external_id → fingerprint，返回 `{type, source_id}` 或 `None` |
| `QualityFilter` | 硬过滤 + 软评分，返回 `QualityEvaluation` |
| `DataTransformer` | `RawItem + 清洗内容 + 指纹 + 质量分 + 主题名 → AnalysisInput` |

---

### 3. DifyClient 模块

**职责**：封装 Dify Workflow API 调用，将 Processor 输出的 `AnalysisInput` 发送给 Dify 内容分析工作流，解析返回结果。

**职责边界**：
- ✅ 构建 Dify `/workflows/run` 请求
- ✅ 阻塞模式调用 + 重试（429/5xx 指数退避）
- ✅ 解析 Dify 响应为 `AnalysisResult`
- ✅ 批量逐条调用（带间隔）
- ✅ 健康检查
- ❌ 不负责决定分析顺序（由 Orchestrator 负责）
- ❌ 不负责结果持久化（由 Orchestrator 负责）

**文件结构**：
```
dify_client/
├── __init__.py    # 导出 DifyClient, DifyConfig, AnalysisResult
├── client.py      # DifyClient 实现
├── config.py      # DifyConfig
├── models.py      # AnalysisResult
└── README.md
```

#### 核心类与接口

**`DifyClient`** — Dify 工作流客户端
```python
class DifyClient:
    def __init__(self, config: DifyConfig): ...

    def analyze(self, analysis_input: AnalysisInput, user: str = "system") -> AnalysisResult:
        """单条分析：AnalysisInput → Dify 工作流 → AnalysisResult"""

    def analyze_batch(self, inputs: List[AnalysisInput], user: str = "system", delay: float = 1.0) -> List[AnalysisResult]:
        """批量分析：逐条调用，每次间隔 delay 秒"""

    def health_check(self) -> bool:
        """检查 Dify API 是否可达（GET /parameters）"""
```

发送给 Dify 的请求体格式：
```json
{
    "inputs": {
        "topic": "AI 工作流搭建",
        "title": "...",
        "url": "...",
        "description": "...",
        "readme": "...",
        "metadata": "{\"stars\": 1200, ...}"  // JSON 字符串
    },
    "response_mode": "blocking",
    "user": "system"
}
```

**`AnalysisResult`** — Dify 分析结果
```python
@dataclass
class AnalysisResult:
    source_id: Optional[int] = None      # 由 Orchestrator 关联
    workflow_run_id: Optional[str] = None
    summary: str = ""
    relevance_score: float = 0.0
    quality_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    raw_response: Dict[str, Any] = field(default_factory=dict)
    analyzed_at: Optional[datetime] = None
    status: str = ""                      # "succeeded" | "failed" | "stopped"
    elapsed_time: float = 0.0
    total_tokens: int = 0
    error: Optional[str] = None

    @classmethod
    def from_dify_response(cls, response: Dict) -> "AnalysisResult": ...

    @property
    def succeeded(self) -> bool: ...
```

**`DifyConfig`**：
```python
@dataclass
class DifyConfig:
    base_url: str = "http://localhost/v1"
    api_key: str = ""
    timeout: int = 120
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "DifyConfig": ...
    def validate(self) -> None: ...  # 检查 api_key 非空
```

环境变量：`DIFY_BASE_URL`、`DIFY_API_KEY`（必须）、`DIFY_TIMEOUT`、`DIFY_MAX_RETRIES`

---

## 模块间数据流

```
SourceQuery ──→ Collector ──→ RawItem ──→ Processor ──→ ProcessingResult
                                                            │
                                                            ├── passed → AnalysisInput ──→ DifyClient ──→ AnalysisResult
                                                            ├── duplicate → {type, duplicate_source_id}
                                                            └── filtered → {reason, quality_score, checks}
```

Processor 需要 Storage 提供：
- `DedupRepository`：去重查询（find_by_url / find_by_external_id / find_by_fingerprint）
- `TopicRepository`：主题名查询（get_name）

**Orchestrator（待开发）控制全流程写入**：

Processor 对 Storage 仅有**只读**依赖（去重查询 + 主题名查询），所有写操作由 Orchestrator 统一控制：

```
Orchestrator 控制全流程：
  1. 调用 Collector.collect()        → [RawItem]
  2. 调用 Processor.process_batch()  → [ProcessingResult]
     └── Processor 内部通过 DedupRepository/TopicRepository 查询 Storage（只读）
  3. 根据 ProcessingResult.status 分别写入：
     ├── passed   → SourceRepository.create_source()
     │             → DifyClient.analyze()
     │             → AnalysisResultRepository.save_analysis_result()
     ├── duplicate → DuplicateRecordRepository.create_duplicate_record()
     └── filtered  → FilteredRecordRepository.create_filtered_record()
```

---

### 4. Storage 模块

**职责**：SQLite 持久化层，实现 Processor 依赖的查询接口，并为 Orchestrator 提供写入接口。

**职责边界**：
- ✅ 数据库初始化、schema 迁移、WAL 模式
- ✅ 实现 `processor.interfaces.TopicRepository`（主题名查询）
- ✅ 实现 `processor.interfaces.DedupRepository`（去重查询：URL / external_id / fingerprint）
- ✅ sources 表 CRUD + 状态管理
- ✅ 重复记录日志（duplicate_records）
- ✅ 过滤记录日志（filtered_records）
- ✅ Dify 分析结果存储（analysis_results）
- ❌ 不负责流程编排（由 Orchestrator 负责）
- ❌ 不负责业务逻辑判断（由 Processor / Orchestrator 负责）

**文件结构**：
```
storage/
├── __init__.py              # 导出所有公开类
├── config.py                # StorageConfig
├── database.py              # Database 初始化 + 连接管理 + 迁移
├── topic_repository.py      # SQLiteTopicRepository（实现 processor.interfaces.TopicRepository）
├── dedup_repository.py      # SQLiteDedupRepository（实现 processor.interfaces.DedupRepository）
├── source_repository.py     # SQLiteSourceRepository（sources CRUD）
├── duplicate_repository.py  # SQLiteDuplicateRecordRepository（重复日志）
├── filtered_repository.py   # SQLiteFilteredRecordRepository（过滤日志）
├── analysis_repository.py   # SQLiteAnalysisResultRepository（Dify 分析结果）
└── README.md
```

#### 数据库表结构

| 表 | 用途 |
|---|---|
| `topics` | 主题管理（name + keywords） |
| `sources` | 通过 Processor 的内容源（去重后保留的） |
| `duplicate_records` | 被判定为重复的 RawItem 日志 |
| `filtered_records` | 被硬过滤的 RawItem 日志 |
| `analysis_results` | Dify 工作流分析结果 |
| `schema_version` | Schema 版本跟踪 |

#### 核心类与接口

**`Database`** — 数据库管理
```python
class Database:
    def __init__(self, config: StorageConfig): ...
    def initialize(self) -> None:
        """创建所有表、设置 WAL 模式、外键约束、迁移。"""
    def get_connection(self) -> sqlite3.Connection: ...
    def close(self) -> None: ...
    def __enter__(self) -> "Database": ...
    def __exit__(self, ...): ...
```

**`SQLiteTopicRepository`** — 主题仓库（实现 `TopicRepository`）
```python
class SQLiteTopicRepository(TopicRepository):
    def get_name(self, topic_id: int) -> str:
        """获取主题名。Raises TopicNotFoundError。"""
    def create_topic(self, name: str, keywords: Optional[List[str]] = None) -> int: ...
    def get_topic(self, topic_id: int) -> Optional[Dict]: ...
    def list_topics(self) -> List[Dict]: ...
    def update_topic(self, topic_id: int, *, name=None, keywords=None) -> bool: ...
```

**`SQLiteDedupRepository`** — 去重仓库（实现 `DedupRepository`）
```python
class SQLiteDedupRepository(DedupRepository):
    def find_by_url(self, canonical_url: str) -> Optional[int]: ...
    def find_by_external_id(self, external_id: str) -> Optional[int]: ...
    def find_by_fingerprint(self, fingerprint: str) -> Optional[int]: ...
```

**`SQLiteSourceRepository`** — 内容源仓库
```python
class SQLiteSourceRepository:
    def create_source(self, *, topic_id, source_type, source_subtype, external_id,
                      url, canonical_url, title, collected_at, processed_at,
                      content_fingerprint, ...) -> int: ...
    def get_source(self, source_id: int) -> Optional[Dict]: ...
    def get_sources_by_status(self, status: str, limit=100) -> List[Dict]: ...
    def get_sources_by_topic(self, topic_id: int, status=None, limit=100) -> List[Dict]: ...
    def update_status(self, source_id: int, status: str) -> bool:
        """状态流转：pending_analysis → analyzed / analysis_failed"""
    def count_by_status(self) -> Dict[str, int]: ...
```

**`SQLiteDuplicateRecordRepository`** — 重复记录日志
```python
class SQLiteDuplicateRecordRepository:
    def create_duplicate_record(self, *, topic_id, duplicate_type, duplicate_source_id,
                                external_id, url, canonical_url, title,
                                content_fingerprint, collected_at, metadata=None) -> int: ...
    def count_by_type(self) -> Dict[str, int]: ...
    def list_recent(self, limit=50) -> List[Dict]: ...
```

**`SQLiteFilteredRecordRepository`** — 过滤记录日志
```python
class SQLiteFilteredRecordRepository:
    def create_filtered_record(self, *, topic_id, filter_reason, quality_score,
                               checks=None, external_id, url, canonical_url, title,
                               content_fingerprint, collected_at, metadata=None) -> int: ...
    def count_by_reason(self) -> Dict[str, int]: ...
    def list_recent(self, limit=50) -> List[Dict]: ...
```

**`SQLiteAnalysisResultRepository`** — 分析结果仓库
```python
class SQLiteAnalysisResultRepository:
    def save_analysis_result(self, *, source_id, workflow_run_id=None, summary="",
                             relevance_score=0.0, quality_score=0.0, tags=None,
                             raw_response=None, analyzed_at) -> int: ...
    def get_by_source_id(self, source_id: int) -> Optional[Dict]: ...
    def list_by_topic(self, topic_id: int, min_relevance=0.0, limit=50) -> List[Dict]:
        """关联 sources 表，按 relevance_score 降序。"""
```

**`StorageConfig`**：
```python
@dataclass
class StorageConfig:
    db_path: str = "data/social_media_reader.db"
    echo_sql: bool = False

    @classmethod
    def from_env(cls) -> "StorageConfig": ...
```

环境变量：`STORAGE_DB_PATH`、`STORAGE_ECHO_SQL`

**异常类**：`TopicNotFoundError`

---

## 待开发模块

### 5. Scheduler + Orchestrator 模块
- APScheduler 定时触发
- 流程编排：串联 Collector → Processor → DifyClient → Storage
- 三条 Pipeline：每日采集、每日分析、每周报告

### 6. API 模块
- FastAPI 提供查询接口和手动触发

### 7. Website 模块
- 个人网站展示

---

## 开发里程碑

| 里程碑 | 内容 | 状态 |
|---|---|---|
| M1 | GitHub 采集可用 | ✅ 完成 |
| M2 | Processor 清洗+去重+质量评估 | ✅ 完成 |
| M2.5 | DifyClient 工作流调用 | ✅ 完成 |
| M3 | Storage 模块 | ✅ 完成 |
| M4 | Scheduler + Orchestrator | 🚧 待开发 |
| M5 | Dify 内容分析工作流 | 🚧 待开发 |
| M6 | API + 个人网站 | 🚧 待开发 |
| M7 | 周报生成 | 🚧 待开发 |

---

## 技术栈

- **语言**：Python 3.8+
- **HTTP 客户端**：httpx（Collector）、requests（DifyClient）
- **AI 平台**：Dify（自部署）
- **数据库**：SQLite（已实现，WAL 模式）
- **Web 框架**：FastAPI（计划）
- **调度**：APScheduler（计划）
- **部署**：Docker Compose，Ubuntu 2 核 4G
