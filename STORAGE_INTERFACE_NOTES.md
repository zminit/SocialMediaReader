# Storage 模块临时接口备忘

> 临时文档：记录当前 `processor/` 模块为了完成去重、主题名解析和后续状态落库，期望 `storage` 模块暴露的接口。后续开发 `storage` 模块时以此作为参考，可根据真实数据库设计再调整命名与返回结构。

## 背景

当前 `processor` 模块的职责是：

```text
RawItem -> 标准化 -> 清洗 -> 指纹 -> 去重查询 -> 质量过滤 -> AnalysisInput
```

Processor 本身不负责数据库写入，也不调用 Dify。它目前只依赖 Storage 提供查询能力；后续上层 orchestration 可能还需要 Storage 提供状态写入能力。

## Processor 当前直接依赖的接口

代码位置：`processor/interfaces.py`

### 1. DedupRepository

用于去重查询。

```python
class DedupRepository(ABC):
    def find_by_url(self, canonical_url: str) -> Optional[int]:
        """通过规范 URL 查找已存在 source id。"""

    def find_by_external_id(self, external_id: str) -> Optional[int]:
        """通过外部 ID 查找已存在 source id。"""

    def find_by_fingerprint(self, fingerprint: str) -> Optional[int]:
        """通过内容指纹查找已存在 source id。"""
```

#### 期望语义

- 返回 `None`：表示未重复。
- 返回 `int`：表示已存在的 `source_id`。
- 查询顺序由 Processor 控制：
  1. `canonical_url`
  2. `external_id`
  3. `content_fingerprint`

#### Storage 侧建议索引

- `sources.canonical_url`
- `sources.external_id`
- `sources.content_fingerprint`

#### 字段来源

| Processor 字段 | 来源 |
| --- | --- |
| `canonical_url` | `RawItem.canonical_url`，为空时 fallback 到 `RawItem.url` |
| `external_id` | `RawItem.external_id` |
| `fingerprint` | Processor 根据清洗后的正文计算 SHA256 |

## 2. TopicRepository

用于将 `topic_id` 转换成 Dify 需要的真实主题名。

```python
class TopicRepository(ABC):
    def get_name(self, topic_id: int) -> str:
        """获取真实主题名。"""
```

#### 期望语义

- 输入：Collector 传入的 `RawItem.topic_id`。
- 输出：真实主题名，例如：`AI 工作流搭建`。
- 如果主题不存在，Storage 侧可以选择：
  - 抛出明确异常，例如 `TopicNotFoundError`
  - 或返回一个上层约定的 fallback 名称

建议优先抛异常，避免 Dify 收到错误主题。

#### Storage 侧建议索引

- `topics.id`

## 后续 Orchestration 可能需要 Storage 暴露的接口

以下接口不是 Processor 当前直接调用的，但根据当前模块边界，建议 Storage 在开发时一起考虑。

### 3. SourceRepository

用于保存通过 Processor 的内容源。

```python
class SourceRepository(ABC):
    def create_source(
        self,
        *,
        topic_id: int,
        source_type: str,
        source_subtype: str,
        external_id: str,
        url: str,
        canonical_url: str,
        title: str,
        author: str,
        description: Optional[str],
        published_at: Optional[datetime],
        collected_at: datetime,
        processed_at: datetime,
        raw_text: Optional[str],
        raw_text_truncated: bool,
        raw_text_length: int,
        cleaned_content_excerpt: str,
        content_fingerprint: str,
        metadata: Dict[str, Any],
        initial_quality_score: float,
        status: str,
    ) -> int:
        """创建 source 记录并返回 source_id。"""
```

#### 建议状态

- `pending_analysis`：已通过 Processor，等待 Dify 分析。
- `analyzed`：Dify 分析完成。
- `analysis_failed`：Dify 分析失败。

### 4. DuplicateRecordRepository

用于记录重复数据，方便排查 Collector 搜索质量和来源覆盖。

```python
class DuplicateRecordRepository(ABC):
    def create_duplicate_record(
        self,
        *,
        topic_id: int,
        duplicate_type: str,
        duplicate_source_id: int,
        external_id: str,
        url: str,
        canonical_url: str,
        title: str,
        content_fingerprint: str,
        collected_at: datetime,
        metadata: Dict[str, Any],
    ) -> int:
        """记录被 Processor 判定为 duplicate 的 RawItem。"""
```

#### duplicate_type 取值

- `url`
- `external_id`
- `content`

### 5. FilteredRecordRepository

用于记录被 Processor 硬过滤的数据，便于后续调整过滤规则。

```python
class FilteredRecordRepository(ABC):
    def create_filtered_record(
        self,
        *,
        topic_id: int,
        filter_reason: str,
        quality_score: float,
        checks: Dict[str, bool],
        external_id: str,
        url: str,
        canonical_url: str,
        title: str,
        content_fingerprint: str,
        collected_at: datetime,
        metadata: Dict[str, Any],
    ) -> int:
        """记录被 Processor 硬过滤的 RawItem。"""
```

#### 当前 filter_reason 可能值

- `missing_required_fields`
- `archived_repo`
- `no_readme`
- `insufficient_content_<length>`
- `unknown`

### 6. AnalysisResultRepository

用于保存 Dify 内容分析结果。该接口更偏后续 Dify 集成模块使用。

```python
class AnalysisResultRepository(ABC):
    def save_analysis_result(
        self,
        *,
        source_id: int,
        workflow_run_id: Optional[str],
        summary: str,
        relevance_score: float,
        quality_score: float,
        tags: List[str],
        raw_response: Dict[str, Any],
        analyzed_at: datetime,
    ) -> int:
        """保存 Dify 分析结果。"""
```

## Storage 表结构草案

仅作为后续参考，不要求现在实现。

### topics

| 字段 | 说明 |
| --- | --- |
| `id` | topic id |
| `name` | 真实主题名 |
| `keywords` | 关键词，可 JSON 存储 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |

### sources

| 字段 | 说明 |
| --- | --- |
| `id` | source id |
| `topic_id` | 主题 id |
| `source_type` | github/rss/csdn/juejin |
| `source_subtype` | github_repo/article 等 |
| `external_id` | 外部唯一 id |
| `url` | 原始 URL |
| `canonical_url` | 规范 URL |
| `title` | 标题 |
| `author` | 作者 |
| `description` | 描述 |
| `published_at` | 发布时间 |
| `collected_at` | 采集时间 |
| `processed_at` | 处理时间 |
| `raw_text` | 原始文本，可考虑单独表或文件存储 |
| `raw_text_truncated` | 原始文本是否截断 |
| `raw_text_length` | 原始文本长度 |
| `cleaned_content_excerpt` | 清洗后的 Dify 输入 excerpt |
| `content_fingerprint` | SHA256 内容指纹 |
| `metadata` | source 特定元数据 JSON |
| `initial_quality_score` | Processor 初筛质量分 |
| `status` | pending_analysis/analyzed/analysis_failed |

### duplicate_records

| 字段 | 说明 |
| --- | --- |
| `id` | duplicate record id |
| `topic_id` | 主题 id |
| `duplicate_type` | url/external_id/content |
| `duplicate_source_id` | 已存在 source id |
| `external_id` | 当前重复项 external id |
| `url` | 当前重复项 URL |
| `canonical_url` | 当前重复项 canonical URL |
| `title` | 当前重复项标题 |
| `content_fingerprint` | 当前重复项内容指纹 |
| `collected_at` | 采集时间 |
| `metadata` | 元数据 JSON |

### filtered_records

| 字段 | 说明 |
| --- | --- |
| `id` | filtered record id |
| `topic_id` | 主题 id |
| `filter_reason` | 过滤原因 |
| `quality_score` | 质量分 |
| `checks` | 过滤检查结果 JSON |
| `external_id` | 外部 id |
| `url` | URL |
| `canonical_url` | canonical URL |
| `title` | 标题 |
| `content_fingerprint` | 内容指纹 |
| `collected_at` | 采集时间 |
| `metadata` | 元数据 JSON |

### analysis_results

| 字段 | 说明 |
| --- | --- |
| `id` | analysis result id |
| `source_id` | source id |
| `workflow_run_id` | Dify workflow run id |
| `summary` | 摘要 |
| `relevance_score` | 相关性分数 |
| `quality_score` | Dify 质量分数 |
| `tags` | 标签 JSON |
| `raw_response` | Dify 原始响应 JSON |
| `analyzed_at` | 分析时间 |

## 当前 Processor 返回结果与 Storage 写入建议

| `ProcessingResult.status` | Storage 建议动作 |
| --- | --- |
| `passed` | 调用 `SourceRepository.create_source(...)`，状态设为 `pending_analysis` |
| `duplicate` | 调用 `DuplicateRecordRepository.create_duplicate_record(...)` |
| `filtered` | 调用 `FilteredRecordRepository.create_filtered_record(...)` |

## 注意事项

1. Storage 实现时应保持接口幂等或在数据库层增加唯一约束，避免并发采集导致重复写入。
2. `content_fingerprint` 当前为 SHA256 精确指纹，不要把它理解为相似度指纹。
3. `AnalysisInput` 中的 `cleaned_content_excerpt` 是 Dify 输入片段，不一定等于完整清洗文本。
4. `topic` 传给 Dify 前必须通过 `TopicRepository.get_name(topic_id)` 转成真实主题名。
5. Processor 已兼容 Collector 当前 metadata：`language -> programming_language`，`pushed_at -> last_commit_at`；Storage 保存时建议保留原始 metadata，同时可在查询层暴露统一字段。