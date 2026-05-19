# Scheduler + Orchestrator 模块

定时调度 + 流程编排，串联 Collector → Processor → DifyClient → Storage。

## 模块定位

- **Scheduler**：APScheduler 封装，管理 cron 定时任务，支持 API 手动触发
- **Orchestrator**：流程编排核心，驱动三条 Pipeline

## 文件结构

```
scheduler/
├── __init__.py           # 导出
├── config.py             # OrchestratorConfig, SchedulerConfig
├── models.py             # JobCommand, JobResult, PipelineStats
├── orchestrator.py       # Orchestrator（三条 Pipeline）
├── scheduler.py          # Scheduler（APScheduler 封装）
└── README.md
```

## 三条 Pipeline

### Pipeline 1: Collect（采集 + 处理 + 入库）

```
TopicRepo.get_topic()
    → 构造 SourceQuery
    → Collector.collect() → [RawItem]
    → Processor.process_batch() → [ProcessingResult]
    → 按 status 写入 Storage:
        passed   → SourceRepository.create_source()
        duplicate → DuplicateRecordRepository.create_duplicate_record()
        filtered  → FilteredRecordRepository.create_filtered_record()
```

### Pipeline 2: Analyze（Dify 内容分析）

```
SourceRepo.get_sources_by_status("pending_analysis")
    → 逐条构造 AnalysisInput
    → DifyClient.analyze()
    → 成功: AnalysisResultRepo.save_analysis_result()
           SourceRepo.update_status("analyzed")
    → 失败: SourceRepo.update_status("analysis_failed")
```

### Pipeline 3: Report（周报生成 — 预留）

```
计算报告周期 → 查询高分分析结果 → Dify 周报工作流 → 保存报告
（需要 reports 表 + Dify 周报工作流，当前未实现）
```

## 数据模型

### JobCommand

任务指令，由 Scheduler 或 API 构造：

| 字段 | 类型 | 说明 |
|---|---|---|
| `job_type` | str | `"collect"` / `"analyze"` / `"report"` |
| `topic_id` | int | 主题 ID（analyze 时 0 表示全部） |
| `trigger` | str | `"cron"` / `"manual"` |
| `max_items` | int | 采集上限（默认 50） |
| `max_analyze` | int | 分析上限（默认 20） |
| `time_range` | tuple | 采集时间范围（可选） |
| `keywords_override` | list | 覆盖默认关键词（可选） |

### JobResult

任务结果：

| 字段 | 类型 | 说明 |
|---|---|---|
| `success` | bool | 是否成功 |
| `stats` | PipelineStats | 统计数据 |
| `duration_seconds` | float | 耗时 |
| `error` | str | 错误信息 |

## 定时任务

| 任务 | 默认触发时间 | 说明 |
|---|---|---|
| `daily_collect` | UTC 02:00（北京 10:00） | 采集所有活跃主题 |
| `daily_analyze` | UTC 04:00（北京 12:00） | 分析所有 pending 内容 |
| `weekly_report` | 每周日 UTC 06:00（北京 14:00） | 生成周报 |

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `ORCHESTRATOR_ANALYZE_DELAY` | `1.0` | Dify 分析请求间隔（秒） |
| `ORCHESTRATOR_MAX_COLLECT` | `50` | 单次采集上限 |
| `ORCHESTRATOR_MAX_ANALYZE` | `20` | 单次分析上限 |
| `ORCHESTRATOR_REPORT_MIN_RELEVANCE` | `0.5` | 周报最低相关性 |
| `SCHEDULER_COLLECT_HOUR` | `2` | 采集时间（UTC） |
| `SCHEDULER_ANALYZE_HOUR` | `4` | 分析时间（UTC） |
| `SCHEDULER_REPORT_DAY` | `sun` | 周报日 |
| `SCHEDULER_REPORT_HOUR` | `6` | 周报时间（UTC） |
| `SCHEDULER_ENABLED` | `true` | 是否启用定时任务 |

## 设计决策

| 决策 | 选择 | 理由 |
|---|---|---|
| Collect 和 Analyze 分离 | 两条独立 Pipeline | Dify 分析慢（10-30s/条），解耦后可独立重试 |
| 同步执行 | 不用异步队列 | V0 单机低频，APScheduler 串行足够 |
| 单条失败不中断 | 记录错误继续 | 保证批次整体完成率 |
| 所有写操作在 Orchestrator | Processor 只读 | 职责清晰，数据流向可控 |
