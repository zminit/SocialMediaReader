# Processor 模块

Processor 负责把 Collector 输出的 `RawItem` 处理成 Dify 内容分析工作流可消费的 `AnalysisInput`。

## 职责边界

Processor 负责：

- 标准化 `RawItem`
- 保守清洗 README / 正文
- 生成 V0 精确内容指纹（SHA256）
- 通过接口执行去重查询
- 执行基础硬过滤和软评分
- 生成 `AnalysisInput`

Processor 不负责：

- 保存 source
- 写入 duplicate / filtered 状态
- 调用 Dify
- 保存分析结果

这些状态类操作由上层 orchestration、storage 和 dify_client 模块负责。

## 主流程

```text
normalize -> clean/extract -> calculate fingerprint -> dedup -> quality filter -> build AnalysisInput
```

## 关键约定

- `cleaned_content_excerpt` 是清洗后截取的输入文本，不是 LLM 总结。
- `topic` 必须是真实主题名，例如 `AI 工作流搭建`。
- Processor 对 Collector 当前的 `language` / `pushed_at` 做兼容映射，对外统一为：
  - `programming_language`
  - `last_commit_at`
- V0 的 SHA256 指纹只做精确去重，不支持相似度阈值；V1 可再引入 simhash/minhash。
- 低 stars 只降权，不作为硬过滤，避免漏掉新项目。

## 使用示例

```python
from processor import (
    ContentCleaner,
    DataTransformer,
    DedupChecker,
    FingerprintCalculator,
    Normalizer,
    Processor,
    ProcessorConfig,
    QualityFilter,
)

config = ProcessorConfig.from_env()
cleaner = ContentCleaner()

processor = Processor(
    normalizer=Normalizer(),
    cleaner=cleaner,
    fingerprint_calculator=FingerprintCalculator(),
    dedup_checker=DedupChecker(dedup_repository),
    quality_filter=QualityFilter(config),
    transformer=DataTransformer(cleaner, config),
    topic_repository=topic_repository,
    config=config,
)

result = processor.process(raw_item)
if result.status == "passed":
    analysis_input = result.analysis_input
```