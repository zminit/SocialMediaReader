# Storage 模块

SQLite 持久化层，实现 Processor 依赖的查询接口和 Orchestrator 需要的写入接口。

## 架构

```
storage/
├── config.py                  # StorageConfig 配置
├── database.py                # Database 初始化 + 连接管理 + 迁移
├── topic_repository.py        # TopicRepository（实现 processor.interfaces.TopicRepository）
├── dedup_repository.py        # DedupRepository（实现 processor.interfaces.DedupRepository）
├── source_repository.py       # SourceRepository（sources CRUD）
├── duplicate_repository.py    # DuplicateRecordRepository（重复日志）
├── filtered_repository.py     # FilteredRecordRepository（过滤日志）
└── analysis_repository.py     # AnalysisResultRepository（Dify 分析结果）
```

## 表结构

| 表 | 用途 |
|---|---|
| `topics` | 主题管理（name + keywords） |
| `sources` | 通过 Processor 的内容源（去重后保留的） |
| `duplicate_records` | 被判定为重复的 RawItem 日志 |
| `filtered_records` | 被硬过滤的 RawItem 日志 |
| `analysis_results` | Dify 工作流分析结果 |
| `schema_version` | Schema 版本跟踪 |

## 使用方式

```python
from storage import StorageConfig, Database
from storage import SQLiteTopicRepository, SQLiteDedupRepository, SQLiteSourceRepository

# 初始化
config = StorageConfig.from_env()  # 或 StorageConfig(db_path="data/my.db")
db = Database(config)
db.initialize()

# 创建仓库
topic_repo = SQLiteTopicRepository(db)
dedup_repo = SQLiteDedupRepository(db)
source_repo = SQLiteSourceRepository(db)

# 创建主题
topic_id = topic_repo.create_topic("AI 工作流", keywords=["AI", "workflow"])

# 去重查询（Processor 使用）
existing_id = dedup_repo.find_by_url("https://github.com/owner/repo")

# 关闭
db.close()
```

## 配置

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `STORAGE_DB_PATH` | `data/social_media_reader.db` | SQLite 数据库文件路径 |
| `STORAGE_ECHO_SQL` | `false` | 是否打印 SQL 日志 |

## 与其他模块的关系

- **Processor** → 依赖 `DedupRepository` + `TopicRepository` 接口（定义在 `processor/interfaces.py`）
- **Orchestrator**（待开发）→ 调用 `SourceRepository`、`DuplicateRecordRepository`、`FilteredRecordRepository`、`AnalysisResultRepository`
