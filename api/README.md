# API 模块

FastAPI HTTP 接口层，为 SocialMediaReader 提供 REST API。

## 启动

```bash
# 开发模式
uvicorn api.app:app --reload

# 或直接运行
python -m api.app

# 生产模式
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

启动后访问 `http://localhost:8000/docs` 查看 Swagger 文档。

## API 端点

### 健康检查

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/health` | 系统健康检查 |

### 主题管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/topics` | 获取所有主题 |
| GET | `/api/topics/{id}` | 获取单个主题 |
| POST | `/api/topics` | 创建主题 |
| PUT | `/api/topics/{id}` | 更新主题 |

### 内容查询

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/sources` | 查询采集内容（支持 topic_id / status 过滤） |
| GET | `/api/sources/{id}` | 获取单条内容详情 |

### 分析结果

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/analysis?topic_id=1` | 按主题查询分析结果 |
| GET | `/api/analysis/source/{id}` | 获取指定 source 的分析结果 |

### 任务管理

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/jobs/trigger` | 手动触发任务 |
| GET | `/api/jobs` | 查看定时任务列表 |
| GET | `/api/jobs/status` | 查看调度器状态 |

### 统计

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/stats` | 系统统计（采集/去重/过滤数量） |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_HOST` | `0.0.0.0` | 监听地址 |
| `API_PORT` | `8000` | 监听端口 |
| `API_DEBUG` | `false` | 调试模式 |
| `API_CORS_ORIGINS` | `*` | CORS 允许的 origin，逗号分隔 |

## 架构

```
api/
├── __init__.py          # 模块导出
├── app.py               # FastAPI 应用入口 + lifespan
├── config.py            # APIConfig
├── dependencies.py      # 依赖注入（AppState 单例 + get_xxx 函数）
└── routers/
    ├── __init__.py
    ├── health.py        # GET /health
    ├── topics.py        # CRUD /api/topics
    ├── sources.py       # GET /api/sources
    ├── analysis.py      # GET /api/analysis
    ├── jobs.py          # POST /api/jobs/trigger + GET /api/jobs
    └── stats.py         # GET /api/stats
```

## 依赖注入

`AppState` 是应用级单例，在 `lifespan` 中按顺序初始化：

```
init_storage()       → Database + 所有 Repository
init_orchestrator()  → Collector + Processor + DifyClient + Orchestrator
init_scheduler()     → Scheduler
start_scheduler()    → 启动定时任务
```

各 router 通过 `Depends(get_xxx)` 获取所需的 Repository / Orchestrator / Scheduler。

## 手动触发示例

```bash
# 触发采集
curl -X POST http://localhost:8000/api/jobs/trigger \
  -H "Content-Type: application/json" \
  -d '{"job_type": "collect", "topic_id": 1}'

# 触发分析（所有主题）
curl -X POST http://localhost:8000/api/jobs/trigger \
  -H "Content-Type: application/json" \
  -d '{"job_type": "analyze", "topic_id": 0}'
```
